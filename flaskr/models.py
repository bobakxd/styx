from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passw_hash = db.Column(db.String(512), unique=False, nullable=False) # SHA-256 пароля в hex формате
    
    def __repr__(self):
        return '<User %r>' % self.username


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_name = db.Column(db.String(80), nullable=False)
    
    def __repr__(self):
        return '<Project %r>' % self.project_name


class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    dir_name = db.Column(db.String(80), nullable=False)
    dir_parent_id = db.Column(db.Integer) # ссылка на запись из той же таблицы
    git_hash = db.Column(db.String(320), nullable=False) # Git использует SHA-1 и колонка хранит значения в hex формате

    def __repr__(self):
        return '<Directory %r>' % self.dir_name


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dir_id = db.Column(db.Integer, db.ForeignKey('directory.id'), nullable=False)
    file_name = db.Column(db.String(80), nullable=False)
    git_hash = db.Column(db.String(320), nullable=False) # Git использует SHA-1 и колонка хранит значения в hex формате

    def __repr__(self):
        return '<File %r>' % self.file_name

