import random
import os
from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask import request as socketio_request
from flask import send_from_directory
from app.routes.auth import bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "gabagoobakey"
socketio = SocketIO(app, cors_allowed_origins="*")
BASE_DIR = os.path.dirname(__file__)

app.register_blueprint(user_bp, url_prefix='')

rooms = {}

class Unit:
    def __init__(self):
        pass

    def __repr__(self):
        return f"Unit({self.__dict__})"

def make_room(owner_sid, rows=10, cols=10):
    gamestate = [
        [{"terrain": "plains", "unit": None} for _ in range(cols)]
        for _ in range(rows)
    ]
    return {
        "owner": owner_sid,
        "members": [owner_sid],
        "gamestate": gamestate
    }

def generate_room_code():
    while True:
        code = str(random.randint(100000, 999999))
        if code not in rooms:
            return code

def check_join_room(room_code, sid):
    if room_code not in rooms:
        return False, f"Room '{room_code}' does not exist."
    if sid in rooms[room_code]["members"]:
        return False, "You're already in this room."
    return True, None

@socketio.on("create_room")
def handle_create_room():
    room_code = generate_room_code()
    rooms[room_code] = make_room(socketio_request.sid)
    join_room(room_code)
    emit("room_created", {"room_code": room_code})

@socketio.on("join_room")
def handle_join_room(data):
    room_code = data.get("room_code", "").strip()
    allowed, reason = check_join_room(room_code, socketio_request.sid)
    if not allowed:
        emit("room_error", {"message": reason})
        return
    rooms[room_code]["members"].append(socketio_request.sid)
    join_room(room_code)
    emit("room_joined", {"room_code": room_code})
    emit("player_joined", {"room_code": room_code}, to=room_code, skip_sid=socketio_request.sid)

@socketio.on("delete_room")
def handle_delete_room(data):
    room_code = data.get("room_code", "").strip()
    if room_code not in rooms or socketio_request.sid != rooms[room_code]["owner"]:
        emit("room_error", {"message": "Room not found or you are not a member."})
        return
    emit("room_deleted", {"room_code": room_code}, to=room_code)
    for sid in rooms[room_code]["members"]:
        leave_room(room_code, sid=sid)
    del rooms[room_code]

@socketio.on("disconnect")
def handle_disconnect():
    sid = socketio_request.sid
    for room_code in list(rooms.keys()):
        if room_code not in rooms:
            continue
        if sid not in rooms[room_code]["members"]:
            continue
        if sid == rooms[room_code]["owner"]:
            emit("room_deleted", {"room_code": room_code, "reason": "owner_left"}, to=room_code)
            for member_sid in rooms[room_code]["members"]:
                leave_room(room_code, sid=member_sid)
            del rooms[room_code]
        else:
            rooms[room_code]["members"].remove(sid)
            emit("player_disconnected", {"sid": sid, "room_code": room_code}, to=room_code)

@app.route("/frontend/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, "frontend/static"), filename)

@app.route("/")
def home():
    return serve_static("index.html")

@app.route("/login")


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
