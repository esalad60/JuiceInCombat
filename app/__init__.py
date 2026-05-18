import os
from flask import Flask, send_from_directory, session, render_template, redirect, url_for
from flask_socketio import SocketIO

BASE_DIR = os.path.dirname(__file__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "gabagoobakey"

socketio = SocketIO(app, cors_allowed_origins="*")

from backend.database import build_db
from backend.routes.auth import bp as auth_bp
app.register_blueprint(auth_bp, url_prefix="")

@app.route("/frontend/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, "frontend/static"), filename)

#@app.route("/")
#def home():
    #return serve_static("index.html")


@app.route("/")
def render_homepage():
    if session.get("username"):
        return render_template("home.html")
    else:
        return redirect(url_for("auth.render_login"))

@app.route("/login")
def login_page():
    return serve_static("login.html")

import server

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
