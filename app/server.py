import time
import json
from pathlib import Path
from typing import Dict, Optional

from flask import session, request
from flask_socketio import Namespace, emit, join_room, leave_room

from backend.database.build_db import (
    get_db,
    get_map,
    save_match_state,
    load_latest_match_state,
    create_match as db_create_match,
    add_match_player,
)
from backend.game.engine import MatchEngine, MatchStatus, EventType
from backend.game.state import create_match, TimeControl, GameState as GameStateClass
from backend.game.parser import register_units
from backend.game.actions import set_unit_registry
from backend.game import fog


active_engines: Dict[int, MatchEngine] = {}          # match_id -> engine
player_match: Dict[str, int] = {}                    # sid -> match_id
player_slots: Dict[str, int] = {}                    # sid -> player_slot


# Absolute path so this works regardless of the process working directory.
_UNITS_DIR = Path(__file__).resolve().parent / "data" / "units"
unit_registry = register_units(str(_UNITS_DIR))
set_unit_registry(unit_registry)


def build_unit_catalog() -> dict:
    catalog: dict[str, list] = {}

    for definition in unit_registry.all():
        catalog.setdefault(definition.faction, []).append({
            "unit_type": definition.unit_type,
            "name": definition.name,
            "category": (
                definition.category.value
                if hasattr(definition.category, "value")
                else definition.category
            ),
            "cost": definition.price,
            "health": definition.health,
            "armor": definition.armor,
            "movement": definition.movement,
            "sight": definition.sight,
            "weapons": [
                {
                    "name": w.name,
                    "damage": w.damage,
                    "ap": w.ap,
                    "range": w.range,
                }
                for w in definition.weapons
            ],
        })

    return catalog


UNIT_CATALOG = build_unit_catalog()


def match_room(match_id: int) -> str:
    return f"match_{match_id}"


def player_room(match_id: int, player_slot: int) -> str:
    return f"match_{match_id}_player_{player_slot}"


def broadcast_to_match(
    match_id: int,
    event: str,
    data: dict,
    skip_sid: Optional[str] = None,
):
    
    emit(event, data, to=match_room(match_id), skip_sid=skip_sid)


def emit_fogged_state_to_players(match_id: int, engine: MatchEngine) -> None:
  
    state = engine.get_state()
    fog.update_all_fog(state)

    for player in state.players:
        slot = player.slot

        emit(
            "game_state",
            fog.state_to_player_view(state, slot),
            to=player_room(match_id, slot),
        )


def emit_game_started_to_players(match_id: int, engine: MatchEngine) -> None:
    """
    Sends the game_started event to each player with their own fog-filtered state.
    """
    state = engine.get_state()
    fog.update_all_fog(state)

    for player in state.players:
        slot = player.slot

        emit(
            "game_started",
            {
                "game_state": fog.state_to_player_view(state, slot),
                "unit_catalog": UNIT_CATALOG,
            },
            to=player_room(match_id, slot),
        )


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
        map_id = match_row["map_id"]
        time_control = match_row["time_control"]
        status = match_row["status"]

        player_specs = []
        for row in rows:
            if row["user_id"] is not None:
                player_specs.append({
                    "slot": row["slot"],
                    "user_id": row["user_id"],
                    "faction": row["faction"],
                    "color": row["color"],
                })

        player_specs.sort(key=lambda x: x["slot"])

        map_data = get_map(map_id)
        if not map_data:
            return None

        map_dict = json.loads(map_data["json_data"])

        from backend.game.state import GameMap

        game_map = GameMap.from_saved_map_dict(map_dict)

        if status != "waiting":
            snapshot = load_latest_match_state(match_id)

            if snapshot:
                game_state = GameStateClass.from_dict(snapshot)
                engine = MatchEngine(
                    game_state,
                    now_fn=time.time,
                    unit_registry=unit_registry,
                )
                engine.status = (
                    MatchStatus.IN_PROGRESS
                    if status == "in_progress"
                    else MatchStatus.ENDED
                )
                active_engines[match_id] = engine
                return engine

        if len(player_specs) < 2:
            return None

        tc = TimeControl.LIVE if time_control == "live" else TimeControl.ASYNC_24H

        state = create_match(
            match_id=match_id,
            map_id=map_id,
            game_map=game_map,
            player_specs=[
                {
                    "faction": p["faction"],
                    "user_id": p["user_id"],
                    "color": p["color"],
                }
                for p in player_specs
            ],
            time_control=tc,
            unit_registry=unit_registry,
        )

        engine = MatchEngine(state, unit_registry=unit_registry)
        active_engines[match_id] = engine
        return engine


