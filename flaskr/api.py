"""Модуль **api** содержит ресурсы API приложения. Ресурсы реализованы
 при помощи класса :class:`flask_restx.Resource`. В экземплярах данных
 классов содержиться логика для обработки запросов к ресурсу.
 """
from flask import Blueprint
from flask_restx import Api
from flask_restx import Resource
from flaskr.models import User
from flaskr.models import Project
from flaskr.models import Directory
from flaskr.models import File
from flask_restx import fields
from flask_restx import reqparse
from flask_restx import marshal
from functools import wraps
from flaskr.models import db
from flask import request
from flask import url_for
from sqlalchemy.exc import IntegrityError
from flask_restx import inputs
from flaskr import webhook
from flask import current_app

#: **api_bp** - это Blueprint, который содержит представления ресурсов API приложения.
#:
#: В дальнейшем api_bp используется классом :class:`flask_restx.Api`.
#:
#: Для данного Blueprint'a статическая директория и директория для 
#: шаблонов указаны корневеные (./static и ./templates).
api_bp = Blueprint('api', __name__, static_folder='static',
        template_folder='templates', url_prefix='/api')

#: Словарь **authorizations** содержит описание заголовков, которые 
#: используются для аутентификации запросов.
#:
#: *APITokenHeader* - заголовок, в котором хранится веб-токен
authorizations = {
        'APITokenHeader': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-TOKEN'
        }
}

#: Главный объект API, который используется в дальнейшем для создания 
#: ресурсов при помощи класса :class:`flask_restx.Resource`.
api = Api(api_bp, authorizations=authorizations)

#: Модель пользователя, которая используется для форматирования ответов 
#: ресурсов.
#:
#: :Поля модели:
#:    * id (*int*) - идентификатор пользователя
#:    * username (*str*) - имя пользователя
#:    * email (*str*) - email пользователя
#:    * registration_time (:class:`datetime.datetime.DateTime`) - дата регистрации пользователя
#:    * self_url (*str*) - ссылка на самого себя
user_model = api.model('User', {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String,
    'registration_time': fields.DateTime(dt_format='rfc822'),
    'self_url': fields.Url('api.user_settings_resource')
})

#: Модель проекта, которая используется для форматирования ответов 
#: ресурсов.
#:
#: :Поля модели:
#:    * id (*int*) - идентификатор проекта
#:    * user (:class:`flask_restx.fields.Nested`) - вложенный объект пользователя
#:    * project_name (*str*) - название проекта
#:    * self_url (*str*) - ссылка на самого себя
project_model = api.model('Project', {
    'id': fields.Integer,
    'user': fields.Nested(user_model),
    'project_name': fields.String,
    'self_url': fields.String(attribute=lambda x: url_for('api.project_root_resource', username=x.user.username, project_name=x.project_name))
})

