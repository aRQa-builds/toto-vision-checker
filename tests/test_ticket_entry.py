"""P4-01 manual ticket entry.

Layouts follow the rules reference v0.3: the real TOTO tickets photographed
21 Oct 2026 (notice lines, QP boards, one DRAW line per draw as NNNN/YY,
PRICE across all draws) and the official 4D specimens (IBET header,
PERMUTATIONS line, R in a Roll number, S'OUT, *). Board numbers here are made
up; the real tickets' boards are not stored.
"""
from datetime import date

import pytest

from lottery_checker import fourd, toto
from lottery_checker.manual import fourd_result, toto_result
from lottery_checker.reveal import build_reveal
from lottery_checker.ticket_entry import parse_ticket

REAL_TOTO_LAYOUT = """TOTO
No more cheques from 1 Nov 2026
Link NRIC to PayNow for payouts
ORDINARY
A. 03 11 19 25 33 47 QP
B. 05 09 21 30 41 44 QP
DRAW:
THU 24/09/26  4220/26
MON 28/09/26  4221/26
PRICE: $4.00
23/09/26 01:51 PM
209-38781441-093108
"""

IBET_SPECIMEN = """4D
IBET
A 1234 BIG $10 SML $10
  24 PERMUTATIONS
DRAW: SAT 26/04/14 0003/14
PRICE:$20.00
23/04/14 02:18pm
209-38781441-093108
00888802-01  02-1349
"""

FOURD_5551 = """4D
ORDINARY
A 8455 BIG $1
B R888 BIG $1
C 9363 BIG S'OUT SML $2*
DRAW: WED 21/10/26 5551/26
PRICE: $13.00
"""

M4227 = toto_result(4227, date(2026, 10, 19), "2 15 19 20 27 30 + 5",
                    group_amounts={1: "2,928,913", 2: "68,513", 3: "1,359", 4: "200"})
M5551 = fourd_result(5551, date(2026, 10, 21), """8455 1103 3344
0273 0436 2089 2837 5006 6491 7394 8072 8468 9574
0030 0854 2005 4062 4623 4890 6736 6804 8934 9363""")
ON_FILE = {4227: M4227.ref, 5551: M5551.ref}


# ---------------- TOTO ----------------

def test_real_toto_layout():
    d = parse_ticket(REAL_TOTO_LAYOUT)
    assert d.game == "toto" and d.ready and d.quick_pick
    assert [e.numbers for e in d.entries] == [(3, 11, 19, 25, 33, 47), (5, 9, 21, 30, 41, 44)]
    assert d.draws == [(4220, date(2026, 9, 24)), (4221, date(2026, 9, 28))]
    assert d.printed_price == 4.0 and d.stake() == 4 and d.warnings == []
    assert d.entry_lines == [5, 6]                # so the confirm screen can point at the line


def test_toto_kind_follows_count_without_a_header():
    d = parse_ticket("TOTO\n1 2 3 4 5 6\n1 2 3 4 5 6 7\n1 2 3 4 5\ndraw 4227")
    assert [e.label for e in d.entries] == ["Ordinary", "System 7", "System Roll"]
    assert d.stake() == 1 + 7 + 44


def test_typed_inline_system_label():
    d = parse_ticket("System 8: 2 15 19 20 27 30 5 41\ndraw 4227")
    assert d.game == "toto" and d.entries[0].label == "System 8" and d.ready


def test_system12_board_wrapping_over_two_lines():
    d = parse_ticket("TOTO\nSYSTEM 12\nA. 02 05 15 19 20 27\n   30 33 38 41 44 49\nDRAW:\nMON 19/10/26 4227/26")
    assert d.ready and d.entries[0].label == "System 12" and len(d.entries[0].numbers) == 12


def test_header_count_mismatch_points_at_the_line():
    d = parse_ticket("TOTO\nSYSTEM 7\nA. 01 02 03 04 05 06\ndraw 4227")
    assert not d.ready
    assert d.errors[0].line_no == 3 and "expected 7 numbers" in d.errors[0].message


@pytest.mark.parametrize("board,msg", [("A. 01 02 03 04 05 50", "1 to 49"),
                                       ("A. 01 02 03 04 05 05", "appears twice"),
                                       ("A. 01 02 03 04", "5, 6 or 7-12"),
                                       ("A. 01 02 O3 04 05 06", "don't understand O3")])
def test_toto_board_errors(board, msg):
    d = parse_ticket(f"TOTO\n{board}\ndraw 4227")
    assert len(d.errors) == 1 and msg in d.errors[0].message and d.errors[0].line_no == 2


