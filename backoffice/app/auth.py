from flask import Blueprint, request, render_template, session, redirect, url_for, flash
from functools import wraps
from werkzeug.security import check_password_hash
from .db import get_conn

app = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def _wrap(*a, **k):
        if "admin_id" not in session:
            flash("Acesso negado! Faça login.", "error")
            return redirect(url_for("auth.login"))
        return f(*a, **k)
    return _wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            username = request.form['username']
            password = request.form['password']
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT admin_id, password FROM Administrador WHERE username = %s", (username,))
            admin = cur.fetchone()
            cur.close()
            conn.close()
            if admin and admin[1] and check_password_hash(admin[1], password):
                session['admin_id'] = admin[0]
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('admin.index'))
            else:
                flash('Username ou password incorretos!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('auth.login'))