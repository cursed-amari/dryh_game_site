import random
import uuid
from flask import Flask, render_template, request, redirect, make_response
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("secret_code")
socketio = SocketIO(app, cors_allowed_origins="*")

online_users = {}
master_data = {"coins": {"hope": 0, "despair": 0}}


def generate_token():
    return str(uuid.uuid4())


@app.route('/', methods=["POST", "GET"])
def index():
    if request.method == "POST":
        fight = [request.form.get("reaction-hit1"), request.form.get("reaction-hit2"),
                 request.form.get("reaction-hit3")]
        flight = [request.form.get("reaction-run1"), request.form.get("reaction-run2"),
                  request.form.get("reaction-run3")]
        fight = sum([1 for x in fight if x])
        flight = sum([1 for x in flight if x])

        token = generate_token()
        online_users[token] = {
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
            "flight": flight,
            "is_master": True if request.form.get("is_master") == "on" else False,
            "in_game": False
        }

        if online_users[token]["is_master"]:
            master_data["coins"] = {"hope": 0, "despair": 0}

        resp = make_response(redirect("/"))
        resp.set_cookie("auth_token", token, httponly=True)
        return resp

    token = request.cookies.get("auth_token")
    character = online_users.get(token) if token else None

    return render_template("index.html", context=character)


@app.route('/character-sheet')
def character_sheet():
    return render_template("character_sheet.html")


@app.route("/game")
def game():
    token = request.cookies.get("auth_token")
    if not token or token not in online_users:
        return redirect("/character-sheet")

    character = online_users[token]
    players = [u for t, u in online_users.items()]
    return render_template("game.html", character=character, players=players)


@socketio.on("connect")
def on_connect():
    token = request.cookies.get("auth_token")
    if not token or token not in online_users:
        return False

    online_users[token]["in_game"] = True
    char_data = online_users[token]
    char_data["sid"] = request.sid

    players = [u for u in online_users.values() if u["in_game"]]
    emit("update_players", players, broadcast=True)

    if char_data.get("is_master", False):
        emit("update_coins", master_data["coins"])


@socketio.on("disconnect")
def on_disconnect():
    token = request.cookies.get("auth_token")
    online_users[token]["in_game"] = False
    players = [u for u in online_users.values() if u["in_game"]]
    emit("update_players", players, broadcast=True)


@socketio.on("update_character")
def handle_update_character(data):
    token = request.cookies.get("auth_token")
    if not token or token not in online_users:
        return

    character = online_users[token]
    allowed_fields = ["madness", "discipline", "exhaustion", "fight", "flight"]
    for field in allowed_fields:
        if field in data:
            character[field] = data[field]

    players = [u for u in online_users.values() if u["in_game"]]
    emit("update_players", players, broadcast=True)


@socketio.on('roll_dice')
def handle_roll_dice(data):
    token = request.cookies.get("auth_token")
    if not token or token not in online_users:
        return

    char = online_users[token]
    is_master = char.get("is_master", False)
    player_name = char.get("name", "Аноним")

    if is_master:
        yellow_dice = max(1, min(15, data.get('yellow', 1)))
        results = sorted([random.randint(1, 6) for _ in range(yellow_dice)])
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

        white_results = sorted([random.randint(1, 6) for _ in range(white_dice)])
        red_results = sorted([random.randint(1, 6) for _ in range(red_dice)])
        black_results = sorted([random.randint(1, 6) for _ in range(black_dice)])

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

    emit('dice_rolled', current_roll, broadcast=True)


@socketio.on("update_coins")
def handle_update_coins(data):
    token = request.cookies.get("auth_token")
    if not token or token not in online_users or not online_users[token].get("is_master", False):
        return

    master_data["coins"]["hope"] = max(0, data.get("hope", master_data["coins"]["hope"]))
    master_data["coins"]["despair"] = max(0, data.get("despair", master_data["coins"]["despair"]))

    emit("update_coins", master_data["coins"], broadcast=True)


@socketio.on("request_coins")
def handle_request_coins():
    emit("update_coins", master_data["coins"])


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5100, use_reloader=False, log_output=True)
