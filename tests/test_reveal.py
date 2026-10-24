"""P4-12 reveal-screen rules."""
from datetime import date
from pathlib import Path

import pytest

from lottery_checker import fourd, toto
from lottery_checker.ingest import official_url
from lottery_checker.parse import parse_fourd, parse_toto
from lottery_checker.reveal import build_reveal, money
from lottery_checker.ticket import DrawRef, check_ticket

FIX = Path(__file__).parent / "fixtures"
DAY = date(2026, 6, 24)
TODAY = date(2026, 6, 25)


def toto_ref(draw_no=4200, day=DAY, **kw):
    return DrawRef(toto.TotoDraw(draw_no, (1, 2, 3, 4, 5, 6), 7, **kw), day)


def fourd_ref(draw_no=5500, day=DAY):
    tens = tuple(f"{i:04d}" for i in range(10))
    return DrawRef(fourd.FourDDraw(draw_no, "1234", "5678", "9012", tens, tens[::-1]), day)


def all_text(rv):
    parts = [rv.headline, rv.subline, rv.claim_text or "", rv.stake.message]
    for ln in rv.lines:
        parts += [ln.result_text, *ln.detail]
    return " | ".join(parts)


# ---------------- money ----------------

@pytest.mark.parametrize("v,s", [(4000, "S$4,000"), (4000.0, "S$4,000"), (1566.5, "S$1,566.50"),
                                 (93233.0, "S$93,233"), (0.5, "S$0.50"), (1234567.0, "S$1,234,567")])
def test_money(v, s):
    assert money(v) == s


# ---------------- rule 1: pending is never S$0 ----------------

def test_pending_only_names_the_group_and_never_shows_zero():
    r = check_ticket([toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7))], [toto_ref()])   # G2 unpriced
    rv = build_reveal(r, today=TODAY)
    assert rv.state == "pending"
    assert rv.headline == "You won a Group 2 prize"
    assert "not yet published" in rv.subline
    assert rv.lines[0].result_text == "Group 2: amount not yet published"
    text = all_text(rv)
    assert "S$0" not in text and "0.00" not in text and "No win" not in text


def test_pending_with_priced_lines_says_at_least():
    entries = [toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7)),      # G2, unpriced
               toto.TotoEntry("ordinary", (1, 2, 3, 40, 41, 42))]   # G7, S$10
    rv = build_reveal(check_ticket(entries, [toto_ref()]), today=TODAY)
    assert rv.state == "pending"
    assert rv.headline == "At least S$10 so far"
    assert "Group 2" in rv.subline
    assert [ln.result_text for ln in rv.lines] == ["Group 2: amount not yet published", "S$10"]


def test_several_pending_groups_are_all_named():
    # System 7 hitting 5 + Additional: G2 and G3 both unpriced on a bare draw.
    r = check_ticket([toto.TotoEntry("system", (1, 2, 3, 4, 5, 7, 40))], [toto_ref()])
    rv = build_reveal(r, today=TODAY)
    assert rv.state == "pending" and r.pending_groups == (2, 3, 4)
    assert rv.headline == "You won Group 2, Group 3 and Group 4 prizes"
    assert rv.subline.startswith("The amounts are not yet published")
    assert rv.lines[0].result_text == "Group 2, Group 3 and Group 4: amounts not yet published"


# ---------------- states ----------------

def test_won_headline_and_claim():
    rv = build_reveal(check_ticket([fourd.FourDEntry("ordinary", "1234", big=2)], [fourd_ref()]),
                      today=TODAY)
    assert rv.state == "won" and rv.headline == "You won S$4,000"
    assert rv.subline == "Staked S$2 across 1 draw"
    assert rv.claim_text.startswith("Claim by 21 Dec 2026")


def test_no_win_has_no_claim_text():
    rv = build_reveal(check_ticket([fourd.FourDEntry("ordinary", "7777", big=1)], [fourd_ref()]),
                      today=TODAY)
    assert rv.state == "no_win" and rv.headline == "No win this time"
    assert rv.claim_text is None and rv.lines[0].result_text == "No win"


# ---------------- rule 2: claim period ----------------

