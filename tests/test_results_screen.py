"""P4-10 results screenshot reader.

Fixtures in tests/fixtures/screens/ come from the official pages for TOTO 4227
and 4D 5551, opened on 21 Oct 2026 in a 375 px phone view:
- *_page.txt: the page's own text of the results block.
- *_mobile_top.txt: the text visible in the first phone screenshot
  (*_mobile_top.jpg), banner and "Next Draw" noise included.
- *_mobile_bottom.txt: what a second, scrolled screenshot holds (built from the
  page text; the pane could not scroll the phone view, so no image for it).
Real Vision OCR output may order lines differently; that is checked when a
Vision key exists (P3-01). Expected values match the captured draws on Grayskull.
"""
from datetime import date
from pathlib import Path

import pytest

from lottery_checker import fourd, toto
from lottery_checker.manual import EntryError
from lottery_checker.results_screen import (ScreenError, read_images, read_screen,
                                            read_screens, to_result)
from lottery_checker.reveal import build_reveal
from lottery_checker.ticket import check_ticket

S = Path(__file__).parent / "fixtures" / "screens"


def txt(name):
    return (S / f"{name}.txt").read_text(encoding="utf-8")


STARTERS = ["0273", "0436", "2089", "2837", "5006", "6491", "7394", "8072", "8468", "9574"]
CONSOL = ["0030", "0854", "2005", "4062", "4623", "4890", "6736", "6804", "8934", "9363"]
SHARES_4227 = {1: 2928913.0, 2: 68513.0, 3: 1359.0, 4: 200.0, 5: 50.0, 6: 25.0, 7: 10.0}


def test_screenshot_images_are_kept_as_fixtures():
    assert (S / "toto_4227_mobile_top.jpg").stat().st_size > 10_000
    assert (S / "fourd_5551_mobile_top.jpg").stat().st_size > 10_000


# ---------------- TOTO ----------------

def test_toto_full_page_text():
    r = read_screen(txt("toto_4227_page"))
    assert (r.game, r.draw_no, r.draw_date) == ("toto", 4227, date(2026, 10, 19))
    assert r.winning == [2, 15, 19, 20, 27, 30] and r.additional == 5
    assert r.shares == SHARES_4227 and r.complete and r.missing_groups == []


def test_toto_top_screenshot_ignores_next_draw_and_jackpot():
    r = read_screen(txt("toto_4227_mobile_top"))
    assert r.draw_date == date(2026, 10, 19)                 # not "Next Draw Thu, 22 Oct"
    assert r.winning == [2, 15, 19, 20, 27, 30] and r.additional == 5
    assert r.shares == {1: 2928913.0, 2: 68513.0}            # $1,000,000 jackpot not read
    assert r.complete and r.missing_groups == [3, 4]   # 5-7 are fixed prizes, never pending
    assert "Group 3" in r.prompt() and "pending" in r.prompt()


def test_toto_top_and_bottom_merge():
    r = read_screens([txt("toto_4227_mobile_top"), txt("toto_4227_mobile_bottom")])
    assert r.shares == SHARES_4227 and r.missing_groups == []


def test_toto_bottom_screenshot_alone_is_not_enough():
    r = read_screens([txt("toto_4227_mobile_bottom")])
    assert not r.complete and "draw number" in r.missing and "winning numbers" in r.missing
    with pytest.raises(EntryError, match="Still missing"):
        to_result(r)


def test_group1_pool_is_not_read_as_a_share():
    # Two Group 1 winners: pool $3,000,000, each share $1,500,000.
    text = txt("toto_4227_page").replace("Group 1\t$2,928,913\t1", "Group 1\t$1,500,000\t2") \
                                .replace("Group 1 Prize\n$2,928,913", "Group 1 Prize\n$3,000,000")
    assert read_screen(text).shares[1] == 1500000.0


def test_group_with_no_winners_stays_unread():
    text = txt("toto_4227_page").replace("Group 1\t$2,928,913\t1", "Group 1\t-\t-")
    r = read_screen(text)
    assert 1 not in r.shares and r.missing_groups == [1]


def test_column_order_ocr_drops_the_table_instead_of_mispairing():
    # OCR that reads the table column by column could pair Group 7 with $2,928,913.
    text = txt("toto_4227_mobile_top").split("Winning Shares")[0] + \
        "Winning Shares\nGroup 1 $10 1\nGroup 2 $25 9\nGroup 7 $2,928,913 159,045\n"
    r = read_screen(text)
    assert r.shares == {} and any("falling amounts" in n for n in r.notes)
    assert r.complete                                       # numbers still fine; groups pending


def test_toto_screenshot_to_reveal():
    m = to_result(read_screens([txt("toto_4227_mobile_top"), txt("toto_4227_mobile_bottom")]))
    assert m.source == "screenshot"
    r = check_ticket([toto.TotoEntry("ordinary", (2, 15, 19, 20, 27, 5))], [m.ref])   # Group 2
    rv = build_reveal(r, printed_price=1.00, today=date(2026, 10, 20))
    assert rv.headline == "You won S$68,513"


