from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import random
import string
import json

app = Flask(__name__)
app.secret_key = 'secret'
socketio = SocketIO(app, async_mode="threading")

rooms = {}

def generate_room_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route("/")
def home():
    return render_template("lobby.html")

@app.route("/create", methods=["POST"])
def create():
    room_code = generate_room_code()
    pseudo = request.form.get("pseudo", "Hôte")
    rooms[room_code] = {
        "players": {},
        "host": pseudo,
        "questions": [],
        "answered": set()
    }
    session["room"] = room_code
    session["username"] = pseudo
    session["is_host"] = True
    return redirect(url_for("game", room_code=room_code))

@app.route("/join", methods=["POST"])
def join():
    room_code = request.form["code"].upper()
    pseudo = request.form.get("pseudo", "Joueur")
    if room_code in rooms:
        session["room"] = room_code
        session["username"] = pseudo
        session["is_host"] = False
        return redirect(url_for("game", room_code=room_code))
    return "Salle introuvable", 404

@app.route("/game/<room_code>")
def game(room_code):
    if room_code not in rooms:
        return "Salle introuvable", 404
    with open("questions.json", "r", encoding="utf-8") as f:
        all_questions = json.load(f)
    return render_template("index.html", room_code=room_code, questions=all_questions)

@socketio.on("join-room")
def handle_join(data):
    room = data["room"]
    username = data["username"]
    join_room(room)
    rooms[room]["players"][username] = 0
    emit("update-players", rooms[room]["players"], to=room)

@socketio.on("start-game")
def handle_start_game(data):
    room = data["room"]
    with open("questions.json", "r", encoding="utf-8") as f:
        all_questions = json.load(f)
    selected = random.sample(all_questions, 5)
    rooms[room]["questions"] = selected
    rooms[room]["answered"] = set()
    emit("start-game", selected, to=room)

@socketio.on("validate-answer")
def handle_answer(data):
    room = data["room"]
    username = data["username"]
    correct = data["correct"]

    if correct:
        rooms[room]["players"][username] += 1
        emit("update-players", rooms[room]["players"], to=room)

    rooms[room]["answered"].add(username)
    answered_count = len(rooms[room]["answered"])
    total_players = len(rooms[room]["players"])
    emit("answer-count", {"answered": answered_count, "total": total_players}, to=room)

@socketio.on("next-question")
def handle_next_question(data):
    room = data["room"]
    index = data["index"]

    if index >= 5:
        emit("game-over", rooms[room]["players"], to=room)
    else:
        rooms[room]["answered"] = set()
        emit("load-question", {"index": index}, to=room)

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
