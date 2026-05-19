import random
from flask_socketio import join_room, leave_room, emit
from flask import request

from . import socketio

# rooms[room_code] = { "owner": sid, "members": [sid, ...], "turn": sid | None, "board": [[tile, ...], ...] }
rooms: dict[str, dict] = {}
player_room: dict[str, str] = {}


class Unit:
    def __repr__(self):
        return f"Unit({self.__dict__})"


def new_board(rows: int = 10, cols: int = 10) -> list:
    return [
        [{"terrain": "plains", "unit": None} for _ in range(cols)]
        for _ in range(rows)
    ]


def new_room(owner_sid: str) -> dict:
    return {
        "owner":     owner_sid,
        "members":   [owner_sid],
        "turn":      None,
        "board": new_board(),
    }


def new_room_code() -> str:
    while True:
        code = str(random.randint(100000, 999999))
        if code not in rooms:
            return code


def other_player(room: dict, sid: str) -> str | None:
    others = [m for m in room["members"] if m != sid]
    return others[0] if others else None


def apply_fog(board: list, viewer_sid: str) -> list:
    return board


@socketio.on("create_room")
def on_create_room():
    sid = request.sid

    if sid in player_room:
        emit("room_error", {"message": "You are already in a room."})
        return

    room_code = new_room_code()
    rooms[room_code] = new_room(sid)
    player_room[sid] = room_code
    join_room(room_code)
    print(room_code);
    emit("room_created", {"room_code": room_code})


@socketio.on("join_room")
def on_join_room(data):
    sid = request.sid

    if sid in player_room:
        emit("room_error", {"message": "You are already in a room."})
        return

    room_code = data.get("room_code", "").strip()

    if room_code not in rooms:
        emit("room_error", {"message": f"Room '{room_code}' does not exist."})
        return

    room = rooms[room_code]

    if len(room["members"]) >= 2:
        emit("room_error", {"message": "Room is full."})
        return

    room["members"].append(sid)
    player_room[sid] = room_code
    join_room(room_code)
    room["turn"] = room["owner"]

    emit("room_joined", {"room_code": room_code})
    emit("player_joined", {"room_code": room_code}, to=room_code, skip_sid=sid)
    notify_turn(room_code)


@socketio.on("delete_room")
def on_delete_room():
    sid = request.sid
    room_code = player_room.get(sid)

    if room_code is None or sid != rooms[room_code]["owner"]:
        emit("room_error", {"message": "You are not in a room or are not the owner."})
        return

    emit("room_deleted", {"room_code": room_code}, to=room_code)
    close_room(room_code)


@socketio.on("submit_move")
def on_submit_move(data):
    sid = request.sid
    room_code = player_room.get(sid)

    if room_code is None:
        emit("move_error", {"message": "You are not in a room."})
        return

    room = rooms[room_code]

    if room["turn"] != sid:
        emit("move_error", {"message": "It is not your turn."})
        return

    fog_board = apply_fog(room["board"], sid)
    emit("board_update", {"board": fog_board})


@socketio.on("end_turn")
def on_end_turn():
    sid = request.sid
    room_code = player_room.get(sid)

    if room_code is None:
        emit("turn_error", {"message": "You are not in a room."})
        return

    room = rooms[room_code]

    if room["turn"] != sid:
        emit("turn_error", {"message": "It is not your turn."})
        return

    room["turn"] = other_player(room, sid)
    notify_turn(room_code)


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_code = player_room.get(sid)

    if room_code is None or room_code not in rooms:
        return

    room = rooms[room_code]

    if sid == room["owner"]:
        emit(
            "room_deleted",
            {"room_code": room_code, "reason": "owner_left"},
            to=room_code,
        )
        close_room(room_code)
    else:
        room["members"].remove(sid)
        del player_room[sid]
        room["turn"] = None
        emit(
            "player_disconnected",
            {"sid": sid, "room_code": room_code},
            to=room_code,
        )


def notify_turn(room_code: str):
    room = rooms[room_code]
    active_sid = room["turn"]
    if active_sid:
        socketio.emit("your_turn", {"room_code": room_code}, to=active_sid)


def close_room(room_code: str):
    if room_code not in rooms:
        return
    for member_sid in rooms[room_code]["members"]:
        leave_room(room_code, sid=member_sid)
        player_room.pop(member_sid, None)
    del rooms[room_code]
