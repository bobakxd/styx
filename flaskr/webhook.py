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
from flask import current_app
from metrics import raw
from metrics import halstead
from cpgqls_client import CPGQLSClient
from visualization import graphs
import re
from flaskr.custom_async import get_set_event_loop

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
                file=f
        )
        db.session.add(raw_metrics)

        calc_halstead_metrics = halstead.analyze_code(tree_obj['path'], 
                content)
        halstead_metrics = HalsteadMetrics(
                unique_n1=calc_halstead_metrics.n1,
                unique_n2=calc_halstead_metrics.n2,
                total_n1=calc_halstead_metrics.N1,
                total_n2=calc_halstead_metrics.N2,
                file=f
        )
        db.session.add(halstead_metrics)

        cpg_client = CPGQLSClient('localhost:{port}'.format(
            port=current_app.config['CPG_SERVER_PORT']
        ), event_loop=get_set_event_loop())
        cfgs = graphs.cfg_for_code(cpg_client, content)
        for func_name, dot in cfgs.items():
            graph_vis = GraphVisualization(
                    graph_type=GraphType.CFG,
                    func_name=func_name,
                    graph_dot=dot,
                    file=f
            )
            db.session.add(graph_vis)


def _add_tree_obj_to_db(o, parent_dir, project_id):
    if o['type'] == 'blob':
        f = File(file_name=o['path'],
                parent_dir=parent_dir,
                git_hash=o['sha'])
        
        _add_metrics_for_file(o, f)

        db.session.add(f)
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
    if o['type'] == 'blob':
        f = File.query.filter_by(
                file_name=o['path'],
                dir_id=parent_dir.id
                ).first()

        if not f:
            f = File(file_name=o['path'],
                    parent_dir=parent_dir,
                    git_hash=o['sha'])
            _add_metrics_for_file(o, f)
            db.session.add(f)

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
    """Обходит дерево коммита при помощи Github API.

    В Github API есть ресурс для получения дерева файлов и директорий коммита:
    `https://api.github.com/repos/{user}/{repo}/git/trees{/sha}`

    URL с SHA-хешом соответстующего дерева передается в *tree_url*.

    :param string tree_url: URL дерева
    :param int project_id: идентификатор проекта
    """
    response = requests.get(tree_url)
    body = response.json()

    root_dir = Directory(project_id=project_id,
            git_hash=body['sha'])

    db.session.add(root_dir)

    _traverse(body['tree'], root_dir, project_id, _add_tree_obj_to_db)

    db.session.commit()


def update_tree_objs_in_db(tree_url, project_id):
    """Обходит дерево коммита при помощи Github API.

    В Github API есть ресурс для получения дерева файлов и директорий коммита:
    `https://api.github.com/repos/{user}/{repo}/git/trees{/sha}`

    URL с SHA-хешом соответстующего дерева передается в *tree_url*.

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
        _traverse(body['tree'], d, project_id, _update_tree_obj_in_db)
        db.session.commit()


def _traverse(tree, parent_dir, project_id, callback):
    """Вспомогательная функция, которая используется для реализации рекурсивного обхода дерева.

    Данная функция используется функцией :func:`traverse_tree`. Функция обходит рекурсивно дерево, критерием прерывания рекурсии являются узлы дерева, которые имеют тип (поле *type*) blob (файл). То есть, если узел имеет тип tree (директория), то обход продолжается для этой директории.

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

