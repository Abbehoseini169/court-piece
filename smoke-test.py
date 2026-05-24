#!/usr/bin/env python3
"""
Smoke test — ansluter en klient, skapar ett rum, fyller tomma platser med AI
och spelar tills spelet är slut. Kör medan servern är igång:

    python smoke-test.py
"""
import sys
import threading
import socketio as sio_module

from game import ai_pick_trump, ai_choose_card, card_id

PORT = 3001
done = threading.Event()
sio = sio_module.Client(logger=False, engineio_logger=False)


@sio.event
def connect():
    print("[smoke] Ansluten till servern")


@sio.event
def disconnect():
    print("[smoke] Frånkopplad")


@sio.on("state")
def on_state(data):
    phase = data["phase"]
    turn = data["turn"]
    seat = data["yourSeat"]

    if phase == "gameover":
        s = data["score"]
        result = data["lastResult"]
        print(f"\n[smoke] === SPELET SLUT ===")
        print(f"[smoke] Lag 0: {s[0]}p  |  Lag 1: {s[1]}p")
        print(f"[smoke] Vinnande lag: {result['winTeam']}")
        done.set()
        return

    if phase == "handover":
        result = data["lastResult"]
        s = data["score"]
        typ = "Baunie" if result["baunie"] else "Kot" if result["kot"] else "Normal"
        print(f"[smoke] Hand klar — {typ}, +{result['points']}p till lag {result['winTeam']}  (totalpoäng: {s[0]}-{s[1]})")
        return

    if phase == "calling" and turn == seat:
        trump = ai_pick_trump(data["yourHand"][:5])
        print(f"[smoke] Kallar trumf: {trump}")
        sio.emit("callTrump", {"suit": trump})
        return

    if phase == "play" and turn == seat:
        card = ai_choose_card(
            data["yourHand"], data["table"], data["leadSuit"], data["trump"], seat
        )
        if card:
            print(f"[smoke] Stick {data['trickCount'] + 1}: plats {seat} spelar {card_id(card)}")
            sio.emit("playCard", {"card": card})


def main():
    try:
        sio.connect(f"http://localhost:{PORT}")
    except Exception as e:
        print(f"[smoke] FEL — kunde inte ansluta: {e}")
        print("[smoke] Är servern igång? Starta med: python server.py")
        sys.exit(1)

    res = sio.call("createRoom", {"name": "Smoke-test"})
    if not res or not res.get("ok"):
        print(f"[smoke] FEL — kunde inte skapa rum: {res}")
        sys.exit(1)

    print(f"[smoke] Rum: {res['code']}  (plats 0)")

    # Starta omedelbart — tomma platser fylls automatiskt med AI
    sio.emit("startGame", {})

    if not done.wait(timeout=120):
        print("[smoke] TIMEOUT — spelet tog mer än 120 sekunder")
        sio.disconnect()
        sys.exit(1)

    sio.disconnect()
    print("[smoke] Smoke test GODKÄNT")


if __name__ == "__main__":
    main()
