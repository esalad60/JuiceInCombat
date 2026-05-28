from flask import Blueprint, session, redirect, url_for

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.get('/')
def settings_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.render_login'))
    return "Settings not yet implemented", 200