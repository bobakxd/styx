"""Модуль **models** содержит объекты моделей для объектно-реляционного 
отображения (ORM) таблиц из БД. Также в некоторый моделях хранится 
дополнительная логика, например, в классе :class:`User` есть методы для 
работы с сессией пользователя.
"""
from flask_sqlalchemy import SQLAlchemy
from flask import current_app
import datetime
import jwt

db = SQLAlchemy()

class User(db.Model):
    """Модель пользователя, хранит свойства с информацией о пользователе:
    *id*, *username*, *email*, *passw_hash*.

    Также класс содержит методы для работы с текущей сессией пользователя: :meth:`get_id`, :meth:`set_authenticated`, :meth:`is_authenticated`, :meth:`encode_auth_token`, :meth:`decode_auth_token`.
    """
    #: id (*int*) - идентификатор пользователя
    id = db.Column(db.Integer, primary_key=True)
    #: username (*str*) - имя пользователя
    username = db.Column(db.String(80), unique=True, nullable=False)
    #: email (*str*) - email пользователя
    email = db.Column(db.String(120), unique=True, nullable=False)
    #: passw_hash (*str*) - пароль пользователя, хранится как хеш SHA-256 
    #: в hex формате
    passw_hash = db.Column(db.String(512), unique=False, nullable=False) # SHA-256 пароля в hex формате
    # registration_time (*DateTime*) - дата регистрации пользователя
    registration_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def is_active(self):
        """Возвращает всегда True, т.к. все пользователи активны."""
        return True

    def get_id(self):
        """Возвращает юникод идентификатор (*str*) пользователя."""
        return '%s<%d>' % (self.username, self.id)

    def is_authenticated(self):
        from flaskr import auth
        """Возвращает признак (*bool*) того, что пользователь аутентифицирован."""
        if self.get_id() in auth.get_sessions():
            return auth.get_sessions()[self.get_id()]
        return False

    def set_authenticated(self, value):
        from flaskr import auth
        """Возвращает признак (*bool*) того, что пользователь аутентифицирован."""
        """Устанавливает признак *value* аутентификации пользователя.

        :param bool value: признак аутентификации
        """
        auth.get_sessions()[self.get_id()] = value

    def is_anonymous(self):
        """Признак анонимности пользователя. Возвращает False, т.к. все 
        пользователи в БД - зарегистрированы.
        """
        return False

    def encode_auth_token(self, time_delta):
        """Создает и шифрует JSON веб-токен пользователя.

        :param time_delta: длительность действия токена
        :type time_delta: :class:`datetime.datetime`
        :returns: JSON веб-токен (JWT) в base64 формате
        :rtype: str
        """
        try:
            payload = {
                    'exp': datetime.datetime.utcnow() + time_delta,
                    'iat': datetime.datetime.utcnow(),
                    'sub': self.id
            }

            return jwt.encode(payload, current_app.config['SECRET_KEY'], 
                    algorithm='HS256')

        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """Дешифрует JSON веб-токен пользователя. Также функция проверяет 
        проверяет подпись токена и срок действия токена.

        :param auth_token: JSON веб-токен (JWT) в base64 формате
        :type auth_token: str
        :returns: имя пользователя токена или сообщение с ошибкой
        :rtype: str
        """
        try:
            payload = jwt.decode(auth_token, 
                    current_app.config['SECRET_KEY'])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Действие подписи закончилось. Пожалуйста, сгенерируете новый токен заново.'
        except jwt.InvalidTokenError:
            return 'Неверный токен. \
                    Попробуете аутентифицироваться заново.'
 
    def __repr__(self):
        return '<User %r>' % self.username


class Token(db.Model):
    """Модель токена, хранит свойства с информацией о веб-токене пользователя: *id*, *user_id*, *token*.
    """
    #: id (*int*) - идентификатор токена
    id = db.Column(db.Integer, primary_key=True)
    #: user_id (*int*) - идентификатор пользователя
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #: token (*str*) - зашифрованный веб-токен в base64 формате
    token = db.Column(db.String(8192), nullable=False)
    #: name (*str*) - название токена
    name = db.Column(db.String(80), nullable=False)
    # iat (*DateTime*) - дата создания токена 
    iat = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    # exp (*DateTime*) - дата окончания действия токена
    exp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return '<Token %r [ %r ]>' % (self.id, self.token)


class Project(db.Model):
    """Модель проект, хранит свойства с информацией о проекте пользователя
    : *id*, *user_id*, *project_name*.
    """
    #: id (*int*) - идентификатор проекта
    id = db.Column(db.Integer, primary_key=True)
    #: user_id (*int*) - идентификатор пользователя проекта
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    #: project_name (*str*) - название проекта
    project_name = db.Column(db.String(80), nullable=False)
    
    def __repr__(self):
        return '<Project %r>' % self.project_name


class Directory(db.Model):
    """Модель директории, хранит свойства с информацией о директории 
    внутри проекта: *id*, *project_id*, *dir_name*, *dir_parent_id*, 
    *git_hash*.
    """
    #: id (*int*) - идентификатор директории
    id = db.Column(db.Integer, primary_key=True)
    #: project_id (*int*) - идентификатор проекта директории
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    #: dir_name (*str*) - название директории
    dir_name = db.Column(db.String(80), nullable=False)
    #: dir_parent_id (*int*) - идентификатор директории-родителя
    dir_parent_id = db.Column(db.Integer) # ссылка на запись из той же таблицы
    #: git_hash (*str*) - Git хеш содержимого директории, SHA-1 в hex 
    #: формате
    git_hash = db.Column(db.String(320), nullable=False) # Git использует SHA-1 и колонка хранит значения в hex формате

    def __repr__(self):
        return '<Directory %r>' % self.dir_name


class File(db.Model):
    """Модель файла, хранит свойства с информацией о файле внутри проекта:
    *id*, *dir_id*, *file_name*, *git_hash*.
    """
    #: id (*int*) - идентификатор файла
    id = db.Column(db.Integer, primary_key=True)
    #: dir_id (*int*) - идентификатор директории файла
    dir_id = db.Column(db.Integer, db.ForeignKey('directory.id'), nullable=False)
    #: file_name (*str*) - имя файла
    file_name = db.Column(db.String(80), nullable=False)
    #: git_hash (*str*) - Git хеш содержимого файла, SHA-1 в hex формате
    git_hash = db.Column(db.String(320), nullable=False) # Git использует SHA-1 и колонка хранит значения в hex формате

    def __repr__(self):
        return '<File %r>' % self.file_name

