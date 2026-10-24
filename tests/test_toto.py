import pytest

from lottery_checker.toto import (
    TotoDraw, TotoEntry, TotoError, check_entry, check_ticket, grade_set, winning_shares,
)
from tests.golden_cl516 import COLS, OFFICIAL

# Winning 1-6, Additional 7, for the constructed scenarios.
DRAW = TotoDraw(draw_no=1, winning=(1, 2, 3, 4, 5, 6), additional=7)
FILLERS = list(range(8, 50))


# ---------- Ordinary: one case per group, plus the Additional edge (cl. 2.2, 5.5) ----------

@pytest.mark.parametrize("six,group", [
    ((1, 2, 3, 4, 5, 6), 1),
    ((1, 2, 3, 4, 5, 7), 2),
    ((1, 2, 3, 4, 5, 8), 3),
    ((1, 2, 3, 4, 7, 8), 4),
    ((1, 2, 3, 4, 8, 9), 5),
    ((1, 2, 3, 7, 8, 9), 6),
    ((1, 2, 3, 8, 9, 10), 7),
    ((1, 2, 7, 8, 9, 10), None),   # 2 + Additional: the Additional never makes up a match
    ((7, 8, 9, 10, 11, 12), None),
])
def test_ordinary_groups(six, group):
    assert grade_set(six, DRAW) == group


# ---------- Golden set: the full official cl. 5.16 table, via real constructed entries ----------

def _entry_for(col, w, a):
    """Build an entry whose chosen numbers contain w winners and (if a) the Additional."""
    size = 5 if col == "roll" else col
    others = size - w - a
    if others < 0:
        return None
    nums = list(DRAW.winning[:w]) + ([DRAW.additional] if a else []) + FILLERS[:others]
    kind = "roll" if col == "roll" else ("ordinary" if col == 6 else "system")
    return TotoEntry(kind, tuple(nums))


CASES = [(w, a, ci, col) for (w, a) in OFFICIAL for ci, col in enumerate(COLS)]


@pytest.mark.parametrize("w,a,ci,col", CASES, ids=[f"w{w}a{a}-{c}" for w, a, _, c in CASES])
def test_official_cl516_table(w, a, ci, col):
    expected = {g: vals[ci] for g, vals in OFFICIAL[(w, a)].items() if vals[ci] is not None}
    entry = _entry_for(col, w, a)
    if entry is None:                      # scenario impossible for this entry size
        assert expected == {}
        return
    assert dict(winning_shares(entry, DRAW)) == expected


# ---------- Official worked examples in the 2026 rules ----------

def test_cl58_example_payout():
    entry = TotoEntry("system", (3, 8, 14, 21, 22, 26, 34))
    draw = TotoDraw(2, (7, 21, 22, 26, 33, 42), 14)
    r = check_entry(entry, draw)
    assert dict(r.shares) == {6: 3, 7: 1}           # Sets A, F, G = G6; E = G7
    assert r.amount == 3 * 25 + 10


def test_cl515_example_shares_and_unpriced_pool_groups():
    entry = TotoEntry("system", (3, 8, 14, 21, 22, 26, 34))
    draw = TotoDraw(3, (3, 8, 21, 22, 26, 39), 14)
    r = check_entry(entry, draw)
    assert dict(r.shares) == {2: 1, 3: 1, 4: 5}
    assert r.amount is None and r.unpriced_groups == (2, 3, 4)
    priced = TotoDraw(3, (3, 8, 21, 22, 26, 39), 14, group_prizes={2: 90000.0, 3: 1800.0, 4: 400.0})
    assert check_entry(entry, priced).amount == 90000 + 1800 + 5 * 400


def test_cl514_example_ordinary():
    draw = TotoDraw(4, (1, 5, 17, 23, 41, 49), 32)
    assert grade_set((1, 5, 17, 23, 32, 41), draw) == 2
    assert grade_set((3, 5, 23, 32, 38, 41), draw) == 6


def test_cascade_amount_comes_from_draw_data():
    # On a cascade draw the published Group 5 amount includes the jackpot share.
    draw = TotoDraw(5, (1, 2, 3, 4, 5, 6), 7, group_prizes={5: 1234.5})
    assert check_entry(TotoEntry("ordinary", (1, 2, 3, 4, 8, 9)), draw).amount == 1234.5


# ---------- Stakes and validation ----------

@pytest.mark.parametrize("nums,stake", [
    ((1, 2, 3, 4, 5, 6), 1), ((1, 2, 3, 4, 5, 6, 7), 7), (tuple(range(1, 13)), 924),
])
def test_stakes(nums, stake):
    kind = "ordinary" if len(nums) == 6 else "system"
    assert TotoEntry(kind, nums).stake == stake


def test_roll_covers_44_sets_and_costs_44():
    e = TotoEntry("roll", (1, 2, 3, 4, 5))
    assert len(list(e.sets())) == 44 and e.stake == 44


@pytest.mark.parametrize("kind,nums", [
    ("ordinary", (1, 2, 3, 4, 5)), ("ordinary", (1, 1, 2, 3, 4, 5)),
    ("ordinary", (0, 2, 3, 4, 5, 6)), ("system", tuple(range(1, 14))), ("roll", (1, 2, 3, 4, 5, 6)),
])
def test_bad_entries(kind, nums):
    with pytest.raises(TotoError):
        TotoEntry(kind, nums)


def test_additional_cannot_repeat_winning():
    with pytest.raises(TotoError):
        TotoDraw(9, (1, 2, 3, 4, 5, 6), 6)


# ---------- Multi-draw ----------

def test_multi_draw_mixed_results():
    entry = TotoEntry("ordinary", (1, 2, 3, 10, 11, 12))
    draws = [
        TotoDraw(10, (1, 2, 3, 20, 21, 22), 30),   # 3 hits -> G7
        TotoDraw(11, (40, 41, 42, 43, 44, 45), 1),  # no win
        TotoDraw(12, (1, 2, 3, 10, 30, 31), 11),    # 4 + Additional -> G4 (pool, unpriced)
    ]
    res = check_ticket([entry], draws)
    assert [dict(r.shares) for r in res] == [{7: 1}, {}, {4: 1}]
    assert [r.amount for r in res] == [10, 0, None]
