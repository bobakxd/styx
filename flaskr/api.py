from flask import Blueprint
from flask_restx import Api
from flask_restx import Resource
from flaskr.models import User
from flaskr.models import Project
from flask_restx import fields
from flask_restx import reqparse
from flask_restx import marshal
from functools import wraps
from flaskr.models import db
from flask import request
from flask import url_for
from sqlalchemy.exc import IntegrityError

api_bp = Blueprint('api', __name__, static_folder='static',
        template_folder='templates', url_prefix='/api')

authorizations = {
        'APITokenHeader': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-TOKEN'
        }
}

api = Api(api_bp, authorizations=authorizations)

user_model = api.model('User', {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String,
    'registration_time': fields.DateTime(dt_format='rfc822'),
    'self_url': fields.Url('api.user_settings_resource')
})

project_model = api.model('Project', {
    'id': fields.Integer,
    'user': fields.Nested(user_model),
    'project_name': fields.String,
    'self_url': fields.String(attribute=lambda x: url_for('api.project_root_resource', username=x.user.username, project_name=x.project_name))
})

def token_required(f):
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
class UserSettings(Resource):
    @api.marshal_with(user_model, envelope='user')
    def get(self, username):
        user = User.query.filter_by(username=username).first()
        return user


@api.route('/<string:username>/<string:project_name>')
class ProjectRoot(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('description', 
                help='Описание проекта', location='json')

    def get(self, username, project_name):
        user = User.query.filter_by(username=username).first()
        project = Project.query.filter_by(user_id=user.id, project_name=project_name).first()

        if not project:
            return {'message': 'Проекта с указанным названием не существует.'}, 404

        return marshal(project, project_model), 200

    @api.doc(security='APITokenHeader')
    @api.expect(parser)
    @token_required
    def post(self, username, project_name):
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


api.add_resource(UserSettings, '/<string:username>/settings', endpoint='user_settings_resource')
api.add_resource(ProjectRoot, '/<string:username>/<string:project_name>', endpoint='project_root_resource')

