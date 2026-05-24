import random

SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}
COURT = {"J", "Q", "K", "A"}


def team_of(seat):
    return seat % 2


def card_id(c):
    return f"{c['r']}{c['s']}"


def _make_deck():
    return [{"s": s, "r": r} for s in SUITS for r in RANKS]


def deal_hand(dealer_seat):
    caller_seat = (dealer_seat + 1) % 4
    safety = 0
    while True:
        deck = _make_deck()
        random.shuffle(deck)
        hands = [[], [], [], []]
        idx = 0
        for batch in [5, 3, 3, 2]:
            for p in range(4):
                seat = (caller_seat + p) % 4
                for _ in range(batch):
                    hands[seat].append(deck[idx])
                    idx += 1
        safety += 1
        if safety >= 50 or any(c["r"] in COURT for c in hands[caller_seat][:5]):
            break
    return {"hands": hands, "dealer_seat": dealer_seat, "caller_seat": caller_seat}


def legal_cards(hand, table, lead_suit):
    if not table:
        return hand[:]
    same_suit = [c for c in hand if c["s"] == lead_suit]
    return same_suit if same_suit else hand[:]


def trick_winner(table, lead_suit, trump):
    best = table[0]
    for play in table:
        c, b = play["card"], best["card"]
        c_trump = c["s"] == trump
        b_trump = b["s"] == trump
        if c_trump and not b_trump:
            best = play
        elif c_trump and b_trump:
            if RANK_VALUE[c["r"]] > RANK_VALUE[b["r"]]:
                best = play
        elif not c_trump and not b_trump:
            if c["s"] == lead_suit and b["s"] == lead_suit and RANK_VALUE[c["r"]] > RANK_VALUE[b["r"]]:
                best = play
            elif c["s"] == lead_suit and b["s"] != lead_suit:
                best = play
    return best["seat"]


def ai_pick_trump(first5):
    cnt = {"S": 0, "H": 0, "D": 0, "C": 0}
    for c in first5:
        cnt[c["s"]] += 1 + (1.2 if RANK_VALUE[c["r"]] >= 11 else 0)
    return max(cnt, key=cnt.get)


def ai_choose_card(hand, table, lead_suit, trump, seat):
    legal = legal_cards(hand, table, lead_suit)
    if len(legal) <= 1:
        return legal[0] if legal else None

    def lowest(cards):
        return min(cards, key=lambda c: RANK_VALUE[c["r"]])

    my_team = team_of(seat)

    if not table:
        non_trump = [c for c in legal if c["s"] != trump]
        pool = non_trump if non_trump else legal
        ace = next((c for c in pool if c["r"] == "A"), None)
        return ace or lowest(pool)

    winner_seat = trick_winner(table, lead_suit, trump)
    winning_card = next(p["card"] for p in table if p["seat"] == winner_seat)
    partner_winning = team_of(winner_seat) == my_team

    def beats(c):
        c_trump = c["s"] == trump
        w_trump = winning_card["s"] == trump
        if c_trump and not w_trump:
            return True
        if c_trump and w_trump:
            return RANK_VALUE[c["r"]] > RANK_VALUE[winning_card["r"]]
        if not c_trump and not w_trump:
            return c["s"] == lead_suit and RANK_VALUE[c["r"]] > RANK_VALUE[winning_card["r"]]
        return False

    if partner_winning:
        non_trump = [c for c in legal if c["s"] != trump]
        return lowest(non_trump if non_trump else legal)

    winners = [c for c in legal if beats(c)]
    if winners:
        nt_win = [c for c in winners if c["s"] != trump]
        return lowest(nt_win if nt_win else winners)

    non_trump = [c for c in legal if c["s"] != trump]
    return lowest(non_trump if non_trump else legal)


def score_hand(tricks_won):
    us, them = tricks_won
    win_team = 0 if us >= 7 else 1
    winner_tricks = us if win_team == 0 else them
    loser_tricks = them if win_team == 0 else us
    baunie = winner_tricks == 13
    kot = loser_tricks == 0 and winner_tricks >= 7
    points = 15 if baunie else 5 if kot else 2
    return {"winTeam": win_team, "kot": kot, "baunie": baunie, "points": points}
