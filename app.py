import random

from flask import Flask, render_template, session, url_for, request, redirect
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")
online_users = {}


@app.route('/', methods=["POST", "GET"])
def index():
    if request.method == "POST":
        fight = [request.form.get("reaction-hit1"), request.form.get("reaction-hit2"),
                 request.form.get("reaction-hit3")]
        flight = [request.form.get("reaction-run1"), request.form.get("reaction-run2"),
                  request.form.get("reaction-run3")]
        fight = sum(list(map(lambda x: 1 if x else 0, fight)))
        flight = sum(list(map(lambda x: 1 if x else 0, flight)))
        session["character"] = {
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "insomnia": request.form.get("insomnia"),
            "recent-event": request.form.get("recent-event"),
            "appearance": request.form.get("appearance"),
            "true-self": request.form.get("true-self"),
            "path": request.form.get("path"),
            "madness-skill": request.form.get("madness-skill"),
            "exhaustion-skill": request.form.get("exhaustion-skill"),
            "madness": 0,
            "discipline": 3,
            "exhaustion": 0,
            "fight": fight,
            "flight": flight
        }

    if "master" not in session:
        session["master"] = False

    return render_template("index.html", context=session.get("character"))


@app.route('/character-sheet')
def character_sheet():
    return render_template("character_sheet.html")


@app.route("/master")
def master():
    session["master"] = True
    session["coins"] = {
        "hope": 0,
        "despair": 0
    }
    return redirect("/game")


@app.route("/game")
def game():
    character = session.get("character")
    if not character:
        return redirect("/character-sheet")
    players = [user for user in online_users.values() if not user.get("is_master", False)]
    return render_template("game.html", character=character, players=players)


@socketio.on("connect")
def on_connect():
    char = session.get("character")
    is_master = session.get("master", False)
    if char and isinstance(char, dict):
        char_data = char.copy()
        char_data["is_master"] = is_master
        char_data["sid"] = request.sid

        online_users[request.sid] = char_data

        players = [user for user in online_users.values() if not user.get("is_master", False)]
        emit("update_players", players, broadcast=True)
    if is_master:
        coins = session.get("coins", {"hope": 0, "despair": 0})
        emit("update_coins", coins)


@socketio.on("disconnect")
def on_disconnect():
    if request.sid in online_users:
        del online_users[request.sid]
        players = [user for user in online_users.values() if not user.get("is_master", False)]
        emit("update_players", players, broadcast=True)


@socketio.on("update_character")
def handle_update_character(data):
    if request.sid in online_users:
        character = online_users[request.sid]

        allowed_fields = ["madness", "discipline", "exhaustion", "fight", "flight"]
        for field in allowed_fields:
            if field in data:
                character[field] = data[field]

        if "character" in session:
            for field in allowed_fields:
                if field in data:
                    session["character"][field] = data[field]
        if not session.modified:
            session.modified = True

        players = [user for user in online_users.values() if not user.get("is_master", False)]
        emit("update_players", players, broadcast=True)


@socketio.on('roll_dice')
def handle_roll_dice(data):
    current_roll = {}
    char = session.get("character")
    is_master = session.get("master", False)
    player_name = char.get("name", "Аноним") if char else "Аноним"

    if is_master:
        yellow_dice = data.get('yellow', 1)
        yellow_dice = max(1, min(15, yellow_dice))

        results = [random.randint(1, 6) for _ in range(yellow_dice)]
        results.sort()
        current_roll = {
            'type': 'yellow',
            'player_name': player_name,
            'dice_count': yellow_dice,
            'results': results
        }
    else:
        white_dice = char.get("discipline", 3)
        red_dice = char.get("madness", 0) + data.get('red_extra', 0)
        black_dice = char.get("exhaustion", 0) + data.get('black_extra', 0)

        white_results = [random.randint(1, 6) for _ in range(white_dice)]
        red_results = [random.randint(1, 6) for _ in range(red_dice)]
        black_results = [random.randint(1, 6) for _ in range(black_dice)]

        white_results.sort()
        red_results.sort()
        black_results.sort()

        current_roll = {
            'type': 'player',
            'player_name': player_name,
            'white_dice': white_dice,
            'red_dice': red_dice,
            'black_dice': black_dice,
            'white_results': white_results,
            'red_results': red_results,
            'black_results': black_results
        }
    if current_roll:
        emit('dice_rolled', current_roll, broadcast=True)


@socketio.on("update_coins")
def handle_update_coins(data):
    if not session.get("master", False):
        return

    session["coins"]["hope"] = max(0, data.get("hope", session["coins"]["hope"]))
    session["coins"]["despair"] = max(0, data.get("despair", session["coins"]["despair"]))

    emit("update_coins", {"hope": session["coins"]["hope"], "despair": session["coins"]["despair"]}, broadcast=True)


@socketio.on("request_coins")
def handle_request_coins():
    coins = session.get("coins", {"hope": 0, "despair": 0})
    emit("update_coins", coins)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5100)
