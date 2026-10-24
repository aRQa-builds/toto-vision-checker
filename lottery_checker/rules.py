"""Rules registry (P2-01): one rule set per game, keyed by the first draw it applies to.

Keyed by draw number, not date: the rules themselves say "from Draw N", and a
cutover day is ambiguous by date alone (the 2026 TOTO rules took effect at
17:00 on 2 Mar 2026, mid-day). Draw numbers are printed on tickets and on the
official results pages, so a parsed or scanned draw always has one.

Adding a version: append a new frozen entry with its first_draw and never edit
a released one, so a stored draw keeps meaning what it meant when captured.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


class RulesError(ValueError):
    """No rule set covers this draw. Raised rather than guessing a version."""


@dataclass(frozen=True)
class TotoRules:
    version: str
    first_draw: int
    fixed_prizes: Mapping[int, int]      # Groups 5-7, per winning combination (cl. 5.5)
    system_sizes: Mapping[int, int]      # numbers chosen -> sets (= stake in S$)
    roll_sets: int
    cascade_trigger: int                 # consecutive unwon draws before the cascade (cl. 5.12)
    source: str
    verified: bool = True


@dataclass(frozen=True)
class FourDRules:
    version: str
    first_draw: int
    ordinary_prizes: Mapping[str, Mapping[str, int]]
    ibet_prizes: Mapping[str, Mapping[str, Mapping[int, int]]]
    source: str
    verified: bool = True


_SYSTEM_SIZES = {7: 7, 8: 28, 9: 84, 10: 210, 11: 462, 12: 924}

TOTO_2022 = TotoRules(
    version="toto-2022",
    first_draw=3751,
    fixed_prizes={5: 50, 6: 25, 7: 10},
    system_sizes=_SYSTEM_SIZES,
    roll_sets=44,
    cascade_trigger=4,
    source=("TOTO Game Rules (General) Version 1, w.e.f. 28 Mar 2022 (Draw 3751/2022), "
            "rules 5.4, 7.2, 7.6, 7.7. Checked against the 2022 PDF on 18 Oct 2026: fixed "
            "prizes, System stakes, Roll 44, cascade at 4 draws and the winning-shares table "
            "all match the 2026 values."),
)

TOTO_2026 = TotoRules(
    version="toto-2026-03-02",
    first_draw=4161,
    fixed_prizes={5: 50, 6: 25, 7: 10},
    system_sizes=_SYSTEM_SIZES,
    roll_sets=44,
    cascade_trigger=4,
    source="TOTO Game Rules w.e.f. 2 Mar 2026 17:00 (Draw 4161/2026), cl. 3.5, 5.5, 5.12, 5.16",
)

_FOURD_ORDINARY = {
    "big": {"first": 2000, "second": 1000, "third": 490, "starter": 250, "consolation": 60},
    "small": {"first": 3000, "second": 2000, "third": 800},
}

# Keyed by the permutation count of the winning number:
# 24 = all digits different, 12 = one pair, 6 = two pairs, 4 = three the same.
_FOURD_IBET = {
    "big": {
        "first": {24: 83, 12: 166, 6: 335, 4: 500},
        "second": {24: 41, 12: 83, 6: 168, 4: 250},
        "third": {24: 20, 12: 40, 6: 85, 4: 127},
        "starter": {24: 10, 12: 20, 6: 41, 4: 62},
        "consolation": {24: 3, 12: 6, 6: 10, 4: 15},
    },
    "small": {
        "first": {24: 125, 12: 250, 6: 500, 4: 750},
        "second": {24: 83, 12: 167, 6: 333, 4: 500},
        "third": {24: 33, 12: 66, 6: 133, 4: 200},
    },
}

FOURD_2024 = FourDRules(
    version="4d-2024-12-30",
    first_draw=5269,
    ordinary_prizes=_FOURD_ORDINARY,
    ibet_prizes=_FOURD_IBET,
    source="4D Game Rules dated 30 Dec 2024 (Draw 5269/2024), prize tables in rule 5",
)

# Oldest first, per game.
REGISTRY: Mapping[str, tuple] = {
    "toto": (TOTO_2022, TOTO_2026),
    # The 2021 4D rules carry the same prize tables, but no draw number is recorded
    # for when they started, so no version is registered for them: a 4D draw before
    # 5269 raises RulesError rather than being priced from a guess.
    "4d": (FOURD_2024,),
}


def rules_for(game: str, draw_no: Optional[int] = None):
    """The rule set in force for a draw number. draw_no=None gives the latest."""
    versions = REGISTRY.get(game)
    if not versions:
        raise RulesError(f"unknown game {game!r}; known games: {sorted(REGISTRY)}")
    if draw_no is None:
        return versions[-1]
    in_force = [r for r in versions if r.first_draw <= draw_no]
    if not in_force:
        raise RulesError(
            f"{game} draw {draw_no}: no rule set covers it; the earliest known version is "
            f"{versions[0].version} from draw {versions[0].first_draw}"
        )
    return in_force[-1]
