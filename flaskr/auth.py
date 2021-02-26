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

auth = Blueprint('auth', __name__, static_folder='static',
        template_folder='templates')

@auth.route('/signin')
def signin():
    return render_template('signin.html')


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
    if request.method == 'POST':
        if functools.reduce(lambda prev, el: prev and bool(el), 
                request.form.values()):
            if request.form['passw'] == request.form['repeat']:
                redirect = register_user(request.form['username'],
                        request.form['email'], request.form['passw'])
                if redirect:
                    return redirect
            else:
                flash('Введенные пароли не совпадают!')
        else:
            flash('Не все поля заполнены!')

    return render_template('signup.html', **request.form)

