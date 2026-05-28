from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backend.database.build_db import (
    add_match_player,
    create_match,
    get_db,
    get_map,
    init_db,
    create_user,
)

bp = Blueprint('lobby', __name__, url_prefix='/lobby')

def require_login():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return False
    return True

def get_available_maps():
    with get_db() as conn:
        cur = conn.execute("SELECT id, name, width, height FROM maps ORDER BY name")
        rows = cur.fetchall()
        return [dict(row) for row in rows]

def get_waiting_matches():
    with get_db() as conn:
        cur = conn.execute("""
            SELECT m.id, m.map_id, m.time_control, m.status,
                   COUNT(mp.user_id) as player_count,
                   map.name as map_name
            FROM matches m
            JOIN maps map ON m.map_id = map.id
            LEFT JOIN match_players mp ON m.id = mp.match_id
            WHERE m.status = 'waiting'
            GROUP BY m.id
            HAVING player_count < 2
            ORDER BY m.created_at DESC
        """)
        rows = cur.fetchall()
        matches = []
        for row in rows:
            d = dict(row)
            d['player_count'] = d['player_count'] or 0
            matches.append(d)
        return matches

def get_user_matches(user_id):
    with get_db() as conn:
        cur = conn.execute("""
            SELECT m.id, m.map_id, m.time_control, m.status,
                   map.name as map_name,
                   (SELECT slot FROM match_players WHERE match_id = m.id AND user_id = ?) as my_slot
            FROM matches m
            JOIN maps map ON m.map_id = map.id
            JOIN match_players mp ON m.id = mp.match_id
            WHERE mp.user_id = ?
            ORDER BY m.created_at DESC
        """, (user_id, user_id))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

@bp.get('/')
def lobby_page():
    if not require_login():
        return redirect(url_for('auth.render_login'))
    
    waiting_matches = get_waiting_matches()
    my_matches = get_user_matches(session['user_id'])
    available_maps = get_available_maps()
    
    return render_template('lobby.html',
                         waiting_matches=waiting_matches,
                         my_matches=my_matches,
                         available_maps=available_maps)

@bp.post('/create')
def create_match_post():
    if not require_login():
        return redirect(url_for('auth.render_login'))
    
    map_id = request.form.get('map_id', type=int)
    time_control = request.form.get('time_control', 'live')
    
    if not map_id:
        flash('Please select a map', 'error')
        return redirect(url_for('lobby.lobby_page'))
    
    map_data = get_map(map_id)
    if not map_data:
        flash('Invalid map selection', 'error')
        return redirect(url_for('lobby.lobby_page'))

    match_id = create_match(map_id, time_control)

    add_match_player(match_id, slot=0, 
                     user_id=session['user_id'],
                     faction='presia',   # placeholder; could let player choose
                     color='#367055')
    
    flash(f'Match created! Join code: {match_id}', 'success')
    return redirect(url_for('lobby.lobby_page'))

@bp.post('/join/<int:match_id>')
def join_match(match_id):
    if not require_login():
        return redirect(url_for('auth.render_login'))
    
    # Check match exists and is waiting
    with get_db() as conn:
        cur = conn.execute("""
            SELECT m.id, m.status, COUNT(mp.user_id) as player_count
            FROM matches m
            LEFT JOIN match_players mp ON m.id = mp.match_id
            WHERE m.id = ?
            GROUP BY m.id
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            flash('Match not found', 'error')
            return redirect(url_for('lobby.lobby_page'))
        
        if match['status'] != 'waiting':
            flash('Match already started or ended', 'error')
            return redirect(url_for('lobby.lobby_page'))
        
        if match['player_count'] >= 2:
            flash('Match is full', 'error')
            return redirect(url_for('lobby.lobby_page'))
        
        # Check if user already in this match
        cur2 = conn.execute("SELECT 1 FROM match_players WHERE match_id = ? AND user_id = ?",
                           (match_id, session['user_id']))
        if cur2.fetchone():
            flash('You already joined this match', 'info')
            return redirect(url_for('game.game_page', match_id=match_id))
        
        # Determine next slot (0 or 1)
        cur_slots = conn.execute("SELECT slot FROM match_players WHERE match_id = ?", (match_id,))
        used_slots = {row['slot'] for row in cur_slots}
        next_slot = 0 if 0 not in used_slots else 1

        faction = 'presia' if next_slot == 0 else 'doon'
        color = '#367055' if next_slot == 0 else '#CBBD93'
        
        add_match_player(match_id, slot=next_slot,
                         user_id=session['user_id'],
                         faction=faction,
                         color=color)
        
        if match['player_count'] + 1 >= 2:
            conn.execute("UPDATE matches SET status = 'in_progress', started_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (match_id,))
            flash('Game starting...', 'success')
        else:
            flash('Waiting for another player...', 'success')
        
        return redirect(url_for('game.game_page', match_id=match_id))