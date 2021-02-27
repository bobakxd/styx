"""Модуль **main** содержит основные представление (view), которые не 
выполняет специфичных функций, например, главная страница.
"""
from flask import Blueprint
from flask import render_template
from flask_login import login_required

#: main - это Blueprint, который содержит представления данного модуля.
#:
#: Для данного Blueprint'a статическая директория и директория для 
#: шаблонов указаны корневеные (./static и ./templates).
main = Blueprint('main', __name__, static_folder='static', 
        template_folder='templates')

@main.route('/<username>')
@login_required
def user_panel(username):
    """Представление (view) c главной панелью пользователя.

    Принимает параметр *username*, т.к. для каждой панели пользователя 
    выделяет отдельный URL /<*username*>.

    :param str username: имя пользователя
    """
    return 'Вы успешно авторизовались!'


@main.route('/')
def index():
    """Представление главной страницы. Возвращает страницу с шаблоном 
    index.html.
    """
    return render_template('index.html')

