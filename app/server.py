import time
import json
from pathlib import Path
from typing import Dict, Optional

from flask import session, request
from flask_socketio import Namespace, emit, join_room, leave_room

from backend.database.build_db import (
    get_db, get_map, save_match_state, load_latest_match_state,
    create_match as db_create_match, add_match_player
)
from backend.game.engine import MatchEngine, MatchStatus, EventType
from backend.game.state import create_match, TimeControl, GameState as GameStateClass
from backend.game.parser import register_units
from backend.game.actions import set_unit_registry

active_engines: Dict[int, MatchEngine] = {}          # match_id -> engine
player_match: Dict[str, int] = {}                    # sid -> match_id

_UNITS_DIR = Path(__file__).resolve().parent / "data" / "units"
unit_registry = register_units(str(_UNITS_DIR))
set_unit_registry(unit_registry)

def get_or_create_engine(match_id: int) -> Optional[MatchEngine]:
    if match_id in active_engines:
        return active_engines[match_id]

    with get_db() as conn:
        cur = conn.execute("""
            SELECT m.id, m.map_id, m.time_control, m.status,
                   mp.user_id, mp.slot, mp.faction, mp.color
            FROM matches m
            LEFT JOIN match_players mp ON m.id = mp.match_id
            WHERE m.id = ?
        """, (match_id,))
        rows = cur.fetchall()
        if not rows:
            return None

        match_row = rows[0]
        map_id = match_row['map_id']
        time_control = match_row['time_control']
        status = match_row['status']

        player_specs = []
        for row in rows:
            if row['user_id'] is not None:
                player_specs.append({
                    'slot': row['slot'],
                    'user_id': row['user_id'],
                    'faction': row['faction'],
                    'color': row['color']
                })
        player_specs.sort(key=lambda x: x['slot'])

        map_data = get_map(map_id)
        if not map_data:
            return None
        map_dict = json.loads(map_data['json_data'])
        from backend.game.state import GameMap
        game_map = GameMap.from_saved_map_dict(map_dict)

        if status != 'waiting':
            snapshot = load_latest_match_state(match_id)
            if snapshot:
                game_state = GameStateClass.from_dict(snapshot)
                engine = MatchEngine(game_state, now_fn=time.time, unit_registry=unit_registry)
                engine.status = MatchStatus.IN_PROGRESS if status == 'in_progress' else MatchStatus.ENDED
                active_engines[match_id] = engine
                return engine

        if len(player_specs) < 2:
            return None

        tc = TimeControl.LIVE if time_control == 'live' else TimeControl.ASYNC_24H
        state = create_match(
            match_id=match_id,
            map_id=map_id,
            game_map=game_map,
            player_specs=[{'faction': p['faction'], 'user_id': p['user_id'], 'color': p['color']} for p in player_specs],
            time_control=tc,
            unit_registry=unit_registry
        )
        engine = MatchEngine(state, unit_registry=unit_registry)
        active_engines[match_id] = engine
        return engine

def broadcast_to_match(match_id: int, event: str, data: dict, skip_sid: Optional[str] = None):
    room = f"match_{match_id}"
    emit(event, data, to=room, skip_sid=skip_sid)

