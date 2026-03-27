from flask import Blueprint, request, render_template, session, redirect, url_for, flash, jsonify
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
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
            cur.execute("SELECT admin_id, password FROM administrador WHERE username = %s", (username,))
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
    # After leaving admin area, send user back to public home instead of login
    return redirect(url_for('admin.home'))


@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = (request.form.get('current_password') or '').strip()
    new_password = (request.form.get('new_password') or '').strip()
    confirm_password = (request.form.get('confirm_password') or '').strip()
    admin_id = session.get('admin_id')

    if not current_password or not new_password or not confirm_password:
        return jsonify({"success": False, "error": "Preencha todos os campos."}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "error": "A nova password e a confirmação não coincidem."}), 400

    if len(new_password) < 4:
        return jsonify({"success": False, "error": "A nova password tem de ter pelo menos 4 caracteres."}), 400

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("SELECT password FROM administrador WHERE admin_id = %s", (admin_id,))
        row = cur.fetchone()

        if not row or not row[0] or not check_password_hash(row[0], current_password):
            return jsonify({"success": False, "error": "A password atual está incorreta."}), 400

        new_password_hash = generate_password_hash(
            new_password,
            method="pbkdf2:sha256",
            salt_length=16,
        )
        cur.execute(
            "UPDATE administrador SET password = %s WHERE admin_id = %s",
            (new_password_hash, admin_id),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Password alterada com sucesso."})
    finally:
        cur.close()
        conn.close()
