from flask import Blueprint, render_template, session, redirect, url_for, flash, request

bp = Blueprint('game', __name__)


@bp.get('/game/<int:match_id>')
def game_page(match_id):
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('auth.render_login'))
    return render_template('game.html', match_id=match_id)
  
@bp.route("/win/<int:match_id>/<int:winner_slot>")
def win_page(match_id, winner_slot):
    return render_template(
        "win.html",
        match_id=match_id,
        winner_slot=winner_slot,
    )