def test_claim_uses_earliest_draw_and_never_says_void():
    refs = [fourd_ref(5501, date(2026, 7, 1)), fourd_ref(5500, DAY)]
    r = check_ticket([fourd.FourDEntry("ordinary", "1234", big=1)], refs)
    rv = build_reveal(r, today=date(2027, 3, 1))
    assert "21 Dec 2026" in rv.claim_text
    for bad in ("void", "expired", "worthless", "too late"):
        assert bad not in rv.claim_text.lower()


def test_pending_still_gets_claim_text():
    r = check_ticket([toto.TotoEntry("ordinary", (1, 2, 3, 4, 5, 7))], [toto_ref()])
    assert build_reveal(r, today=TODAY).claim_text is not None


# ---------------- rule 3: printed PRICE check ----------------

def test_stake_matches_printed_price():
    r = check_ticket([fourd.FourDEntry("ibet", "1234", big=10, small=10)], [fourd_ref()])
    rv = build_reveal(r, printed_price=20.00, today=TODAY)     # specimen iBet: PRICE $20.00
    assert rv.stake.state == "match" and not rv.needs_review


def test_stake_mismatch_flags_review_but_still_reveals():
    # Specimen sold-out ticket printed $182; a parser that ignored S'OUT would count more.
    r = check_ticket([fourd.FourDEntry("ordinary", "1234", big=100, small=100)], [fourd_ref()])
    rv = build_reveal(r, printed_price=182.00, today=TODAY)
    assert rv.stake.state == "mismatch" and rv.needs_review
    assert "S$182" in rv.stake.message and "S$200" in rv.stake.message
    assert "S'OUT" in rv.stake.message
    assert rv.state == "won"                                   # result still shown


def test_missing_price_line_is_not_checked_not_failed():
    r = check_ticket([fourd.FourDEntry("ordinary", "7777", big=1)], [fourd_ref()])
    rv = build_reveal(r, printed_price=None, today=TODAY)
    assert rv.stake.state == "not_checked" and not rv.needs_review


def test_multi_draw_price_is_whole_ticket():
    # Real Toto tickets (21 Oct): 2 boards x 2 draws prints PRICE $4.00.
    entries = [toto.TotoEntry("ordinary", (11, 12, 13, 14, 15, 16)),
               toto.TotoEntry("ordinary", (21, 22, 23, 24, 25, 26))]
    refs = [toto_ref(4220, date(2026, 9, 24)), toto_ref(4221, date(2026, 9, 28))]
    rv = build_reveal(check_ticket(entries, refs), printed_price=4.00, today=TODAY)
    assert rv.stake.state == "match"


# ---------------- rule 4: links and attribution ----------------

def test_one_official_link_per_draw_and_attribution():
    refs = [fourd_ref(5500), fourd_ref(5501, date(2026, 6, 27))]
    entries = [fourd.FourDEntry("ordinary", "1234", big=1), fourd.FourDEntry("ordinary", "7777", big=1)]
    rv = build_reveal(check_ticket(entries, refs), today=TODAY)
    assert rv.official_links == [(5500, official_url("4d", 5500)), (5501, official_url("4d", 5501))]
    assert "do not own" in rv.attribution


# ---------------- real fixtures ----------------

def test_real_toto_system7_reveal():
    ref = DrawRef.from_parsed(parse_toto((FIX / "toto_4068.html").read_text(encoding="utf-8"))[0])
    r = check_ticket([toto.TotoEntry("system", (14, 26, 27, 30, 46, 10, 1))], [ref])
    rv = build_reveal(r, printed_price=7.00, today=date(2025, 4, 11))
    assert rv.headline == "You won S$93,233" and rv.stake.state == "match"
    assert rv.claim_text.startswith("Claim by 7 Oct 2025")


def test_real_4d_reveal():
    ref = DrawRef.from_parsed(parse_fourd((FIX / "fourd_5500.html").read_text(encoding="utf-8"))[0])
    entries = [fourd.FourDEntry("ordinary", "5950", big=2),
               fourd.FourDEntry("ibet", "0398", big=1),
               fourd.FourDEntry("roll", "59R0", big=1)]
    rv = build_reveal(check_ticket(entries, [ref]), printed_price=13.00, today=TODAY)
    assert rv.headline == "You won S$6,010" and not rv.needs_review
    assert rv.official_links == [(5500, official_url("4d", 5500))]
