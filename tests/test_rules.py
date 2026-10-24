"""P2-01: the rules registry, and that a draw is priced from its own rule set."""
import dataclasses

import pytest

from lottery_checker import rules
from lottery_checker.fourd import FourDDraw, FourDEntry, check_entry as check_4d
from lottery_checker.rules import RulesError, rules_for
from lottery_checker.toto import TotoDraw, TotoEntry, check_entry as check_toto


# ---------- Picking a version ----------

@pytest.mark.parametrize("game,draw_no,version", [
    ("toto", 3751, "toto-2022"),     # first draw of the 2022 rules
    ("toto", 4160, "toto-2022"),     # last draw before the 2026 rules
    ("toto", 4161, "toto-2026-03-02"),   # first draw of the 2026 rules
    ("toto", 9999, "toto-2026-03-02"),
    ("4d", 5269, "4d-2024-12-30"),
    ("4d", 9999, "4d-2024-12-30"),
])
def test_version_in_force_either_side_of_a_cutover(game, draw_no, version):
    assert rules_for(game, draw_no).version == version


def test_no_draw_number_gives_the_latest():
    assert rules_for("toto") is rules.TOTO_2026
    assert rules_for("4d") is rules.FOURD_2024


@pytest.mark.parametrize("game,draw_no", [("toto", 3750), ("4d", 5268), ("4d", 1)])
def test_draw_older_than_any_version_raises(game, draw_no):
    with pytest.raises(RulesError):
        rules_for(game, draw_no)


def test_unknown_game_raises():
    with pytest.raises(RulesError):
        rules_for("sweep", 1)


def test_versions_are_ordered_oldest_first_and_distinct():
    for game, versions in rules.REGISTRY.items():
        firsts = [v.first_draw for v in versions]
        assert firsts == sorted(firsts) and len(set(firsts)) == len(firsts), game
        assert len({v.version for v in versions}) == len(versions), game


# ---------- A draw is priced from its own rule set ----------

def test_toto_draw_prices_from_its_own_fixed_prizes():
    custom = dataclasses.replace(rules.TOTO_2026, version="test", fixed_prizes={5: 99, 6: 25, 7: 10})
    draw = TotoDraw(1, (1, 2, 3, 4, 5, 6), 7, rules=custom)
    assert check_toto(TotoEntry("ordinary", (1, 2, 3, 4, 8, 9)), draw).amount == 99
    # The same entry on a draw with the real rules still pays the published $50.
    assert check_toto(TotoEntry("ordinary", (1, 2, 3, 4, 8, 9)),
                      TotoDraw(2, (1, 2, 3, 4, 5, 6), 7)).amount == 50


def test_fourd_draw_prices_from_its_own_tables():
    custom = dataclasses.replace(
        rules.FOURD_2024, version="test",
        ordinary_prizes={"big": {"first": 1234}, "small": {"first": 3000}},
    )
    tens = tuple(f"{i:04d}" for i in range(10))
    draw = FourDDraw(5300, "1234", "5678", "9012", tens, tens[::-1], rules=custom)
    assert check_4d(FourDEntry("ordinary", "1234", big=1), draw).amount == 1234


def test_draw_without_rules_defaults_to_latest():
    assert TotoDraw(1, (1, 2, 3, 4, 5, 6), 7).rules is rules.TOTO_2026
    tens = tuple(f"{i:04d}" for i in range(10))
    assert FourDDraw(1, "1234", "5678", "9012", tens, tens[::-1]).rules is rules.FOURD_2024


def test_both_toto_versions_are_verified():
    # toto-2022 was checked against the 2022 rules PDF on 18 Oct 2026.
    assert rules_for("toto", 4068).verified is True
    assert rules_for("toto", 4161).verified is True
