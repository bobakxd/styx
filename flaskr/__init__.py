from flask import Flask
from flaskr.main import main
from flaskr.auth import auth
from flaskr.api import api_bp
from flaskr.filters import filters
from flaskr.auth import login_manager
from flaskr.models import db
from sqlalchemy.engine import Engine
from sqlalchemy import event

app = Flask(__name__)
app.config.update(
    SECRET_KEY=b'\xd2\xa8\x86\x05\xb0[\x85S\xeeF\x1c#\x8av1\x05',
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    SQLALCHEMY_DATABASE_URI='sqlite:///main.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    CPG_SERVER_PORT=5052
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
app.register_blueprint(filters)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

