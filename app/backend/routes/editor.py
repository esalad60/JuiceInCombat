from flask import Blueprint, session, redirect, url_for

bp = Blueprint('editor', __name__, url_prefix='/editor')


@bp.get('/')
def editor_page():
    if not session.get('is_admin'):
        return redirect(url_for('lobby.lobby_page'))
    return "Editor not yet implemented", 200