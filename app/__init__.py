# Monkey-patch MUST happen before importing anything that uses sockets/threads.
import eventlet
eventlet.monkey_patch()

import os
from pathlib import Path

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

from config import Config
from backend.database.build_db import init_db
from backend.routes import auth, lobby, game, editor, settings, api
from server import GameNamespace

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    static_folder=str(BASE_DIR  / 'static'),
    template_folder=str(BASE_DIR / 'templates'),
)
app.config.from_object(Config)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
)

init_db()

app.register_blueprint(auth.bp)
app.register_blueprint(lobby.bp)
app.register_blueprint(game.bp)
app.register_blueprint(editor.bp)
app.register_blueprint(settings.bp)
app.register_blueprint(api.bp)

socketio.on_namespace(GameNamespace('/game'))


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def not_found(e):
    return "Not found", 404


@app.errorhandler(500)
def server_error(e):
    return "Server error", 500


if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG,
        use_reloader=False,  # reloader + eventlet + module-level state don't mix well
        #allow_unsafe_werkzeug=True,
    )
