from flask import Flask
from flaskr.main import main
from flaskr.auth import auth
from flaskr.api import api_bp
from flaskr.auth import login_manager
from flaskr.models import db
import os
import sys

app = Flask(__name__)
app.config.update(
    SECRET_KEY=b'\xd2\xa8\x86\x05\xb0[\x85S\xeeF\x1c#\x8av1\x05',
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    SQLALCHEMY_DATABASE_URI='sqlite:///main.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ECHO=True
)
db.init_app(app)
login_manager.init_app(app)

@app.cli.command('init-db')
def init_db():
    with app.app_context():
        db.create_all()

app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(api_bp)

