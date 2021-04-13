"""Модуль **auth** содержит функции для работы с текущей сессией 
пользователя, также он хранит Blueprint с представлениями для 
регистрации и авторизации пользователя.
"""
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

#: auth - это Blueprint, который содержит представления для 
#: регистрации и авторизации.
#:
#: Для данного Blueprint'a статическая директория и директория для 
#: шаблонов указаны корневеные (./static и ./templates).
auth = Blueprint('auth', __name__, static_folder='static',
        template_folder='templates')
login_manager = LoginManager()

def get_sessions():
    """Возвращает словарь с сессиями пользователей, который храниться 
    в глобальном контексте приложения (в объекте g).

    :returns: словарь с признаками того, что пользователь аутентифицирован {id_пользователя:*bool*}
    :rtype: dict
    """
    if 'sessions' not in g:
        g.sessions = {}
    return g.sessions


@login_manager.user_loader
def user_loader(user_id):
    """Реализация функции user_load, которая используется расширением 
    flask-login. Данная функция возвращает объект User по юникод 
    идентификатору *user_id*.

    :param str user_id: юникод идентификатор пользователя
    :returns: объект с информацией о пользователе
    :rtype: :class:`flaskr.models.User`
    """
    only_id = int(user_id.split('<')[1].rstrip('>'))
    return User.query.get(only_id)


def verify_password(passw, user):
    """Проверяет пароль *passw* на правильность, сравнивая c паролем 
    объекта :class:`flaskr.models.User` (то есть с паролем, который 
    храниться в БД).

    :param str passw: сравниваемый пароль
    :param user: объект с информацией о пользователе
    :type user: :class:`flaskr.models.User`
    :returns: признак правильности пароля
    :rtype: bool
    """
    digest = hashlib.sha256(passw.encode('utf-8')).hexdigest()
    return user.passw_hash == digest


@auth.route('/signin', methods=['GET', 'POST'])
def signin():
    """Представление (view) для авторизации пользователя, принимает 
    запросы двух типов: GET и POST.

    При получении запроса GET возвращает страницу со входом для 
    пользователя. При получения запроса POST (в случае, если форма 
    была заполнена), то обрабатывает параметры, которые передаются 
    формой.

    :returns: шаблон (render_template) или перенаправление (redirect, в случае удачной аутентификации)
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.user_panel', 
            username=current_user.username))

    if request.method == 'POST':
        # Проверяем все ли поля формы заполнены
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
    """Представление (view) для выхода пользователя. Обновляет 
    состояние сессии пользователя после выхода.
    """
    user = current_user
    user.set_authenticated(False)
    logout_user()
    return redirect(url_for('.signin'))


def register_user(username, email, passw):
    """Добавление пользователя в БД с параметрами *username*, 
    *email*, *passw*.

    В случае если пользователь с указанным именем *username* или 
    *email* существует в БД, то возвращает предупреждение с 
    использованием функции :func:`flask.flash`. В случае, если 
    такого пользователя не существует, то добавляет соответствующую 
    запись в БД.

    :param str username: имя пользователя
    :param str email: электронная почта пользователя
    :param str passw: пароль
    :returns: перенаправление (redirect в случае успешного добавления)
     или None (но выводиться предупреждение с использованием :func:`flask.flash`)
    """
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
    """Представление (view) со страницей успешной регистрации"""
    return render_template('signup_success.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Представление (view) для регистрации пользователя, принимает 
    запросы двух типов: GET и POST.

    При получении запроса GET возвращает страницу с формой 
    регистрации. При получения запроса POST (в случае, если форма 
    была заполнена), то обрабатывает параметры, которые передаются 
    формой.

    :returns: шаблон (render_template) или перенаправление (redirect, в случае удачной регистрации)
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.user_panel', 
            username=current_user.username))

    if request.method == 'POST':
        # Проверяем все ли поля формы заполнены
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

