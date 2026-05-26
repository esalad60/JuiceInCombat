import random
from flask_socketio import join_room, leave_room, emit
from flask import request, session

from . import socketio

# rooms[room_code] = { "owner": sid, "members": [sid, ...], "turn": sid | None, "board": [[tile, ...], ...] }
rooms: dict[str, dict] = {}
player_room: dict[str, str] = {}


def new_board(rows: int = 10, cols: int = 10) -> list:
    return [
        [{"terrain": "plains", "unit": None} for _ in range(cols)]
        for _ in range(rows)
    ]


def new_room(owner_sid: str, owner_name: str) -> dict:
    return {
        "owner": owner_sid,
        "members": [owner_sid],
        "players": [owner_name],
        "turn": None,
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


# def apply_fog(board: list, viewer_sid: str) -> list:
#     fogboard = [[]]
#     range = 0 # placeholder because they dont tell me these things
#     for row in range(len(board)):
#         for col in range(len(board[row])):
#             fogboard[row][col] = Tile(
#             x = board[row][col].x # copy over attributes from previous board except fog status
#             y = board[row][col].y
#             terrain = board[row][col].terrain
#             is_trap = board[row][col].is_trap
#             faction = board[row][col].faction
#         )
#             if (board.is_occupied = True) and True: # condition: check range to see if fog covers. however this is a placeholder
#                 for row2 in range(len(board)):
#                     for col2 in range(len(board[row2])): # too lazy to calculate this so we're iterating across the entire board again
#                         if (range <= abs((row + col)-(row2+col2))) or fogboard[row2][col2]:
#                             fogboard[row2][col2].is_occupied = board[row2][col2].is_occupied
#                         else:
#                             fogboard[row2][col2].is_occupied = False
#     return board


@socketio.on("create_room")
def on_create_room():
    sid = request.sid

    if sid in player_room:
        emit("room_error", {"message": "You are already in a room."})
        return

    room_code = new_room_code()
    username = session.get("username", "Player 1")
    rooms[room_code] = new_room(sid, username)
    player_room[sid] = room_code
    join_room(room_code)
    print(room_code);
    emit("room_created", {
        "room_code": room_code,
        "redirect_url": f"/room/{room_code}"
    })


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
    username = session.get("username", "Player 2")

    if len(room["members"]) >= 2:
        emit("room_error", {"message": "Room is full."})
        return

    room["members"].append(sid)
    room["players"].append(username)
    player_room[sid] = room_code
    join_room(room_code)
    room["turn"] = room["owner"]

    emit("room_joined", {
        "room_code": room_code,
        "redirect_url": f"/room/{room_code}"
    })
    emit("player_joined", {"room_code": room_code}, to=room_code, skip_sid=sid)
    notify_turn(room_code)


@socketio.on("enter_room_page")
def on_enter_room_page(data):
    sid = request.sid
    room_code = data.get("room_code", "").strip()

    if room_code not in rooms:
        emit("room_error", {"message": "Room does not exist."})
        return

    room = rooms[room_code]
    username = session.get("username", "Player")

    if room["owner"] is None:
        room["owner"] = sid
        room["members"].insert(0, sid)
        player_room[sid] = room_code
        join_room(room_code)

        emit("room_state", {
            "room_code": room_code,
            "players": room["players"]
        })
        return

    if sid not in room["members"]:
        if len(room["members"]) < 2:
            room["members"].append(sid)

            if username not in room["players"]:
                room["players"].append(username)

            player_room[sid] = room_code
            join_room(room_code)
        else:
            emit("room_error", {"message": "Room is full."})
            return

    emit("room_state", {
        "room_code": room_code,
        "players": room["players"]
    })

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
        player_room.pop(sid, None)

        if sid in room["members"]:
            room["members"].remove(sid)

        room["owner"] = None
        return
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