class GameNamespace(Namespace):
    def on_connect(self):
        print(f"Client connected: {request.sid}")

    def on_disconnect(self):
        sid = request.sid
        match_id = player_match.pop(sid, None)
        if match_id:
            leave_room(f"match_{match_id}", sid=sid)
            broadcast_to_match(match_id, 'player_disconnected', {'sid': sid}, skip_sid=sid)
        print(f"Client disconnected: {sid}")

    def on_create_match(self, data):
        sid = request.sid
        if sid in player_match:
            emit('error', {'message': 'Already in a match'})
            return

        map_id = data.get('map_id')
        time_control = data.get('time_control', 'live')
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not logged in'})
            return

        match_id = db_create_match(map_id, time_control)
        add_match_player(match_id, slot=0, user_id=user_id, faction='presia', color='#367055')

        player_match[sid] = match_id
        join_room(f"match_{match_id}")

        emit('match_created', {'match_id': match_id})
        emit('joined', {
            'match_id': match_id,
            'player_slot': 0,
            'game_state': None,   # no state until the match starts
        })

    def on_join_match(self, data):
        sid = request.sid
        if sid in player_match:
            emit('error', {'message': 'Already in a match'})
            return

        match_id = data.get('match_id')
        user_id = session.get('user_id')
        if not user_id or match_id is None:
            emit('error', {'message': 'Missing match_id or not logged in'})
            return

        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            emit('error', {'message': 'Invalid match_id'})
            return

        # Register this user into a slot (or find their existing slot).
        with get_db() as conn:
            cur = conn.execute("SELECT slot FROM match_players WHERE match_id = ? AND user_id = ?", (match_id, user_id))
            row = cur.fetchone()
            if row:
                player_slot = row['slot']
            else:
                cur2 = conn.execute("SELECT slot FROM match_players WHERE match_id = ?", (match_id,))
                taken = [r['slot'] for r in cur2.fetchall()]
                if 0 not in taken:
                    player_slot = 0
                elif 1 not in taken:
                    player_slot = 1
                else:
                    emit('error', {'message': 'Match is full'})
                    return
                add_match_player(match_id, slot=player_slot, user_id=user_id,
                                 faction='doon' if player_slot == 1 else 'presia',
                                 color='#CBBD93' if player_slot == 1 else '#367055')

        player_match[sid] = match_id
        join_room(f"match_{match_id}")

        # How many players are now in the match?
        with get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) as cnt FROM match_players WHERE match_id = ?", (match_id,))
            cnt = cur.fetchone()['cnt']

        engine = get_or_create_engine(match_id)

        # Still waiting for an opponent — no engine yet. Tell the client to wait.
        if engine is None:
            emit('joined', {
                'match_id': match_id,
                'player_slot': player_slot,
                'game_state': None,
            })
            return

        # Two players are present. Start the match if it hasn't started yet.
        if cnt >= 2 and engine.get_status() == MatchStatus.WAITING:
            engine.start()
            with get_db() as conn:
                conn.execute(
                    "UPDATE matches SET status = 'in_progress', started_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (match_id,))
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())
            broadcast_to_match(match_id, 'game_started', {'game_state': engine.get_state().to_dict()})

        emit('joined', {
            'match_id': match_id,
            'player_slot': player_slot,
            'game_state': engine.get_state().to_dict()
        })

    def on_action(self, data):
        sid = request.sid
        match_id = player_match.get(sid)
        if not match_id:
            emit('error', {'message': 'Not in a match'})
            return

        engine = active_engines.get(match_id)
        if not engine or engine.get_status() != MatchStatus.IN_PROGRESS:
            emit('error', {'message': 'Match not active'})
            return

        with get_db() as conn:
            cur = conn.execute("SELECT slot FROM match_players WHERE match_id = ? AND user_id = ?",
                               (match_id, session.get('user_id')))
            row = cur.fetchone()
            if not row:
                emit('error', {'message': 'Not a player in this match'})
                return
            player_slot = row['slot']

        action = data.get('action')
        if not action:
            emit('error', {'message': 'Missing action'})
            return

        try:
            engine.submit_action(player_slot, action)
            events = engine.drain_events()
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())
            broadcast_to_match(match_id, 'game_state', engine.state.to_dict())
            for ev in events:
                if ev.type == EventType.ACTION_APPLIED:
                    broadcast_to_match(match_id, 'action_applied', ev.payload)
                elif ev.type == EventType.TURN_ENDED:
                    broadcast_to_match(match_id, 'turn_changed', ev.payload)
                elif ev.type == EventType.MATCH_ENDED:
                    broadcast_to_match(match_id, 'game_ended', ev.payload)
        except Exception as e:
            emit('error', {'message': str(e)})

    def on_end_turn(self, data):
        sid = request.sid
        match_id = player_match.get(sid)
        if not match_id:
            emit('error', {'message': 'Not in a match'})
            return

        engine = active_engines.get(match_id)
        if not engine or engine.get_status() != MatchStatus.IN_PROGRESS:
            emit('error', {'message': 'Match not active'})
            return

        with get_db() as conn:
            cur = conn.execute("SELECT slot FROM match_players WHERE match_id = ? AND user_id = ?",
                               (match_id, session.get('user_id')))
            row = cur.fetchone()
            if not row:
                emit('error', {'message': 'Not a player'})
                return
            player_slot = row['slot']

        if player_slot != engine.current_player():
            emit('error', {'message': 'Not your turn'})
            return

        try:
            engine.end_turn(player_slot)
            events = engine.drain_events()
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())
            # Send authoritative state first so clients recompute whose turn it
            # is correctly, then send the lightweight notifications.
            broadcast_to_match(match_id, 'game_state', engine.state.to_dict())
            for ev in events:
                if ev.type == EventType.TURN_ENDED:
                    broadcast_to_match(match_id, 'turn_changed', ev.payload)
                elif ev.type == EventType.MATCH_ENDED:
                    broadcast_to_match(match_id, 'game_ended', ev.payload)
        except Exception as e:
            emit('error', {'message': str(e)})