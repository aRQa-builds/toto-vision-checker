"""Tilted tickets keep their rows apart (23 Oct 2026: a few degrees of tilt merged two boards)."""
import math

import pytest

from lottery_checker.ocr import OcrResult, Word

ROWS = ["TOTO", "ORDINARY", "A. 03 08 11 19 27 30 QP", "B. 05 12 22 31 38 44 QP",
        "PRICE: $4.00", "DRAW:", "MON 19/10/26 4227/26", "THU 22/10/26 4228/26"]


def build(deg):
    t = math.radians(deg)
    words = []
    for r, row in enumerate(ROWS):
        x = 100
        for tok in row.split():
            wd = 14 * len(tok) + 4
            cx, cy = x + wd / 2, 100 + r * 60
            X = cx * math.cos(t) - cy * math.sin(t)
            Y = cx * math.sin(t) + cy * math.cos(t)
            words.append(Word(tok, (int(X - wd / 2), int(Y - 20), int(X + wd / 2), int(Y + 20))))
            x += wd + 14
    return OcrResult(" ".join(ROWS), words)


@pytest.mark.parametrize("deg", [0, 3, -3, 6, -6, 9])
def test_rows_survive_tilt(deg):
    assert build(deg).lines() == ROWS


def test_skew_estimate_close():
    for deg in (3, 6, -6):
        assert abs(build(deg).skew() - deg) <= 1.0


def test_few_words_not_rotated():
    r = OcrResult("A B", [Word("A", (0, 0, 10, 10)), Word("B", (20, 2, 30, 12))])
    assert r.skew() == 0.0


# ---------------------------------------------------------------- P3-02-R1: row anchor (5 Nov 2026)

def _w(text, x, y, h):
    return Word(text, (int(x - 20), int(y - h / 2), int(x + 20), int(y + h / 2)))


def test_a_tall_watermark_word_does_not_split_a_board_row():
    """Real TOTO photo a02 (now 07_toto_ordinary_4216_4217.jpg) (word centres after deskew, 5 Nov 2026). The watermark word INGAPORE
    (h 28, y 562) started board B's row; 3.04 (h 37, y 584) was 22 px away, just over the
    0.6 x 37 = 22.2 tolerance measured from that first word, so the row split in two."""
    words = [_w("A.", 92, 539, 34), _w("12", 137, 538, 35), _w("13", 201, 538, 35),
             _w("14", 266, 538, 36), _w("16", 332, 537, 35), _w("26", 395, 537, 36),
             _w("39", 461, 537, 35),
             _w("INGAPORE", 127, 562, 28), _w("B.", 91, 577, 18), _w("3.04", 116, 584, 37),
             _w("24", 200, 583, 36), _w("28", 266, 583, 35), _w("33", 333, 582, 35),
             _w("38", 397, 582, 36), _w("39", 462, 582, 35),
             _w("PRICE", 100, 637, 24), _w("4.00", 311, 637, 24)]
    rows = OcrResult("", words).lines()
    assert rows[0] == "A. 12 13 14 16 26 39"
    assert rows[1].split()[:3] == ["B.", "3.04", "INGAPORE"] and rows[1].endswith("24 28 33 38 39")
    assert rows[2] == "PRICE 4.00"


def test_4d_bet_rows_keep_number_and_stake_together():
    """Real 4D photo a05 (now 10_4d_ordinary_10line_5553.jpg): the big number (h 32) sits about 10 px below its small stake text (h 18)."""
    words = [_w("B.", 148, 454, 18), _w("BIG", 330, 455, 18), _w("1", 372, 455, 18),
             _w("SML", 450, 454, 19), _w("0", 508, 454, 19),
             _w("1310", 214, 464, 32),
             _w("C.", 149, 502, 18), _w("2310", 214, 512, 47), _w("BIG", 330, 502, 18),
             _w("1", 372, 501, 18), _w("SML", 450, 502, 19), _w("0", 509, 502, 21)]
    rows = OcrResult("", words).lines()
    assert len(rows) == 2
    assert rows[0].split() == ["B.", "1310", "BIG", "1", "SML", "0"]
    assert rows[1].split() == ["C.", "2310", "BIG", "1", "SML", "0"]
