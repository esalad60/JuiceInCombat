from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from backend.database.build_db import get_db, get_user_by_username

bp = Blueprint('auth', __name__, url_prefix='')

@bp.get('/register')
def register_get():
    return render_template('register.html')

@bp.post('/register')
def post_register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirmpwd', '')

    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect(url_for('auth.register_get'))
    if password != confirm:
        flash('Passwords do not match', 'error')
        return redirect(url_for('auth.register_get'))
    if len(password) < 4:
        flash('Password must be at least 4 characters', 'error')
        return redirect(url_for('auth.register_get'))

    existing = get_user_by_username(username)
    if existing:
        flash('Username already taken', 'error')
        return redirect(url_for('auth.register_get'))

    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash)
        )
        cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = cur.fetchone()[0]

    session.clear()
    session['user_id'] = user_id
    session['username'] = username
    flash('Account created successfully!', 'success')
    return redirect(url_for('lobby.lobby_page'))

@bp.get('/login')
def render_login():
    return render_template('login.html')

@bp.post('/login')
def post_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect(url_for('auth.render_login'))

    user = get_user_by_username(username)
    if user is None:
        flash('Username not found', 'error')
        return redirect(url_for('auth.render_login'))

    try:
        password_ok = check_password_hash(user['password'], password)
    except Exception:
        password_ok = False
    if not password_ok:
        flash('Invalid password', 'error')
        return redirect(url_for('auth.render_login'))

    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user['is_admin'])
    flash(f'Welcome back, {username}!', 'success')
    return redirect(url_for('lobby.lobby_page'))

@bp.get('/logout')
def render_logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.render_login'))