def test_toto_top_only_reveal_is_pending_not_zero():
    m = to_result(read_screen(txt("toto_4227_mobile_top")))
    r = check_ticket([toto.TotoEntry("ordinary", (2, 15, 19, 40, 41, 5))], [m.ref])   # 3 + Add = G6
    rv = build_reveal(r, today=date(2026, 10, 20))
    assert rv.headline == "You won S$25"                     # G6 is fixed, so priced anyway
    r = check_ticket([toto.TotoEntry("ordinary", (2, 15, 19, 20, 41, 42))], [m.ref])  # 4 = G5
    assert build_reveal(r, today=date(2026, 10, 20)).headline == "You won S$50"
    r = check_ticket([toto.TotoEntry("ordinary", (2, 15, 19, 20, 27, 42))], [m.ref])  # 5 = G3
    rv = build_reveal(r, today=date(2026, 10, 20))
    assert rv.state == "pending" and rv.headline == "You won a Group 3 prize"


# ---------------- 4D ----------------

def test_fourd_full_page_text():
    r = read_screen(txt("fourd_5551_page"))
    assert (r.game, r.draw_no, r.draw_date) == ("4d", 5551, date(2026, 10, 21))
    assert (r.first, r.second, r.third) == ("8455", "1103", "3344")
    assert r.starter == STARTERS and r.consolation == CONSOL and r.complete


def test_fourd_top_screenshot_ignores_sweep_banner():
    r = read_screen(txt("fourd_5551_mobile_top"))
    assert r.draw_date == date(2026, 10, 21)                 # not the Sweep "DRAW DATE: Wed, 4 Nov"
    assert (r.first, r.second, r.third) == ("8455", "1103", "3344")
    assert r.starter == STARTERS[:8]                         # "2026" from dates not read as a number
    assert not r.complete
    assert "Starter prizes (8 of 10 read)" in r.missing and "Consolation prizes (0 of 10 read)" in r.missing
    assert "add another screenshot" in r.prompt()


def test_fourd_top_and_scrolled_bottom_merge():
    r = read_screens([txt("fourd_5551_mobile_top"), txt("fourd_5551_mobile_bottom")])
    assert r.starter == STARTERS and r.consolation == CONSOL and r.complete


def test_fourd_order_of_screenshots_does_not_matter():
    r = read_screens([txt("fourd_5551_mobile_bottom"), txt("fourd_5551_mobile_top")])
    assert r.starter == STARTERS and r.complete


def test_fourd_bottom_with_no_overlap_still_places_last_starters():
    bottom = "8468 9574\nConsolation Prizes\n" + "\n".join(CONSOL)
    r = read_screens([txt("fourd_5551_mobile_top"), bottom])
    assert r.starter == STARTERS


def test_fourd_gap_between_screenshots_is_reported_not_filled():
    top = txt("fourd_5551_mobile_top").replace("5006 6491\n7394 8072\n", "")   # only 4 starters
    bottom = "8468 9574\nConsolation Prizes\n" + "\n".join(CONSOL)
    r = read_screens([top, bottom])
    assert len(r.starter) == 4 and not r.complete


def test_fourd_overlap_disagreement_raises():
    bottom = txt("fourd_5551_mobile_bottom").replace("7394 8072", "7394 8073")
    with pytest.raises(ScreenError, match="Starter 8"):
        read_screens([txt("fourd_5551_mobile_top"), bottom])


def test_fourd_screenshot_to_reveal():
    m = to_result(read_screens([txt("fourd_5551_mobile_top"), txt("fourd_5551_mobile_bottom")]))
    r = check_ticket([fourd.FourDEntry("ordinary", "8455", big=1),
                      fourd.FourDEntry("ordinary", "9363", big=1)], [m.ref])     # 1st + consolation
    rv = build_reveal(r, printed_price=2.00, today=date(2026, 10, 22))
    assert rv.headline == "You won S$2,060" and rv.stake.state == "match"


# ---------------- guards ----------------

def test_screenshots_of_different_draws_are_refused():
    other = txt("fourd_5551_mobile_top").replace("Draw No. 5551", "Draw No. 5550")
    with pytest.raises(ScreenError, match="different draws"):
        read_screens([txt("fourd_5551_mobile_top"), other])


def test_toto_and_4d_mixed_refused():
    with pytest.raises(ScreenError, match="mix"):
        read_screens([txt("toto_4227_page"), txt("fourd_5551_page")])


def test_unrelated_screenshot_refused():
    with pytest.raises(ScreenError, match="no TOTO or 4D"):
        read_screens(["Photo of my cat\nTaken 21 Oct"])


def test_read_images_goes_through_ocr():
    class Fake:
        def __init__(self, t): self.text = t
    texts = iter([txt("fourd_5551_mobile_top"), txt("fourd_5551_mobile_bottom")])
    r = read_images([b"img1", b"img2"], recognize=lambda b: Fake(next(texts)))
    assert r.complete and r.draw_no == 5551


