"""Модуль **webhook** содержит функции для взаимодейтсвия с Github API. В модуле также есть разные вспомогательные функции для обработки параметров или полей запросов Github API.
"""
import requests
import urllib
import base64
from flaskr.models import File
from flaskr.models import Directory
from flaskr.models import RawMetrics
from flaskr.models import HalsteadMetrics
from flaskr.models import db
from flaskr.models import GraphVisualization
from flaskr.models import GraphType
from flaskr.models import Project
from flask import current_app
from metrics import raw
from metrics import halstead
#from cpgqls_client import CPGQLSClient
from visualization import graph
import re
from flaskr.custom_async import get_set_event_loop
import datetime

def apply_args_to_url(url, **kwargs):
    """Применяет аргументы к URL с параметрами. Возвращает строку с URL и вставленными в него параметрами.

    URL с параметрами, который возвращается в ответах Github API имеет следующий формат:
    `https://api.github.com/../..{/arg}`

    Функция подставляет в *arg* параметр из *kwargs* и возвращает строку с формированным URL'ом.

    :param string url: URL с параметрами
    :param kwargs: словарь с переменными именованными параметрами
    :returns: сформированная строка c URL
    :rtype: string
    """
    url = url.replace('{/', '/{')
    return url.format(**kwargs)


def get_commit(git_commits_url, sha):
    response = requests.get(apply_args_to_url(git_commits_url, sha=sha))
    return response.json()


def get_commit_of_default_branch(repo):
    """Получает представление последнего коммита главной ветви репозитория.

    Выполняет запрос к Github API, который получает представление последнего коммита главной ветви репозитория *repo*.

    :param dict repo: JSON-объект репозитория
    :returns: JSON-объект последнего коммита
    :rtype: dict
    """
    branch = repo['default_branch']
    branches_url = repo['branches_url']
    response = requests.get(apply_args_to_url(branches_url, branch=branch))
    return response.json()['commit']


def base64_decode(s):
    """Переводит строку в формате base64 в юникод (utf-8) строку.

    :param string s: строка в base64
    :returns: юникод строка
    :rtype: string
    """
    return base64.b64decode(s).decode('utf-8')


def decode_content(content, encoding):
    """Переводит строку с содержимым *content* в юникод (utf-8) строку в зависимости от формата *encoding*, в котором хранится *content*.

    :param string content: строка с содержимым
    :param string encoding: формат строки (base64,..)
    :returns: юникод строка
    :rtype: string
    """
    decode_func = {
        'base64': base64_decode
    }

    lines = content.split('\n')
    return ''.join([decode_func[encoding](l) for l in lines])


def _add_metrics_for_file(tree_obj, f):
    """Добавляет метрики для файла из дерева репозитория.

    Подсчитывает метрики и строит визуализации для файла *f*. Создает модели метрик (:class:`flaskr.models.RawMetrics`, :class:`flaskr.models.HalsteadMetrics`) и модели визуализаций (:class:`flaskr.models.GraphVisualization`) для файла *f*.

    :param dict tree_obj: узел из дерева коммита репозитория
    :param f: модель файла
    :type f: :class:`flaskr.models.File`
    """
    if re.match(r'.+\.c$', tree_obj['path']):
        blob_response = requests.get(tree_obj['url'])
        blob_body = blob_response.json()

        content = decode_content(
                blob_body['content'], blob_body['encoding'])
        calc_raw_metrics = raw.analyze_code(tree_obj['path'], content)
        raw_metrics = RawMetrics(
                loc=calc_raw_metrics.loc,
                lloc=calc_raw_metrics.lloc,
                ploc=calc_raw_metrics.ploc,
                comments=calc_raw_metrics.comments,
                blanks=calc_raw_metrics.blanks,
                file_id=f.id
        )
        db.session.add(raw_metrics)

        calc_halstead_metrics = halstead.analyze_code(tree_obj['path'], 
                content)
        halstead_metrics = HalsteadMetrics(
                unique_n1=calc_halstead_metrics.n1,
                unique_n2=calc_halstead_metrics.n2,
                total_n1=calc_halstead_metrics.N1,
                total_n2=calc_halstead_metrics.N2,
                file_id=f.id
        )
        db.session.add(halstead_metrics)

        #cpg_client = CPGQLSClient('localhost:{port}'.format(
        #    port=current_app.config['CPG_SERVER_PORT']
        #), event_loop=get_set_event_loop())
        current_app.logger.info("file: ")
        current_app.logger.info(tree_obj['path'])
        cfgs = graph.cfg_for_code(content, tree_obj['path'])
        for func_name, dot in cfgs.items():
            graph_vis = GraphVisualization(
                    graph_type=GraphType.CFG,
                    func_name=func_name,
                    graph_dot=dot,
                    file_id=f.id
            )
            db.session.add(graph_vis)


