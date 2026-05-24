import os
import random
import string
import threading
import time

from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, join_room

from game import (
    deal_hand, legal_cards, trick_winner, score_hand,
    ai_pick_trump, ai_choose_card, team_of, card_id,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "courtpiece-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = {}       # code -> room dict
sock = {}        # sid -> {"room": code, "seat": int}

AUTOSTART_S = 30
RECONNECT_GRACE_S = 30
TARGET_SCORE = 7


# ---- Hjälpfunktioner -------------------------------------------------------

def make_room_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(random.choices(chars, k=4))
        if code not in rooms:
            return code


def make_player_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


def new_room(code, host_id):
    return {
        "code": code,
        "seats": [None, None, None, None],
        "hostId": host_id,
        "started": False,
        "autostartTimer": None,
        "autostartAt": None,
        "hands": None, "trump": None, "turn": -1,
        "table": [], "leadSuit": None,
        "dealer": 0, "caller": 1,
        "tricksWon": [0, 0], "trickCount": 0,
        "score": [0, 0], "phase": "lobby",
        "lastResult": None,
    }


def _timer(delay, fn, *args):
    t = threading.Timer(delay, fn, args=args)
    t.daemon = True
    t.start()
    return t


def arm_autostart(room):
    if room["started"]:
        return
    if room["autostartTimer"]:
        room["autostartTimer"].cancel()
    room["autostartAt"] = time.time() * 1000 + AUTOSTART_S * 1000
    room["autostartTimer"] = _timer(AUTOSTART_S, begin_game, room)


def begin_game(room):
    if room["started"]:
        return
    if room["autostartTimer"]:
        room["autostartTimer"].cancel()
        room["autostartTimer"] = None
    for i in range(4):
        if not room["seats"][i]:
            room["seats"][i] = {"id": f"ai-{i}", "name": f"Dator {i+1}", "isAI": True}
    room["started"] = True
    room["autostartAt"] = None
    start_hand(room)


# ---- Vad varje spelare får se -----------------------------------------------

def view_for(room, seat):
    legal = []
    if seat == room["turn"] and room["hands"] and room["phase"] == "play":
        legal = list(map(card_id, legal_cards(room["hands"][seat], room["table"], room["leadSuit"])))
    return {
        "code": room["code"],
        "phase": room["phase"],
        "started": room["started"],
        "autostartAt": room["autostartAt"],
        "seats": [
            {"name": s["name"], "isAI": s.get("isAI", False), "disconnected": s.get("disconnected", False)}
            if s else None
            for s in room["seats"]
        ],
        "yourSeat": seat,
        "yourHand": room["hands"][seat] if seat >= 0 and room["hands"] else [],
        "handCounts": [len(h) for h in room["hands"]] if room["hands"] else [0, 0, 0, 0],
        "trump": room["trump"],
        "turn": room["turn"],
        "table": room["table"],
        "leadSuit": room["leadSuit"],
        "caller": room["caller"],
        "dealer": room["dealer"],
        "tricksWon": room["tricksWon"],
        "trickCount": room["trickCount"],
        "score": room["score"],
        "lastResult": room["lastResult"],
        "legal": legal,
    }


def broadcast(room):
    for seat, s in enumerate(room["seats"]):
        if s and not s.get("isAI") and not s.get("disconnected"):
            socketio.emit("state", view_for(room, seat), to=s["id"])


# ---- Spelflöde --------------------------------------------------------------

def maybe_ai_calling(room):
    if room["phase"] != "calling":
        return
    caller = room["seats"][room["caller"]]
    if not caller or not caller.get("isAI"):
        return

    def do_call():
        if room["phase"] != "calling":
            return
        room["trump"] = ai_pick_trump(room["hands"][room["caller"]][:5])
        room["phase"] = "play"
        room["turn"] = room["caller"]
        broadcast(room)
        maybe_ai_turn(room)

    _timer(0.8, do_call)


def start_hand(room):
    result = deal_hand(room["dealer"])
    room["hands"] = result["hands"]
    room["caller"] = result["caller_seat"]
    room["trump"] = None
    room["table"] = []
    room["leadSuit"] = None
    room["tricksWon"] = [0, 0]
    room["trickCount"] = 0
    room["turn"] = result["caller_seat"]
    room["phase"] = "calling"
    broadcast(room)
    maybe_ai_calling(room)


def apply_play(room, seat, card):
    if room["phase"] != "play" or room["turn"] != seat:
        return False
    legal = legal_cards(room["hands"][seat], room["table"], room["leadSuit"])
    if not any(card_id(c) == card_id(card) for c in legal):
        return False

    room["hands"][seat] = [c for c in room["hands"][seat] if card_id(c) != card_id(card)]
    if not room["table"]:
        room["leadSuit"] = card["s"]
    room["table"].append({"seat": seat, "card": card})

    if len(room["table"]) == 4:
        winner_seat = trick_winner(room["table"], room["leadSuit"], room["trump"])
        room["turn"] = -1
        broadcast(room)
        _timer(1.1, resolve_trick, room, winner_seat)
    else:
        room["turn"] = (seat + 1) % 4
        broadcast(room)
        maybe_ai_turn(room)
    return True


def resolve_trick(room, winner_seat):
    room["tricksWon"][team_of(winner_seat)] += 1
    room["trickCount"] += 1
    room["table"] = []
    room["leadSuit"] = None

    us, them = room["tricksWon"]
    if us >= 7 or them >= 7 or room["trickCount"] == 13:
        result = score_hand(room["tricksWon"])
        room["score"][result["winTeam"]] += result["points"]
        room["lastResult"] = result

        if room["score"][0] >= TARGET_SCORE or room["score"][1] >= TARGET_SCORE:
            room["phase"] = "gameover"
            room["turn"] = -1
            broadcast(room)
            return

        room["phase"] = "handover"
        room["turn"] = -1
        broadcast(room)
        _timer(5.0, lambda: next_hand(room) if room["phase"] == "handover" else None)
        return

    room["turn"] = winner_seat
    broadcast(room)
    maybe_ai_turn(room)


def maybe_ai_turn(room):
    if room["phase"] != "play" or room["turn"] < 0:
        return
    s = room["seats"][room["turn"]]
    if not s or not s.get("isAI"):
        return
    seat = room["turn"]
    delay = 0.12 + random.random() * 0.08

    def do_play():
        if room["turn"] != seat:
            return
        card = ai_choose_card(room["hands"][seat], room["table"], room["leadSuit"], room["trump"], seat)
        if card:
            apply_play(room, seat, card)

    _timer(delay, do_play)


def next_hand(room):
    if room["phase"] != "handover":
        return
    caller_won = room["lastResult"]["winTeam"] == team_of(room["caller"])
    room["dealer"] = room["dealer"] if caller_won else (room["dealer"] + 1) % 4
    start_hand(room)


# ---- HTTP -------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ---- Socket.IO-händelser ----------------------------------------------------

@socketio.on("createRoom")
def handle_create_room(data):
    name = (data or {}).get("name") or "Spelare 1"
    code = make_room_code()
    room = new_room(code, request.sid)
    player_id = make_player_id()
    room["seats"][0] = {"id": request.sid, "playerId": player_id, "name": name, "isAI": False, "disconnected": False}
    rooms[code] = room
    join_room(code)
    sock[request.sid] = {"room": code, "seat": 0}
    arm_autostart(room)
    broadcast(room)
    return {"ok": True, "code": code, "playerId": player_id}


@socketio.on("joinRoom")
def handle_join_room(data):
    code = ((data or {}).get("code") or "").upper()
    name = (data or {}).get("name") or "Spelare"
    room = rooms.get(code)
    if not room:
        return {"ok": False, "error": "Rummet finns inte"}
    if room["started"]:
        return {"ok": False, "error": "Spelet har redan börjat"}
    seat = next((i for i, s in enumerate(room["seats"]) if s is None), -1)
    if seat < 0:
        return {"ok": False, "error": "Rummet är fullt"}
    player_id = make_player_id()
    room["seats"][seat] = {"id": request.sid, "playerId": player_id, "name": name, "isAI": False, "disconnected": False}
    join_room(code)
    sock[request.sid] = {"room": code, "seat": seat}
    broadcast(room)
    if all(s and not s.get("isAI") for s in room["seats"]):
        begin_game(room)
    return {"ok": True, "code": code, "seat": seat, "playerId": player_id}


@socketio.on("rejoin")
def handle_rejoin(data):
    code = ((data or {}).get("code") or "").upper()
    player_id = (data or {}).get("playerId", "")
    room = rooms.get(code)
    if not room:
        return {"ok": False, "error": "Rummet finns inte"}
    seat = next(
        (i for i, s in enumerate(room["seats"])
         if s and s.get("playerId") == player_id and s.get("disconnected")), -1
    )
    if seat < 0:
        return {"ok": False, "error": "Ingen återanslutningsplats hittad"}
    t = room["seats"][seat].get("reconnectTimer")
    if t:
        t.cancel()
    room["seats"][seat]["reconnectTimer"] = None
    room["seats"][seat]["id"] = request.sid
    room["seats"][seat]["disconnected"] = False
    if not room["hostId"]:
        room["hostId"] = request.sid
    join_room(code)
    sock[request.sid] = {"room": code, "seat": seat}
    broadcast(room)
    return {"ok": True, "seat": seat, "playerId": player_id}


@socketio.on("startGame")
def handle_start_game(data):
    sd = sock.get(request.sid, {})
    room = rooms.get(sd.get("room"))
    if not room or room["hostId"] != request.sid:
        return
    begin_game(room)
    return {"ok": True}


@socketio.on("playCard")
def handle_play_card(data):
    sd = sock.get(request.sid, {})
    room = rooms.get(sd.get("room"))
    if room:
        apply_play(room, sd.get("seat"), (data or {}).get("card"))


@socketio.on("callTrump")
def handle_call_trump(data):
    sd = sock.get(request.sid, {})
    room = rooms.get(sd.get("room"))
    if not room or room["phase"] != "calling" or sd.get("seat") != room["caller"]:
        return
    room["trump"] = (data or {}).get("suit")
    room["phase"] = "play"
    room["turn"] = room["caller"]
    broadcast(room)
    maybe_ai_turn(room)


@socketio.on("nextHand")
def handle_next_hand(data):
    sd = sock.get(request.sid, {})
    room = rooms.get(sd.get("room"))
    if room:
        next_hand(room)


@socketio.on("disconnect")
def handle_disconnect():
    sd = sock.pop(request.sid, {})
    room = rooms.get(sd.get("room"))
    if not room:
        return
    seat = sd.get("seat", -1)
    if seat < 0 or not room["seats"][seat] or room["seats"][seat].get("isAI"):
        return

    if room["hostId"] == request.sid:
        nxt = next(
            (s for i, s in enumerate(room["seats"])
             if i != seat and s and not s.get("isAI") and not s.get("disconnected")), None
        )
        room["hostId"] = nxt["id"] if nxt else None

    room["seats"][seat]["disconnected"] = True
    room["seats"][seat]["id"] = None

    def replace_with_ai():
        s = room["seats"][seat]
        if not s or not s.get("disconnected"):
            return
        room["seats"][seat] = {"id": f"ai-{seat}", "name": f"Dator {seat+1}", "isAI": True}
        broadcast(room)
        maybe_ai_calling(room)
        maybe_ai_turn(room)

    t = _timer(RECONNECT_GRACE_S, replace_with_ai)
    room["seats"][seat]["reconnectTimer"] = t
    broadcast(room)


# ---- Starta -----------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    print(f"Court Piece-servern (Python) lyssnar på port {port}")
    socketio.run(app, port=port, debug=False, allow_unsafe_werkzeug=True)
