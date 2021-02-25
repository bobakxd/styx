from flask import Flask
from flaskr.main import main
app = Flask(__name__)

app.register_blueprint(main)

