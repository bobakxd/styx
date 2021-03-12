"""Модуль **main** содержит основные представление (view), которые не 
выполняет специфичных функций, например, главная страница.
"""
from flask import Blueprint
from flask import render_template
from flask_login import login_required
import hashlib
from flaskr.models import User
from flaskr.models import Project
from flaskr.models import Token
import locale
from flask import request
from flask import flash
from datetime import datetime
from flaskr.models import db
import functools
from flask import current_app

#: main - это Blueprint, который содержит представления данного модуля.
#:
#: Для данного Blueprint'a статическая директория и директория для 
#: шаблонов указаны корневеные (./static и ./templates).
main = Blueprint('main', __name__, static_folder='static', 
        template_folder='templates')

try:
    locale.setlocale(locale.LC_TIME, ('ru', 'utf-8'))
except locale.Error:
    pass

def gravatar_avatar_url(email, size):
    """Возвращает граватар с указанным *email* и размером *size*. 

    Возвращает сгенерированный граватар с использованием параметра 
    d=monsterid в случае, если аватар не загружен на сервисе.

    :param str email: email пользователя
    :param int size: ширина или высота аватара
    :returns: URL граватара
    :rtype: str
    """
    avatar_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return 'https://www.gravatar.com/avatar/{hash}?d=monsterid&s={px}'\
            .format(hash=avatar_hash, px=size)


@main.app_template_filter()
def date_format(value):
    """Фильтр, который преобразовывает DateTime в строку формата 
    %-d %B, %Y г.
    """
    return value.strftime('%-d %B, %Y г.') 


@main.route('/<username>')
@login_required
def user_panel(username):
    """Представление (view) c главной панелью пользователя.

    Возвращает шаблон user_panel/index.html. Принимает параметр 
    *username*, т.к. для каждой панели пользователя выделяет отдельный 
    URL /<*username*>.

    :param str username: имя пользователя
    """
    user = User.query.filter_by(
            username=username).first()
    projects = Project.query.filter_by(user_id=user.id).all()

    return render_template('user_panel/index.html', 
            user=user, projects=projects, 
            gravatar_avatar_url=gravatar_avatar_url)


@main.route('/<username>/settings')
@login_required
def user_settings(username):
    """Представление (view) с панелью настроек пользователя.

    Принимает параметр *username*, т.к. для каждой панели настроек 
    пользователя выделяется отдельный ресурс /<*username*>.

    :param str username: имя пользователя
    """
    user = User.query.filter_by(
            username=username).first()
    return render_template('user_panel/settings.html', 
            user=user, gravatar_avatar_url=gravatar_avatar_url)


@main.route('/<username>/settings/tokens', methods=['GET', 'POST'])
@login_required
def user_settings_tokens(username):
    """Представление (view) c панелью настроек токенов пользователя.

    Возвращает шаблон user_panel/settings_tokens.html. Принимает параметр 
    *username*, т.к. для каждой панели настроек токенов выделяет отдельный URL /<*username*>.

    В случае обработки POST запроса, обрабатывает поля формы добавления 
    токена. Добавляет токен в БД в случае, если все поля формы были 
    заполнены верно.

    :param str username: имя пользователя
    """
    user = User.query.filter_by(
            username=username).first()
    created_jwt = None

    if request.method == 'POST':
        if functools.reduce(lambda prev, el: prev and bool(el), request.form.values()):
            expire_date = datetime.strptime(request.form['expire_date'], '%Y-%m-%d')
            now = datetime.now()
            created_jwt = user.encode_auth_token(expire_date - now)
            token = Token(user_id=user.id, token=created_jwt, name=request.form['token_name'], iat=now, exp=expire_date)
            db.session.add(token)
            db.session.commit()

    tokens = Token.query.filter_by(user_id=user.id).all()

    return render_template('user_panel/settings_tokens.html', 
            user=user, gravatar_avatar_url=gravatar_avatar_url, tokens=tokens, created_jwt=created_jwt)


@main.route('/')
def index():
    """Представление главной страницы. Возвращает страницу с шаблоном 
    index.html.
    """
    return render_template('index.html')

