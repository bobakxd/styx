from flask import Flask
from flaskr.main import main
from flaskr.auth import auth
from flaskr.models import db

app = Flask(__name__)
app.config['SECRET_KEY'] = b'\xd2\xa8\x86\x05\xb0[\x85S\xeeF\x1c#\x8av1\x05'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
db.init_app(app)

@app.cli.command('init-db')
def init_db():
    with app.app_context():
        db.create_all()

app.register_blueprint(main)
app.register_blueprint(auth)