# ---------------------------------------------------------------- batch: several draws at once

from datetime import date as _date  # noqa: E402

from lottery_checker.results_screen import sort_by_draw  # noqa: E402

_TOP = (S / "toto_4227_mobile_top.txt").read_text(encoding="utf-8")
_BOTTOM = (S / "toto_4227_mobile_bottom.txt").read_text(encoding="utf-8")
# A second draw for multi-draw tests: the 4227 page with another draw's header and numbers (test data).
_TOP_4228 = (_TOP.replace("Draw No. 4227", "Draw No. 4228").replace("Mon, 19 Oct 2026", "Thu, 22 Oct 2026")
             .replace("2 15 19 20 27 30", "3 8 11 25 33 47").replace("Additional Number\n5", "Additional Number\n12"))
WANT = [(4227, _date(2026, 10, 19)), (4228, _date(2026, 10, 22))]


def test_batch_sorts_screenshots_to_their_draws():
    b = sort_by_draw([read_screen(t) for t in (_TOP, _BOTTOM, _TOP_4228, _BOTTOM)], WANT)
    assert sorted(b.draws) == [4227, 4228] and b.notes == []
    assert b.draws[4227].winning == [2, 15, 19, 20, 27, 30]
    assert b.draws[4228].winning == [3, 8, 11, 25, 33, 47] and b.draws[4228].additional == 12
    assert b.draws[4227].shares[4] == 200.0 and b.draws[4228].shares[4] == 200.0   # bottom joined the one before


def test_batch_any_order_of_draws():
    b = sort_by_draw([read_screen(t) for t in (_TOP_4228, _TOP)], WANT)
    assert b.draws[4228].draw_no == 4228 and b.draws[4227].draw_no == 4227


def test_batch_matches_by_date_when_the_number_did_not_read():
    no_number = _TOP_4228.replace("Draw No. 4228", "Draw No.")
    b = sort_by_draw([read_screen(no_number)], WANT)
    assert list(b.draws) == [4228]


def test_batch_prize_table_first_is_skipped_with_a_note():
    b = sort_by_draw([read_screen(_BOTTOM), read_screen(_TOP)], WANT)
    assert list(b.draws) == [4227] and any("Screenshot 1" in n for n in b.notes)


def test_batch_draw_not_on_ticket_and_missing_draw_are_reported():
    b = sort_by_draw([read_screen(_TOP)], [(4228, _date(2026, 10, 22)), (4231, None)])
    assert not b.draws and any("4227, which isn't on this ticket" in n for n in b.notes)
    b = sort_by_draw([read_screen(_TOP)], WANT)
    assert any("No screenshot yet for draw 4228" in n for n in b.notes)


def test_batch_single_draw_ticket_takes_a_prize_table_on_its_own():
    b = sort_by_draw([read_screen(_BOTTOM)], [(4227, _date(2026, 10, 19))])
    assert b.draws[4227].shares[4] == 200.0 and b.notes == []


# ---------------------------------------------------------------- draw dates (live bug 22 Oct)
from lottery_checker.results_screen import expected_date, plausible_date  # noqa: E402


def test_next_draw_date_on_its_own_line_is_not_the_draw_date():
    """Phone screenshots of draw 4216 were saved as 22 Oct: Vision put 'Next Draw'
    and its date on different lines, with the jackpot between."""
    text = ("Results\nTOTO Next Jackpot $1,000,000 est\nNext Draw\nest\nThu, 22 Oct 2026 , 6.30pm\n"
            "Thu, 10 Sep 2026 Draw No. 4216\nWinning Numbers\n6 16 26 30 39 42\nAdditional Number\n27")
    r = read_screen(text)
    assert r.draw_no == 4216 and str(r.draw_date) == "2026-09-10"


def test_a_date_that_cannot_belong_to_the_draw_number_is_dropped():
    text = "Thu, 22 Oct 2026 Draw No. 4216\nWinning Numbers\n6 16 26 30 39 42\nAdditional Number\n27"
    r = read_screen(text)
    assert r.draw_no == 4216 and r.draw_date is None and "draw date" in r.missing


def test_expected_dates_from_draw_numbers():
    assert abs((expected_date("toto", 4216) - _date(2026, 9, 10)).days) <= 2
    assert abs((expected_date("toto", 4161) - _date(2026, 3, 2)).days) <= 4      # 2026 rules start
    assert abs((expected_date("4d", 5500) - _date(2026, 6, 24)).days) <= 6
    assert plausible_date("toto", 4228, _date(2026, 10, 22))
    assert not plausible_date("toto", 4216, _date(2026, 10, 22))


def test_ticket_date_fills_in_when_the_screenshot_date_was_unusable():
    bad = "Thu, 22 Oct 2026 Draw No. 4216\nWinning Numbers\n6 16 26 30 39 42\nAdditional Number\n27"
    b = sort_by_draw([read_screen(bad)], [(4216, _date(2026, 9, 10))])
    assert str(b.draws[4216].draw_date) == "2026-09-10" and b.draws[4216].complete
