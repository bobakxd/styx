from flask import Blueprint
from flask_restx import Api
from flask_restx import Resource
from flaskr.models import User
from flask_restx import fields
from flask_restx import reqparse

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
    'registration_time': fields.DateTime(dt_format='rfc822')
})

@api.route('/<string:username>/settings')
@api.doc(params={'username': 'Имя пользователя'})
class UserSettings(Resource):
    @api.marshal_with(user_model, envelope='user')
    def get(self, username):
        user = User.query.filter_by(username=username).first()
        return user