def token_required(f):
    """Декоратор, который проверяет валидность веб-токена перед 
    выполнением запроса.

    :param *func* f: функция обработки запроса
    :returns: декоратор с переданной функцией
    :rtype: *func*
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        header_name = authorizations['APITokenHeader']['name'] 

        if header_name in request.headers:
            token = request.headers[header_name]

        if not token:
            return {'message': 'Необходим токен для выполнения операции.'}, 401

        is_success, result = User.decode_auth_token(token) 
        if is_success and result == kwargs['username']:
            return f(*args, **kwargs)
        elif is_success:
            return {'message': 'Необходим токен владельца проекта.'}, 401
        else:
            return {'message': result}, 401

    return decorated


@api.route('/<string:username>/settings')
@api.doc(params={'username': 'Имя пользователя'})
@api.doc(params={'username': 'Имя пользователя'}, description='Настройки пользователя')
class UserSettings(Resource):
    """Ресурс настроек пользователя, URL ресурса: /{username}/settings.

    :Параметры запроса:
       * *username* - имя пользователя
    """
    @api.marshal_with(user_model, envelope='user')
    def get(self, username):
        """Возвращает представление пользователя

        Обратывает GET запрос, возвращет представление пользователя с использованием модели :data:`user_model`.
        """
        user = User.query.filter_by(username=username).first()
        return user


@api.route('/<string:username>/<string:project_name>')
@api.doc(params={'username': 'Имя пользователя', 'project_name': 'Название проекта'}, description='Корень проекта')
class ProjectRoot(Resource):
    """Ресурс корня проекта, URL ресурса: /{username}/{project_name}.

    :Параметры запроса:
       * *username* - имя пользователя
       * *project_name* - название проекта
    """
    parser = reqparse.RequestParser()
    parser.add_argument('description', 
                help='Описание проекта', location='json')

    @api.response(200, 'Success', project_model)
    @api.response(404, 'Проекта не существует')
    def get(self, username, project_name):
        """Возвращает представление проекта.

        Обрабатывает GET запрос, возвращает представление проекта с 
        использованием модели :data:`project_model`. Либо ошибку 404 в случае, если указазно не верное название проекта.
        """
        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        return marshal(project, project_model), 200

    @api.doc(security='APITokenHeader')
    @api.expect(parser)
    @api.response(200, 'Success', project_model)
    @api.response(422, 'Проект с таким названием уже существует')
    @token_required
    def post(self, username, project_name):
        """Добавляет проект.

        Обрабатывает POST запрос, добавляет проект в БД с указанными 
        параметрами, также возвращает представление проекта с 
        использованием модели :data:`project_model`. 

        В случае, если проект с таким названием уже существует, то 
        возвращает ошибку 422. 

        :param str description: описание проекта, передается в теле запроса
        """
        args = ProjectRoot.parser.parse_args()
        user = User.query.filter_by(username=username).first()

        project = Project(user_id=user.id,
                project_name=project_name,
                description=args['description'])
        db.session.add(project)

        try:
            db.session.commit()
        except IntegrityError:
            return {'message': 'Проект с таким названием уже существует.'}, 422

        return marshal(project, project_model), 200


@api.route('/<string:username>/<string:project_name>/webhook/github')
@api.doc(params={'username': 'Имя пользователя', 'project_name': 'Название проекта'}, description='Веб-хук проекта для синхронизации с Github.')
class Webhook(Resource):
    """Ресурс Github веб-хука проекта, URL ресурса: 
    {username}/{project_name}/webhook/github.

    :Параметры запроса:
       * *username* - имя пользователя
       * *project_name* - название проекта
    """
    model = api.model('Model', {
        'description': fields.String,
        'self_url': fields.String
    })

    @api.response(200, 'Success', model)
    @api.response(404, 'Проекта не существует')
    def get(self, username, project_name):
        """Возвращает представление с описанием веб-хука.

        Обрабатывает GET запрос, возвращает представление с описанием веб-хука и ссылкой на самого себя.

        :Поля представления:
           * *description* (*str*) - описание веб-хука
           * *hook_id* (*int*) - идентификатор веб-хука
           * *self_url* (*str*) - ссылка на самого себя
        """
        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        return {'description': 'Данный веб-хук подключается к сервису Github. После подключения, сервис будет отправлять POST запросы на данный ресурс для синхронизации репозитория с данным проектом. Если вы еще подключили данный веб-хук к репозиторию, то вам необходимо сделать, чтобы получить метрики вашего проекта.', 'hook_id': project.hook_id, 'self_url': self._get_self_url(username, project_name)}, 200

    put_parser = reqparse.RequestParser()
    put_parser.add_argument('reset', type=inputs.boolean,
             location='args', default=False, 
             help='Сбрасывает веб-хук')

    @api.response(200, 'Success')
    @api.response(404, 'Проекта не существует')
    @api.response(406, 'Веб-хук не подключен')
    @api.expect(put_parser)
    def put(self, username, project_name):
        """Сбрасывает веб-хук.

        Обрабатывает PUT запрос, который сбрасывает веб-хук в зависимости от параметра *reset*. В случае успеха, возвращает представление.

        :Поля представления:
           * *message* (*str*) - сообщение об проведенной операции
        """
        args = Webhook.put_parser.parse_args(request)

        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        if args['reset']:
            if project.hook_id is not None:
                Directory.query.filter_by(dir_name=None, project_id=project.id).delete()
                project.hook_id = None
                db.session.commit()
                return {'message': 'Хук был успешно сброшен. Теперь к проекту можно подключить новый веб-хук.', 'self-url': self._get_self_url(username, project_name)}, 200
        else:
            if project.hook_id is not None:
                return {
                    'message': 'Хук не был сброшен. В поле hook_id приведен идентификатор текущего подключенного веб-хука к проекту.',
                    'hook_id': project.hook_id,
                    'self-url': self._get_self_url(username, 
                        project_name)
                }, 200

        return { 'message': 'К проекту не подключен веб-хук в данный момент.' }, 406
    
    post_model = api.schema_model('PostModel', {
        'required': ['hook_id'],
        'properties': {
            'hook_id': {
                'description': 'Идентификатор веб-хука',
                'type': 'integer'
            },
            'after': {
                'description': 'SHA самого последнего коммита после выполнения push в репозитории',
                'type': 'string'
            },
            'repository': {
                'required': ['default_branch', 'branches_url'],
                'properties': {
                    'branches_url': {
                        'description': 'URL ветвей репозитория',
                        'type': 'string'
                    },
                    'git_commits_url': {
                        'description': 'URL коммитов репозитория',
                        'type': 'string'
                    },
                    'default_branch': {
                        'description': 'Название главной ветви репозитория',
                        'type': 'string'
                    }
                },
                'type': 'object'
            }
        },
        'type': 'object'
    })

    @api.response(200, 'Success')
    @api.response(404, 'Проекта не существует')
    @api.response(403, 'Хук уже подключен')
    @api.response(406, 'Неправильные заголовки в запросе')
    @api.param('X-GitHub-Event', 'Название события, которое запустило веб-хук', _in='header', required=True)
    @api.expect(post_model, validate=True)
    def post(self, username, project_name): 
        """Обрабатывает разные события Github веб-хука.

        Обрабатывает POST запрос, который обрабатывает разные события веб-хука Github в зависимости заголовка *X-GitHub-Event*. В случае успеха, возвращает представление cо статусом веб-хука и ссылкой на самого себя.

        :Поля представления:
           * *message* (*str*) - сообщение о статусе веб-хука
           * *self_url* (*str*) - ссылка на самого себя
        """
        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        event = request.headers['X-GitHub-Event']        
        if event == 'ping':
            if not project.hook_id:
                project.hook_id = api.payload['hook_id']
                db.session.commit()
                commit = webhook.get_commit_of_default_branch(
                        api.payload['repository'])
                webhook.add_tree_objs_to_db(commit['commit']['tree']['url'], project.id)

                return {'message': 'Хук успешно подключен.', 'hook_id': project.hook_id, 'self-url': self._get_self_url(username, project_name)}, 200
            else:
                return {'message': 'Хук уже подключен к проекту.'}, 403

        if event == 'push':
            if project.hook_id:
                after_commit = webhook.get_commit(
                        api.payload['repository']['git_commits_url'], 
                        api.payload['after']
                        )
                webhook.update_tree_objs_in_db(
                        after_commit['tree']['url'], project.id)

                return {'message': 'Событие push успешно обработано.', 'hook_id': project.hook_id, 'self-url': self._get_self_url(username, project_name)}, 200
            else:
                return {'message': 'Хук не подключен к проекту.'}, 403

    def _get_self_url(self, username, project_name):
        return '/{username}/{project_name}/webhook/github'.format(username=username, project_name=project_name) 


@api.route('/<string:username>/<string:project_name>/<path:path>/metrics/<string:metrics_type>')
@api.doc(params={'username': 'Имя пользователя', 'project_name': 'Название проекта', 'path': 'Путь к файлу', 'metrics_type': 'Вид метрик'}, description='Метрики файла')
class Metrics(Resource):
    """Ресурс метрик файла, URL ресурса: 
    {username}/{project_name}/{path}/metrics/{metrics_type}.

    :Параметры запроса:
       * *username* - имя пользователя
       * *project_name* - название проекта
       * *path* - путь к файлу
       * *metrics_type* - вид метрик (raw, halstead)

    :Вид метрик:
       * *raw* - LOC метрики
       * *halstead* - метрики Холстеда
    """
    raw_metrics_model = api.model('RawMetrics', {
        'loc': fields.Integer(required=True, help='Общее количество строк кода (LOC)'),
        'lloc': fields.Integer(required=True, help='Количество логических строк кода (LLOC)'),
        'ploc': fields.Integer(required=True, help='Количество физических строк кода (PLOC)'),
        'comments': fields.Integer(required=True, help='Количество строк комментариев'),
        'blanks': fields.Integer(required=True, help='Количество пустых строк')
    })

    halstead_metrics_model = api.model('HalsteadMetrics', {
        'n1': fields.Integer(required=True, help='Количество уникальных операторов', attribute='unique_n1'),
        'n2': fields.Integer(required=True, help='Количество уникальных операндов', attribute='unique_n2'),
        'N1': fields.Integer(required=True, help='Общее количество операторов', attribute='total_n1'),
        'N2': fields.Integer(required=True, help='Общее количество операндов', attribute='total_n2')
    })

    @api.response(200, 'Success')
    @api.response(404, 'Проекта не существует')
    @api.response(406, 'Веб-хук не был подключен')
    def get(self, username, project_name, path, metrics_type):
        """Возвращает представление с различными метриками файла.

        Обрабатывает GET запрос, возвращает представление с различными метриками файла. Вид метрик указывается при помощи параметра *metrics_type*. Для разных значений параметра возвращаются разные представления метрик.

        :Поля представления для raw (LOC метрики):
           * loc (*int*) - общее количество строк кода (LOC)
           * lloc (*int*) - количество логических строк кода (LLOC)
           * ploc (*int*) - количество физических строк кода (PLOC)
           * comments (*int*) - количество строк комментариев
           * blanks (*int*) - количество пустых строк

        :Поля представления для halstead (метрики Холстеда):
           * n1 (*int*) - количество уникальных операторов
           * n1 (*int*) - количество уникальных операндов
           * N1 (*int*) - общее количество операторов
           * N2 (*int*) - общее количество операндов
        """
        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        parts = path.split('/')
        dirs = parts[:-1]
        filename = parts[-1]

        parent = Directory.query.filter_by(dir_name=None, project_id=project.id).first()

        if not parent:
            return {'message': 'Веб-хук не был подключен к проекту.'}, 406

        for child in dirs:
            parent = Directory.query.filter_by(dir_parent_id=parent.id, dir_name=child).first()

            if not parent:
                return {'message': 'Директории с указанным именем не существует.'}, 404

        f = File.query.filter_by(dir_id=parent.id, file_name=filename).first()

        if not f:
            return {'message': 'Файла с указанным именем не существует.'}, 404

        if metrics_type == 'raw':
            return marshal(f.raw_metrics, Metrics.raw_metrics_model), 200
        elif metrics_type == 'halstead':
            return marshal(f.halstead_metrics, 
                    Metrics.halstead_metrics_model), 200
        else:
            return {'message': 'Указанные метрики не вычислены для данного файла'}, 404


api.add_resource(UserSettings, '/<string:username>/settings', endpoint='user_settings_resource')
api.add_resource(ProjectRoot, '/<string:username>/<string:project_name>', endpoint='project_root_resource')