class GameNamespace(Namespace):
    def on_connect(self):
        print(f"Client connected: {request.sid}")

    def on_disconnect(self):
        sid = request.sid

        match_id = player_match.pop(sid, None)
        player_slot = player_slots.pop(sid, None)

        if match_id is not None:
            leave_room(match_room(match_id), sid=sid)

            if player_slot is not None:
                leave_room(player_room(match_id, player_slot), sid=sid)

            broadcast_to_match(
                match_id,
                "player_disconnected",
                {"sid": sid},
                skip_sid=sid,
            )

        print(f"Client disconnected: {sid}")

    def on_create_match(self, data):
        sid = request.sid

        if sid in player_match:
            emit("error", {"message": "Already in a match"})
            return

        map_id = data.get("map_id")
        time_control = data.get("time_control", "live")
        user_id = session.get("user_id")

        if not user_id:
            emit("error", {"message": "Not logged in"})
            return

        match_id = db_create_match(map_id, time_control)

        add_match_player(
            match_id,
            slot=0,
            user_id=user_id,
            faction="presia",
            color="#367055",
        )

        player_match[sid] = match_id
        player_slots[sid] = 0

        join_room(match_room(match_id))
        join_room(player_room(match_id, 0))

        emit("match_created", {"match_id": match_id})

        emit("joined", {
            "match_id": match_id,
            "player_slot": 0,
            "game_state": None,   # no state until the match starts
            "unit_catalog": UNIT_CATALOG,
        })

    def on_join_match(self, data):
        sid = request.sid

        if sid in player_match:
            emit("error", {"message": "Already in a match"})
            return

        match_id = data.get("match_id")
        user_id = session.get("user_id")

        if not user_id or match_id is None:
            emit("error", {"message": "Missing match_id or not logged in"})
            return

        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            emit("error", {"message": "Invalid match_id"})
            return

        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT slot
                FROM match_players
                WHERE match_id = ? AND user_id = ?
                """,
                (match_id, user_id),
            )
            row = cur.fetchone()

            if row:
                player_slot = row["slot"]
            else:
                cur2 = conn.execute(
                    """
                    SELECT slot
                    FROM match_players
                    WHERE match_id = ?
                    """,
                    (match_id,),
                )
                taken = [r["slot"] for r in cur2.fetchall()]

                if 0 not in taken:
                    player_slot = 0
                elif 1 not in taken:
                    player_slot = 1
                else:
                    emit("error", {"message": "Match is full"})
                    return

                add_match_player(
                    match_id,
                    slot=player_slot,
                    user_id=user_id,
                    faction="doon" if player_slot == 1 else "presia",
                    color="#CBBD93" if player_slot == 1 else "#367055",
                )

        player_match[sid] = match_id
        player_slots[sid] = player_slot

        join_room(match_room(match_id))
        join_room(player_room(match_id, player_slot))

        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) as cnt
                FROM match_players
                WHERE match_id = ?
                """,
                (match_id,),
            )
            cnt = cur.fetchone()["cnt"]

        engine = get_or_create_engine(match_id)

        if engine is None:
            emit("joined", {
                "match_id": match_id,
                "player_slot": player_slot,
                "game_state": None,
                "unit_catalog": UNIT_CATALOG,
            })
            return

        # Two players are present. Start the match if it hasn't started yet.
        if cnt >= 2 and engine.get_status() == MatchStatus.WAITING:
            engine.start()

            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE matches
                    SET status = 'in_progress',
                        started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (match_id,),
                )

            # Save full server truth to DB.
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())

            # Emit fogged game_started payloads to each player.
            emit_game_started_to_players(match_id, engine)

            # Clear MATCH_STARTED / TURN_STARTED internal events so they do not
            # get drained during the first action later.
            engine.drain_events()

        emit("joined", {
            "match_id": match_id,
            "player_slot": player_slot,
            "game_state": fog.state_to_player_view(engine.get_state(), player_slot),
            "unit_catalog": UNIT_CATALOG,
        })

    def on_action(self, data):
        sid = request.sid

        match_id = player_match.get(sid)
        if not match_id:
            emit("error", {"message": "Not in a match"})
            return

        engine = active_engines.get(match_id)
        if not engine or engine.get_status() != MatchStatus.IN_PROGRESS:
            emit("error", {"message": "Match not active"})
            return

        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT slot
                FROM match_players
                WHERE match_id = ? AND user_id = ?
                """,
                (match_id, session.get("user_id")),
            )
            row = cur.fetchone()

            if not row:
                emit("error", {"message": "Not a player in this match"})
                return

            player_slot = row["slot"]

        action = data.get("action")

        if not action:
            emit("error", {"message": "Missing action"})
            return

        try:
            engine.submit_action(player_slot, action)
            events = engine.drain_events()

            # Save full state to DB. This is okay.
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())

            # Send fog-filtered state to each player.
            emit_fogged_state_to_players(match_id, engine)

            for ev in events:
                if ev.type == EventType.ACTION_APPLIED:
                    # Only send raw action result to the player who made it.
                    # Broadcasting this to everyone can leak hidden target info.
                    emit(
                        "action_applied",
                        ev.payload,
                        to=player_room(match_id, player_slot),
                    )

                elif ev.type == EventType.TURN_ENDED:
                    broadcast_to_match(match_id, "turn_changed", ev.payload)

                elif ev.type == EventType.MATCH_ENDED:
                    broadcast_to_match(match_id, "game_ended", ev.payload)

        except Exception as e:
            emit("error", {"message": str(e)})

    def on_end_turn(self, data):
        sid = request.sid

        match_id = player_match.get(sid)
        if not match_id:
            emit("error", {"message": "Not in a match"})
            return

        engine = active_engines.get(match_id)
        if not engine or engine.get_status() != MatchStatus.IN_PROGRESS:
            emit("error", {"message": "Match not active"})
            return

        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT slot
                FROM match_players
                WHERE match_id = ? AND user_id = ?
                """,
                (match_id, session.get("user_id")),
            )
            row = cur.fetchone()

            if not row:
                emit("error", {"message": "Not a player"})
                return

            player_slot = row["slot"]

        if player_slot != engine.current_player():
            emit("error", {"message": "Not your turn"})
            return

        try:
            engine.end_turn(player_slot)
            events = engine.drain_events()

            # Save full state to DB. This is okay.
            save_match_state(match_id, engine.state.turn, engine.state.to_dict())

            # Send fog-filtered state to each player.
            emit_fogged_state_to_players(match_id, engine)

            for ev in events:
                if ev.type == EventType.TURN_ENDED:
                    broadcast_to_match(match_id, "turn_changed", ev.payload)

                elif ev.type == EventType.MATCH_ENDED:
                    broadcast_to_match(match_id, "game_ended", ev.payload)

        except Exception as e:
            emit("error", {"message": str(e)})