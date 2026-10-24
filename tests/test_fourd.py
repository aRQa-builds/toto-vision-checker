import pytest

from lottery_checker.fourd import (
    FourDDraw, FourDEntry, FourDError, check_entry, check_ticket, permutation_count, ticket_cost,
)

DRAW = FourDDraw(
    draw_no=1, first="1234", second="5678", third="9012",
    starter=("0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "1243", "3412"),
    consolation=("1000", "2000", "3000", "4000", "5000", "6000", "7000", "8000", "9000", "4321"),
)


def amount(kind, number, big=0, small=0, draw=DRAW):
    return check_entry(FourDEntry(kind, number, big, small), draw).amount


# ---------- Ordinary, Big and Small in each category ----------

@pytest.mark.parametrize("number,big,small,expected", [
    ("1234", 1, 0, 2000), ("1234", 0, 1, 3000), ("1234", 1, 1, 5000),
    ("5678", 1, 0, 1000), ("5678", 0, 1, 2000),
    ("9012", 1, 0, 490), ("9012", 0, 1, 800),
    ("0001", 1, 0, 250), ("0001", 0, 1, 0),     # Small has no starter
    ("4321", 2, 0, 120), ("4321", 0, 2, 0),     # Small has no consolation
    ("9999", 5, 5, 0),
])
def test_ordinary(number, big, small, expected):
    assert amount("ordinary", number, big, small) == expected


def test_same_number_in_two_categories_wins_both():
    d = FourDDraw(2, "1111", "5678", "2222",
                  tuple(f"{i:04d}" for i in range(10)),
                  ("5678",) + tuple(f"{i:04d}" for i in range(10, 19)))
    assert amount("ordinary", "5678", big=1, draw=d) == 1000 + 60    # rule 4.6


# ---------- 4D Roll ----------

def test_roll_covers_ten_and_costs_ten_times():
    e = FourDEntry("roll", "12R4", big=1)
    assert e.covered() == [f"12{d}4" for d in range(10)]
    assert e.cost_per_draw == 10
    assert check_entry(e, DRAW).amount == 2000          # 1234 is first


def test_roll_accepts_x_marker():
    assert FourDEntry("roll", "58x2", big=1).covered()[0] == "5802"


@pytest.mark.parametrize("bad", ["12R", "R2R4", "12A4", "1234"])
def test_roll_bad(bad):
    with pytest.raises(FourDError):
        FourDEntry("roll", bad, big=1)


# ---------- System ----------

@pytest.mark.parametrize("number,perms", [("1234", 24), ("1123", 12), ("1122", 6), ("1112", 4)])
def test_permutation_counts(number, perms):
    assert permutation_count(number) == perms
    assert FourDEntry("system", number, big=1).cost_per_draw == perms


def test_system_pays_every_winning_permutation():
    # 1234 first, 1243 + 3412 starter, 4321 consolation
    assert amount("system", "1234", big=1) == 2000 + 250 + 250 + 60


def test_system_single_permutation_rejected():
    with pytest.raises(FourDError):
        FourDEntry("system", "1111", big=1)


def test_multi_day_stake_matches_2021_rules_example():
    # 1234 System, $2 per permutation, Sat and Sun = 24 x 2 x 2 = $96
    assert ticket_cost([FourDEntry("system", "1234", big=2)], n_draws=2) == 96


# ---------- iBet ----------

def test_ibet_costs_marked_amount_once():
    assert FourDEntry("ibet", "1234", big=1).cost_per_draw == 1


def test_ibet_amounts_by_pattern_from_table():
    d = FourDDraw(3, "1123", "1122", "1112",
                  tuple(f"{i:04d}" for i in range(10)), tuple(f"{i:04d}" for i in range(10, 20)))
    assert amount("ibet", "3211", big=1, draw=d) == 166     # one pair, first
    assert amount("ibet", "2211", big=1, draw=d) == 168     # two pairs, second
    assert amount("ibet", "2111", big=1, draw=d) == 127     # three same, third
    assert amount("ibet", "3211", small=1, draw=d) == 250


def test_ibet_multiple_winning_permutations_each_paid():
    # ASSUMPTION (open item 7 in the rules reference): each matching prize pays.
    assert amount("ibet", "4321", big=1) == 83 + 10 + 10 + 3


# ---------- Validation and multi-draw ----------

def test_minimum_stake():
    with pytest.raises(FourDError):
        FourDEntry("ordinary", "1234")


def test_multi_draw_mixed():
    other = FourDDraw(4, "0000", "1111", "2222",
                      tuple(f"{i:04d}" for i in range(10, 20)), tuple(f"{i:04d}" for i in range(20, 30)))
    res = check_ticket([FourDEntry("ordinary", "1234", big=1)], [DRAW, other])
    assert [r.amount for r in res] == [2000, 0]
