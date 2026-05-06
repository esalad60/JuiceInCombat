import random
from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room, emit, request as socketio_request

app = Flask(__name__)
@app.route("/")
def home():
    return "page is up"

if __name__ == "__main__":
    app.debug = True
    app.run()