def test_itoto_is_recognised_but_not_priced():
    d = parse_ticket("TOTO\nITOTO - SYSTEM 12\nA. 02 05 15 19 20 27\n30 33 38 41 44 49\n"
                     "DRAW:\nFRI 27/02/26 4160/26\nPRICE: $33.00\nNUMBER OF UNITS PURCHASED: 1 of 28")
    assert d.units == (1, 28) and not d.supported and not d.ready
    assert any("not supported yet" in p for p in d.problems())


def test_price_mismatch_warns():
    d = parse_ticket(REAL_TOTO_LAYOUT.replace("PRICE: $4.00", "PRICE: $2.00"))
    assert any("PRICE says S$2.00 but these bets come to S$4.00" in w for w in d.warnings)


def test_toto_check_against_draw_on_file():
    d = parse_ticket("TOTO\nORDINARY\nA. 02 15 19 20 27 05\nDRAW:\nMON 19/10/26 4227/26\nPRICE: $1.00")
    rv = build_reveal(d.check(ON_FILE.get), printed_price=d.printed_price, today=date(2026, 10, 20))
    assert rv.headline == "You won S$68,513" and rv.stake.state == "match"


def test_missing_draw_result_is_named():
    d = parse_ticket(REAL_TOTO_LAYOUT)
    with pytest.raises(LookupError, match=r"\[4220, 4221\]"):
        d.check(ON_FILE.get)


# ---------------- 4D ----------------

def test_ibet_specimen_skips_codes_and_timestamps():
    d = parse_ticket(IBET_SPECIMEN)
    assert d.game == "4d" and d.errors == [] and d.warnings == []
    assert d.entries == [fourd.FourDEntry("ibet", "1234", 10, 10)]
    assert d.printed_price == 20.0 and d.stake() == 20   # charged once, as printed


def test_roll_detected_from_the_r_and_sold_out_and_reduced_markers():
    d = parse_ticket(FOURD_5551)
    assert [(e.kind, e.number, e.big, e.small) for e in d.entries] == [
        ("ordinary", "8455", 1, 0), ("roll", "R888", 1, 0), ("ordinary", "9363", 0, 2)]
    assert any("sold-out" in w for w in d.warnings) and any("lower stake" in w for w in d.warnings)
    assert d.stake() == 1 + 10 + 2 and d.printed_price == 13.0


def test_fourd_check_against_tonights_draw():
    d = parse_ticket(FOURD_5551)
    rv = build_reveal(d.check(ON_FILE.get), printed_price=d.printed_price, today=date(2026, 10, 22))
    # 8455 Big $1 = 1st $2,000; R888 covers 0888-9888, none drawn; 9363 Small has no consolation.
    assert rv.headline == "You won S$2,000" and rv.stake.state == "match"


def test_short_forms():
    d = parse_ticket("1234 B2 S1\n12R4 B1\ndraw 5551")
    assert d.game == "4d" and [(e.kind, e.number, e.big, e.small) for e in d.entries] == [
        ("ordinary", "1234", 2, 1), ("roll", "12R4", 1, 0)]


def test_system_permutations_line_is_checked():
    d = parse_ticket("4D\nSYSTEM\nA 1123 BIG $1\n  24 PERMUTATIONS\ndraw 5551")
    assert any("24 permutations, 1123 has 12" in w for w in d.warnings)


def test_fully_sold_out_board_is_not_a_bet():
    d = parse_ticket("4D\nA 1234 BIG S'OUT SML S'OUT\nB 5678 BIG $1\ndraw 5551")
    assert [e.number for e in d.entries] == ["5678"]
    assert any("fully sold out" in w for w in d.warnings)


@pytest.mark.parametrize("board,msg", [("A 1234", "no stake found"),
                                       ("A 123 BIG $1", "leading zeros"),
                                       ("A 1111 BIG $1", "")])
def test_fourd_board_errors(board, msg):
    header = "4D\nIBET\n" if board.startswith("A 1111") else "4D\n"
    d = parse_ticket(f"{header}{board}\ndraw 5551")
    assert len(d.errors) == 1 and msg in d.errors[0].message
    if board.startswith("A 1111"):
        assert "can't be played as ibet" in d.errors[0].message


# ---------------- general ----------------

def test_unknown_game():
    d = parse_ticket("hello\nworld")
    assert d.game is None and not d.ready and "TOTO or 4D" in d.errors[0].message


def test_no_draw_is_a_problem_not_a_crash():
    d = parse_ticket("TOTO\nA. 01 02 03 04 05 06")
    assert not d.ready and any("No draw found" in p for p in d.problems())
    with pytest.raises(ValueError, match="not ready"):
        d.check(ON_FILE.get)


def test_draw_number_and_date_in_different_years_warns():
    d = parse_ticket("TOTO\nA. 01 02 03 04 05 06\nTHU 24/09/26 4220/25")
    assert any("different years" in w for w in d.warnings)
