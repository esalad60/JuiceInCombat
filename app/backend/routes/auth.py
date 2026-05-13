from flask import Blueprint, render_template,request,redirect,url_for,session,flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

bp = Blueprint('auth', __name__, url_prefix='')
DB_FILE="../data/data.db"

@bp.get('/register')
def register_get():
    return render_template('register.html')

@bp.post('/register')
def post_register():
    username = request.form.get('username')
    password = request.form.get('password')
    confirmpwd = request.form.get('confirmpwd')
    if (password != confirmpwd):
        flash('Passwords must match', 'error')
        return redirect(url_for('auth.register_get'))
    db = sqlite3.connect(DB_FILE)
    c = db.cursor()
    c.execute("SELECT * FROM USERS WHERE USERNAME = ?", (username,))
    user_exists = c.fetchone()
    if user_exists:
        flash('Username already taken', 'error')
        db.close()
        return redirect(url_for('auth.register_get'))
    hashword = generate_password_hash(password)
    c.execute("INSERT INTO USERS (username, password) VALUES (?, ?)", (username, hashword))
    db.commit()
    db.close()
    session["username"] = username
    flash('Account registered successfully!', 'success')
    return redirect(url_for('render_homepage'))

@bp.get('/login')
def render_login():
    return render_template('login.html')

@bp.post('/login')
def post_login():
    username=request.form.get('username')
    password=request.form.get('password')
    db=sqlite3.connect(DB_FILE)
    c=db.cursor()
    c.execute("SELECT PASSWORD FROM USERS WHERE USERNAME = ?", (username,))
    login_deets=c.fetchone()
    if(login_deets is not None):
        hashword=login_deets[0]
        if (check_password_hash(hashword,password)):
          flash('Logged in successfully!', 'success')
          session['username']=username
          db.close()
          return redirect(url_for('render_homepage'))
        else:
            flash('Invalid password', 'error')
    else:
        flash("Username incorrect or not found", 'error')
    db.close()
    return redirect(url_for('auth.render_login'))
    
@bp.get('/logout')
def render_logout():
    session.pop('username', None)
    flash('Logout successful', 'success')
    return redirect(url_for('auth.render_login'))