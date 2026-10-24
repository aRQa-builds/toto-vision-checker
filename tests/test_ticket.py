"""P3-05 aggregator and P3-06 claim period."""
from datetime import date
from pathlib import Path

import pytest

from lottery_checker import fourd, toto
from lottery_checker.claim import CLAIM_DAYS, claim_by, claim_hint, days_left
from lottery_checker.parse import parse_fourd, parse_toto
from lottery_checker.ticket import DrawRef, TicketError, check_ticket

FIX = Path(__file__).parent / "fixtures"
DRAW_DAY = date(2026, 6, 24)


def toto_ref(draw_no=4200, **kw):
    d = toto.TotoDraw(draw_no, (1, 2, 3, 4, 5, 6), 7, **kw)
    return DrawRef(d, DRAW_DAY)


def fourd_ref(draw_no=5500):
    tens = tuple(f"{i:04d}" for i in range(10))
    d = fourd.FourDDraw(draw_no, "1234", "5678", "9012", tens, tens[::-1])
    return DrawRef(d, DRAW_DAY)


# ---------------- claim period (P3-06) ----------------

def test_claim_by_is_180_days():
    assert CLAIM_DAYS == 180
    assert claim_by(date(2026, 6, 24)) == date(2026, 12, 21)


def test_claim_by_crosses_a_leap_day():
    assert claim_by(date(2027, 11, 1)) == date(2028, 4, 29)   # Feb 2028 has 29 days


@pytest.mark.parametrize("today,left", [
    (date(2026, 6, 24), 180), (date(2026, 12, 20), 1),
    (date(2026, 12, 21), 0), (date(2026, 12, 22), -1),
])
def test_days_left(today, left):
    assert days_left(date(2026, 6, 24), today) == left


def test_hint_never_says_void_after_the_period():
    msg = claim_hint(date(2026, 6, 24), date(2027, 1, 1))
    assert "21 Dec 2026" in msg and "extended it before" in msg
    for bad in ("void", "expired", "worthless", "too late"):
        assert bad not in msg.lower()


def test_hint_counts_down():
    assert "180 days left" in claim_hint(date(2026, 6, 24), date(2026, 6, 24))
    assert "1 day left" in claim_hint(date(2026, 6, 24), date(2026, 12, 20))
    assert "last day" in claim_hint(date(2026, 6, 24), date(2026, 12, 21))


# ---------------- aggregation ----------------

def test_fourd_ticket_rolls_up_stake_and_winnings():
    entries = [fourd.FourDEntry("ordinary", "1234", big=2),   # first, $4000
               fourd.FourDEntry("ordinary", "9999", big=1)]   # nothing
    r = check_ticket(entries, [fourd_ref()])
    assert r.total_stake == 3 and r.total_won == 4000 and r.net == 3997
    assert not r.pending and r.won_anything
    assert [ln.label for ln in r.lines] == ["Ordinary", "Ordinary"]
    assert r.lines[0].detail == ["1234 first (big): 4,000"]
    assert r.lines[1].detail == []


def test_toto_pending_group_does_not_become_zero():
    # Group 2 won but the draw carries no published amount for it.
    r = check_ticket([toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7))], [toto_ref()])
    assert r.pending and r.total_won is None and r.net is None
    assert r.pending_groups == (2,)
    assert r.won_anything                       # pending still counts as a win
    assert "not yet published" in r.lines[0].detail[0]


def test_one_pending_line_makes_the_whole_ticket_pending():
    entries = [toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7)),    # G2, unpriced
               toto.TotoEntry("ordinary", (1, 2, 3, 40, 41, 42))]  # G7, $10
    r = check_ticket(entries, [toto_ref()])
    assert r.total_won is None and r.pending_groups == (2,)
    assert sum(1 for ln in r.lines if ln.pending) == 1


def test_priced_toto_ticket_totals():
    ref = toto_ref(group_prizes={2: 90000.0})
    r = check_ticket([toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7))], [ref])
    assert r.total_won == 90000.0 and not r.pending and r.pending_groups == ()


def test_multi_draw_claim_uses_the_earliest_draw():
    early, late = date(2026, 6, 24), date(2026, 7, 1)
    refs = [DrawRef(fourd_ref(5500).draw, late), DrawRef(fourd_ref(5501).draw, early)]
    r = check_ticket([fourd.FourDEntry("ordinary", "1234", big=1)], refs)
    assert len(r.lines) == 2 and r.total_stake == 2
    assert r.earliest_draw_date == early and r.claim_by() == claim_by(early)


def test_no_win_ticket():
    r = check_ticket([fourd.FourDEntry("ordinary", "7777", big=1)], [fourd_ref()])
    assert r.total_won == 0 and not r.won_anything and r.net == -1


# ---------------- guards ----------------

def test_game_mismatch_raises_rather_than_scoring_zero():
    with pytest.raises(TicketError):
        check_ticket([fourd.FourDEntry("ordinary", "1234", big=1)], [toto_ref()])


def test_mixed_games_on_one_ticket_raise():
    with pytest.raises(TicketError):
        check_ticket([fourd.FourDEntry("ordinary", "1234", big=1),
                      toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 6))], [fourd_ref()])


@pytest.mark.parametrize("entries,refs", [([], [fourd_ref()]),
                                          ([fourd.FourDEntry("ordinary", "1234", big=1)], [])])
def test_empty_inputs_raise(entries, refs):
    with pytest.raises(TicketError):
        check_ticket(entries, refs)


# ---------------- against the real fixtures ----------------

def test_real_4d_draw_end_to_end():
    ref = DrawRef.from_parsed(parse_fourd((FIX / "fourd_5500.html").read_text(encoding="utf-8"))[0])
    entries = [fourd.FourDEntry("ordinary", "5950", big=2),
               fourd.FourDEntry("ibet", "0398", big=1),
               fourd.FourDEntry("roll", "59R0", big=1)]
    r = check_ticket(entries, [ref])
    assert r.total_stake == 13 and r.total_won == 6010
    assert r.earliest_draw_date == date(2026, 6, 24)
    assert r.claim_by() == date(2026, 12, 21)
    assert [ln.label for ln in r.lines] == ["Ordinary", "iBet", "4D Roll"]


def test_real_toto_draw_end_to_end():
    ref = DrawRef.from_parsed(parse_toto((FIX / "toto_4068.html").read_text(encoding="utf-8"))[0])
    r = check_ticket([toto.TotoEntry("system", (14, 26, 27, 30, 46, 10, 1))], [ref])
    assert r.total_stake == 7 and r.total_won == 93233.0
    assert r.earliest_draw_date == date(2025, 4, 10)
    assert "ended on" in r.claim_hint(date(2026, 10, 18))   # long past, still not "void"
