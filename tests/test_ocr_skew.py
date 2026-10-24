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
