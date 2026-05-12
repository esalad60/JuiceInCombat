from flask import Blueprint, render_template,request,redirect,url_for,session,flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

bp = Blueprint('auth', __name__, url_prefix='')
DB_FILE="../data/data.db"

@bp.get('/login')
def render_login():
    return render_template('login.html')

@bp.post('/login')
def post_login():
    usr=request.form.get('username')
    pw=request.form.get('password')
    db=sqlite3.connect(DB_FILE)
    c=db.cursor()
    c.execute("SELECT PASSWORD FROM USERS WHERE USERNAME = ?" (username,))
    login_deets=c.fetchone()
    if(user_data is not None):
        return "temp"
    
