"""P4-11 manual results entry, checked against draws the capture stored for real."""
from datetime import date

import pytest

from lottery_checker import fourd, toto
from lottery_checker.manual import (EntryError, fourd_result, parse_amount,
                                    parse_fourd_numbers, parse_toto_numbers, toto_result)
from lottery_checker.reveal import USER_ATTRIBUTION, build_reveal
from lottery_checker.ticket import check_ticket

# TOTO 4227, Mon 19 Oct 2026, as captured on Grayskull (data/draws/toto/4227.json).
T4227 = dict(numbers="2 15 19 20 27 30 + 5",
             amounts={1: "S$2,928,913", 2: "68,513", 3: "1359", 4: "$200"})
# 4D 5551, Wed 21 Oct 2026, as captured on Grayskull at 19:00 (data/draws/4d/5551.json).
F5551 = """1st 8455  2nd 1103  3rd 3344
Starter 0273 0436 2089 2837 5006 6491 7394 8072 8468 9574
Consolation 0030 0854 2005 4062 4623 4890 6736 6804 8934 9363"""


# ---------------- text helpers ----------------

@pytest.mark.parametrize("text,main,add", [
    ("2 15 19 20 27 30 + 5", [2, 15, 19, 20, 27, 30], 5),
    ("2,15,19,20,27,30 Additional 5", [2, 15, 19, 20, 27, 30], 5),
    ("2 15 19 20 27 30 Add no. 5", [2, 15, 19, 20, 27, 30], 5),
    ("02 15 19 20 27 30 05", [2, 15, 19, 20, 27, 30], 5),       # 7th taken as Additional
    ("2 15 19 20 27 30", [2, 15, 19, 20, 27, 30], None),
])
def test_parse_toto_numbers(text, main, add):
    assert parse_toto_numbers(text) == (main, add)


@pytest.mark.parametrize("text,v", [("S$2,928,913", 2928913.0), ("68,513", 68513.0), ("$200", 200.0),
                                    ("1566.50", 1566.5), ("", None), ("-", None), (None, None), (50, 50.0)])
def test_parse_amount(text, v):
    assert parse_amount(text) == v


@pytest.mark.parametrize("bad", ["abc", "0", "-5"])
def test_parse_amount_refuses_nonsense(bad):
    with pytest.raises(EntryError):
        parse_amount(bad)


def test_fourd_keeps_leading_zeros_and_refuses_short_numbers():
    assert parse_fourd_numbers("0273, 0030 8455") == ["0273", "0030", "8455"]
    with pytest.raises(EntryError, match="273"):
        parse_fourd_numbers("273 8455")


# ---------------- TOTO ----------------

def test_toto_entry_matches_the_captured_draw():
    m = toto_result(4227, date(2026, 10, 19), T4227["numbers"], group_amounts=T4227["amounts"])
    d = m.ref.draw
    assert d.winning == (2, 15, 19, 20, 27, 30) and d.additional == 5
    assert d.prize_for(1) == 2928913.0 and d.prize_for(4) == 200.0
    assert d.prize_for(5) == 50 and d.prize_for(7) == 10           # fixed groups by default
    assert d.rules.version == "toto-2026-03-02"
    assert m.warnings == [] and m.source == "user"


def test_toto_group_amounts_optional_and_win_stays_pending():
    m = toto_result(4227, date(2026, 10, 19), "2 15 19 20 27 30 + 5")
    assert any("Group 1, Group 2, Group 3, Group 4" in w for w in m.warnings)
    # 5 + Additional = Group 2, no amount typed -> pending, never S$0.
    r = check_ticket([toto.TotoEntry("ordinary", (2, 15, 19, 20, 27, 5))], [m.ref])
    rv = build_reveal(r, today=date(2026, 10, 20), results_source="user")
    assert rv.state == "pending" and rv.headline == "You won a Group 2 prize"
    assert rv.subline == "Add the Group 2 amount from the official result to see your total."
    assert rv.lines[0].result_text == "Group 2: amount not entered"
    assert "S$0" not in rv.headline + rv.subline and rv.attribution == USER_ATTRIBUTION


def test_toto_typed_entry_prices_like_the_capture():
    m = toto_result(4227, date(2026, 10, 19), T4227["numbers"], group_amounts=T4227["amounts"])
    entries = [toto.TotoEntry("ordinary", (2, 15, 19, 20, 27, 5)),     # Group 2
               toto.TotoEntry("ordinary", (2, 15, 19, 40, 41, 42))]    # Group 7
    rv = build_reveal(check_ticket(entries, [m.ref]), printed_price=2.00,
                      today=date(2026, 10, 20), results_source="user")
    assert rv.headline == "You won S$68,523" and rv.stake.state == "match"


