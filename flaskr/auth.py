from flask import Blueprint
from flask import render_template
from flask import request
from flask import flash
import functools
from flaskr.models import User
from flaskr.models import db
import hashlib
from flask import redirect
from flask import url_for
from flask import session
from flask import g
from flask_login import LoginManager
from flask_login import login_user
from flask_login import login_required
from flask_login import current_user
from flask_login import logout_user
from sqlalchemy import or_

auth = Blueprint('auth', __name__, static_folder='static',
        template_folder='templates')
login_manager = LoginManager()

def get_sessions():
    if 'sessions' not in g:
        g.sessions = {}
    return g.sessions


@login_manager.user_loader
def user_loader(user_id):
    only_id = int(user_id.split('<')[1].rstrip('>'))
    return User.query.get(only_id)


def verify_password(passw, user):
    digest = hashlib.sha256(passw.encode('utf-8')).hexdigest()
    return user.passw_hash == digest


@auth.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('main.user_panel', 
            username=current_user.username))

    if request.method == 'POST':
        if functools.reduce(lambda prev, el: prev and bool(el), 
                request.form.values()):
            user = User.query.filter(or_(
                User.username == request.form['credential'],
                User.email == request.form['credential'])).first()
            if user and verify_password(request.form['passw'], user):
                user.set_authenticated = True
                login_user(user, remember=True)
                return redirect(url_for('main.user_panel', 
                    username=user.username))
            else:
                flash('Вы ввели неверное имя пользователя или пароль!')
        else:
            flash('Не все поля заполнены!')

    return render_template('signin.html', **request.form)


@auth.route('/logout')
@login_required
def logout():
    user = current_user
    user.set_authenticated(False)
    logout_user()
    return 'Вы успешно вышли!'


def register_user(username, email, passw):
    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким именем уже существует!')
        return

    if User.query.filter_by(email=email).first():
        flash('Пользователь с таким email\'ом уже существует!')
        return

    digest = hashlib.sha256(passw.encode('utf-8')).hexdigest()
    user = User(username=username, email=email, passw_hash=digest)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('.signup_success'))


@auth.route('/signup/success')
def signup_success():
    return render_template('signup_success.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.user_panel', 
            username=current_user.username))

    if request.method == 'POST':
        if functools.reduce(lambda prev, el: prev and bool(el), 
                request.form.values()):
            if request.form['passw'] == request.form['repeat']:
                redirect_view = register_user(request.form['username'],
                        request.form['email'], request.form['passw'])
                if redirect_view:
                    return redirect_view
            else:
                flash('Введенные пароли не совпадают!')
        else:
            flash('Не все поля заполнены!')

    return render_template('signup.html', **request.form)

