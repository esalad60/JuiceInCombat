from flask import Blueprint, render_template
from import *

bp = Blueprint("lobby", __name__, url_prefix="")

@bp.route("/room/<room_code>")
def room_page(room_code):


    room = rooms.get(room_code)

    if room is None:
        return "Room does not exist", 404

    players = room.get("players", [])

    Player1 = players[0] if len(players) > 0 else ""
    Player2 = players[1] if len(players) > 1 else ""

    return render_template("room.html", room_code=room_code, Player1=Player1, Player2=Player2)
