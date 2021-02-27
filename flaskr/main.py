from flask import Blueprint
from flask import render_template
from flask_login import login_required

main = Blueprint('main', __name__, static_folder='static', 
        template_folder='templates')

@main.route('/<username>')
@login_required
def user_panel(username):
    return 'Вы успешно авторизовались!'


@main.route('/')
def index():
    return render_template('index.html')

