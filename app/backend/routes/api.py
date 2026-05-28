from flask import Blueprint, jsonify, session

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.get('/whoami')
def whoami():
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False),
    })