def _add_tree_obj_to_db(o, parent_dir, project_id):
    """Добавляет узел дерева коммита в БД.

    Если узел дерева типа **blob**, то создает модель файла :class:`flaskr.models.File`. Для данного файла добавляются метрики в БД при помощи функции :func:`_add_metrics_for_file`.

    Если узел дерева типа **tree**, то создает модель директории :class:`flaskr.models.Directory`.

    :param dict o: узел из дерева коммита репозитория
    :param parent_dir: родительская директория узла
    :type parent_dir: :class:`flaskr.models.Directory`
    :param int project_id: идентификатор проекта
    :returns: добавленная модель файла или директории, None в случае, если узел не был добавлен
    """
    if o['type'] == 'blob':
        f = File(file_name=o['path'],
                parent_dir=parent_dir,
                git_hash=o['sha'])
        
        db.session.add(f)
        db.session.flush()
        _add_metrics_for_file(o, f)

        return f
    
    if o['type'] == 'tree':
        d = Directory(dir_name = o['path'],
                project_id=project_id,
                dir_parent=parent_dir,
                git_hash=o['sha'])
        db.session.add(d)
        return d

    return None


def _update_tree_obj_in_db(o, parent_dir, project_id):
    """Обновляет узел дерева коммита в БД.

    Если узел дерева типа **blob** и соответствующей модели нет в БД, то создает модель файла :class:`flaskr.models.File`. Для данного файла обновляются метрики в БД при помощи функции :func:`_add_metrics_for_file`.

    Если узел дерева типа **tree** и соответстующей модели нет в БД, то создает модель директории :class:`flaskr.models.Directory`.

    :param dict o: узел из дерева коммита репозитория
    :param parent_dir: родительская директория узла
    :type parent_dir: :class:`flaskr.models.Directory`
    :returns: модель файла или директории, если произошли изменения, None в случае, если узел не был изменен
    """
    if o['type'] == 'blob':
        f = File.query.filter_by(
                file_name=o['path'],
                dir_id=parent_dir.id
                ).first()

        if not f:
            f = File(file_name=o['path'],
                    parent_dir=parent_dir,
                    git_hash=o['sha'])
            db.session.add(f)
            db.session.flush()
            _add_metrics_for_file(o, f)

        if o['sha'] != f.git_hash:
            _add_metrics_for_file(o, f)
            f.git_hash = o['sha']

        return f

    if o['type'] == 'tree':
        d = Directory.query.filter_by(
            project_id=project_id,
            dir_name=o['path'],
            dir_parent_id=parent_dir.id
            ).first()

        if not d:
            d = Directory(dir_name = o['path'],
                project_id=project_id,
                dir_parent=parent_dir,
                git_hash=o['sha'])
            db.session.add(d)
            return d
        
        if o['sha'] != d.git_hash:
            return d

        return None
 

def add_tree_objs_to_db(tree_url, project_id):
    """Обходит дерево коммита при помощи Github API и добавляет узлы в БД.

    В Github API есть ресурс для получения дерева файлов и директорий коммита:
    `https://api.github.com/repos/{user}/{repo}/git/trees{/sha}`

    URL с SHA-хешом соответстующего дерева передается в *tree_url*.

    Обход дерева производится при помощи функции :func:`_traverse`, в параметр *callback* передается функция :func:`_add_tree_obj_to_db`.

    :param string tree_url: URL дерева
    :param int project_id: идентификатор проекта
    """
    response = requests.get(tree_url)
    body = response.json()

    p = Project.query.filter_by(id=project_id).first()
    p.update_time = datetime.datetime.utcnow()

    root_dir = Directory(project_id=project_id,
            git_hash=body['sha'])

    db.session.add(root_dir)

    _traverse(body['tree'], root_dir, project_id, _add_tree_obj_to_db)

    db.session.commit()


def update_tree_objs_in_db(tree_url, project_id):
    """Обходит дерево коммита при помощи Github API и обновляет узлы в БД.

    В Github API есть ресурс для получения дерева файлов и директорий коммита:
    `https://api.github.com/repos/{user}/{repo}/git/trees{/sha}`

    URL с SHA-хешом соответстующего дерева передается в *tree_url*.

    Обход дерева производится при помощи функции :func:`_traverse`, в параметр *callback* передается функция :func:`_update_tree_obj_in_db`.

    :param string tree_url: URL дерева
    :param int project_id: идентификатор проекта
    """
    response = requests.get(tree_url)
    body = response.json()

    d = Directory.query.filter_by(
            project_id=project_id,
            dir_name=None
            ).first()

    if body['sha'] != d.git_hash:
        p = Project.query.filter_by(id=project_id).first()
        p.update_time = datetime.datetime.utcnow()
        _traverse(body['tree'], d, project_id, _update_tree_obj_in_db)
        db.session.commit()


def _traverse(tree, parent_dir, project_id, callback):
    """Вспомогательная функция, которая используется для реализации рекурсивного обхода дерева.

    Данная функция используется функциями :func:`add_tree_objs_to_db` и :func:`update_tree_objs_in_db`. Функция обходит рекурсивно дерево, критерием прерывания рекурсии являются узлы дерева, которые имеют тип (поле *type*) blob (файл). То есть, если узел имеет тип tree (директория), то обход продолжается для этой директории. При обходе дерева для каждого узла вызывается функция *callback*.

    :param dict tree: JSON-объект дерева
    :param parent_dir: родительская директория
    :type parent_dir: :class:`flaskr.models.Directory`
    :param int project_id: идентификатор проекта
    """
    for o in tree:
        obj = callback(o, parent_dir, project_id)

        if o['type'] == 'tree':
            if obj:
                response = requests.get(o['url'])
                body = response.json()
                _traverse(body['tree'], obj, project_id, callback)