def test_cascade_override_of_fixed_group_warns_but_is_used():
    m = toto_result(4227, date(2026, 10, 19), T4227["numbers"],
                    group_amounts={**T4227["amounts"], 5: "75"})
    assert m.ref.draw.prize_for(5) == 75.0
    assert any("usually S$50" in w for w in m.warnings)


def test_out_of_order_amounts_warn():
    m = toto_result(4227, date(2026, 10, 19), T4227["numbers"],
                    group_amounts={1: "1,000,000", 2: "68,513", 3: "1359", 4: "13590"})
    assert any("Group 3" in w and "Group 4" in w for w in m.warnings)


@pytest.mark.parametrize("numbers,match", [
    ("2 15 19 20 27 + 5", "6 winning numbers"),
    ("2 15 19 20 27 30", "Additional Number too"),
    ("2 15 19 20 27 50 + 5", "1 to 49"),
    ("2 15 15 20 27 30 + 5", "appears twice"),
    ("2 15 19 20 27 30 + 30", "cannot be one of the six"),
])
def test_toto_bad_input_says_what_to_fix(numbers, match):
    with pytest.raises(EntryError, match=match):
        toto_result(4227, date(2026, 10, 19), numbers)


def test_unknown_group_refused():
    with pytest.raises(EntryError, match="no Group 8"):
        toto_result(4227, date(2026, 10, 19), T4227["numbers"], group_amounts={8: "10"})


def test_too_old_draw_refused_not_mispriced():
    with pytest.raises(EntryError, match="older than the rules"):
        toto_result(100, date(2000, 1, 1), T4227["numbers"])


# ---------------- 4D ----------------

def test_fourd_pasted_page_text_matches_the_captured_draw():
    m = fourd_result(5551, date(2026, 10, 21), F5551)
    d = m.ref.draw
    assert (d.first, d.second, d.third) == ("8455", "1103", "3344")
    assert d.starter[0] == "0273" and d.consolation[0] == "0030"
    assert len(d.starter) == len(d.consolation) == 10
    assert d.rules.version == "4d-2024-12-30" and m.warnings == []


def test_fourd_list_input_and_a_real_check():
    nums = F5551.replace("1st", "").replace("2nd", "").replace("3rd", "")
    nums = nums.replace("Starter", "").replace("Consolation", "").split()
    m = fourd_result(5551, date(2026, 10, 21), nums)
    r = check_ticket([fourd.FourDEntry("ordinary", "8455", big=1),
                      fourd.FourDEntry("ordinary", "0273", big=1, small=1)], [m.ref])
    rv = build_reveal(r, printed_price=3.00, today=date(2026, 10, 22), results_source="user")
    assert rv.headline == "You won S$2,250" and rv.attribution == USER_ATTRIBUTION


def test_fourd_wrong_count():
    with pytest.raises(EntryError, match="23 numbers"):
        fourd_result(5551, date(2026, 10, 21), F5551.replace(" 9363", ""))


def test_fourd_list_with_short_number_refused():
    with pytest.raises(EntryError, match="273"):
        fourd_result(5551, date(2026, 10, 21), ["8455", "1103", "3344", "273"] + ["0000"] * 19)


def test_fourd_duplicate_number_warns():
    m = fourd_result(5551, date(2026, 10, 21), F5551.replace("9363", "8455"))
    assert any("8455 appears more than once" in w for w in m.warnings)


def test_bad_draw_number():
    with pytest.raises(EntryError, match="positive whole number"):
        fourd_result(0, date(2026, 10, 21), F5551)


def test_official_source_keeps_official_attribution():
    m = fourd_result(5551, date(2026, 10, 21), F5551)
    rv = build_reveal(check_ticket([fourd.FourDEntry("ordinary", "7777", big=1)], [m.ref]))
    assert "Singapore Pools (singaporepools.com.sg)" in rv.attribution


def test_unknown_results_source_refused():
    m = fourd_result(5551, date(2026, 10, 21), F5551)
    with pytest.raises(ValueError):
        build_reveal(check_ticket([fourd.FourDEntry("ordinary", "7777", big=1)], [m.ref]),
                     results_source="screenshot")
