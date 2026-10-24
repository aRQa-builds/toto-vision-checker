"""TOTO matcher and payout.

Rules: TOTO Game Rules w.e.f. 2 Mar 2026 (Draw 4161/2026).
- Six winning numbers from 1-49 plus one Additional Number (cl. 2.1).
- Every set of six on a ticket is graded on its own and wins at most one
  prize, the highest it qualifies for (cl. 5.8, 5.9).
- The Additional Number never counts toward the match count (cl. 2.2).
- Groups 1-4 are pool-based: the per-share amount is a per-draw published
  value. Groups 5-7 are fixed ($50 / $25 / $10) (cl. 5.5).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable, Mapping, Optional

from .rules import TotoRules, rules_for

NUM_MIN, NUM_MAX = 1, 49

# Defaults for entry validation and stakes: the latest rule set (P2-01). A draw
# carries its own rule set, which is what prices it.
_LATEST = rules_for("toto")

# Fixed prizes per winning combination, cl. 5.5. Groups 1-4 have no fixed value.
FIXED_PRIZES = _LATEST.fixed_prizes

# Sets and stake per entry type, cl. 3.5. Ordinary is 1 set, $1.
SYSTEM_SIZES = _LATEST.system_sizes
ROLL_SETS = _LATEST.roll_sets


class TotoError(ValueError):
    """Invalid draw or entry."""


def _check_numbers(nums: Iterable[int], what: str) -> tuple[int, ...]:
    nums = tuple(nums)
    if len(set(nums)) != len(nums):
        raise TotoError(f"{what}: duplicate numbers {nums}")
    for n in nums:
        if not isinstance(n, int) or not NUM_MIN <= n <= NUM_MAX:
            raise TotoError(f"{what}: {n!r} is outside 1-49")
    return tuple(sorted(nums))


@dataclass(frozen=True)
class TotoDraw:
    """One TOTO draw result.

    group_prizes holds the published per-share (Groups 1-4) or per-combination
    (Groups 5-7) amounts for this draw. Groups 1-4 must come from the official
    result because they depend on the pool, snowball and cascade. Groups 5-7
    default to the fixed amounts of the draw's own rule set, but a published
    value overrides them.

    rules: the rule set in force for this draw (P2-01). Left out, it defaults
    to the latest version, which suits hand-built draws in tests and the UI.
    Anything carrying a real draw number — the parser, the capture, stored
    records — passes rules_for("toto", draw_no), so a draw older than any
    known rule set raises RulesError instead of being priced from today's.
    """

    draw_no: int
    winning: tuple[int, ...]
    additional: int
    group_prizes: Mapping[int, float] = field(default_factory=dict)
    rules: Optional[TotoRules] = None

    def __post_init__(self):
        win = _check_numbers(self.winning, f"draw {self.draw_no} winning")
        if len(win) != 6:
            raise TotoError(f"draw {self.draw_no}: need 6 winning numbers, got {len(win)}")
        _check_numbers([self.additional], f"draw {self.draw_no} additional")
        if self.additional in win:
            raise TotoError(f"draw {self.draw_no}: additional {self.additional} repeats a winning number")
        object.__setattr__(self, "winning", win)
        if self.rules is None:
            object.__setattr__(self, "rules", rules_for("toto"))

    def prize_for(self, group: int) -> Optional[float]:
        if group in self.group_prizes:
            return self.group_prizes[group]
        return self.rules.fixed_prizes.get(group)


@dataclass(frozen=True)
class TotoEntry:
    """One TOTO entry (board) on a ticket.

    kind: "ordinary" (6 numbers), "system" (7-12 numbers) or "roll" (5 numbers).
    """

    kind: str
    numbers: tuple[int, ...]

    def __post_init__(self):
        nums = _check_numbers(self.numbers, f"{self.kind} entry")
        object.__setattr__(self, "numbers", nums)
        n = len(nums)
        if self.kind == "ordinary" and n != 6:
            raise TotoError(f"ordinary entry needs 6 numbers, got {n}")
        if self.kind == "system" and n not in SYSTEM_SIZES:
            raise TotoError(f"system entry needs 7-12 numbers, got {n}")
        if self.kind == "roll" and n != 5:
            raise TotoError(f"system roll entry needs 5 numbers, got {n}")
        if self.kind not in ("ordinary", "system", "roll"):
            raise TotoError(f"unknown entry kind {self.kind!r}")

    @property
    def label(self) -> str:
        if self.kind == "system":
            return f"System {len(self.numbers)}"
        return "System Roll" if self.kind == "roll" else "Ordinary"

    @property
    def stake(self) -> int:
        """Stake in S$ per draw, cl. 3.4-3.5."""
        if self.kind == "ordinary":
            return 1
        if self.kind == "roll":
            return ROLL_SETS
        return SYSTEM_SIZES[len(self.numbers)]

    def sets(self) -> Iterable[tuple[int, ...]]:
        """Every set of six this entry covers."""
        if self.kind == "ordinary":
            yield self.numbers
        elif self.kind == "system":
            yield from combinations(self.numbers, 6)
        else:  # roll: the 5 numbers plus each of the other 44
            for r in range(NUM_MIN, NUM_MAX + 1):
                if r not in self.numbers:
                    yield tuple(sorted(self.numbers + (r,)))


def grade_set(six: Iterable[int], draw: TotoDraw) -> Optional[int]:
    """Prize group (1-7) for one set of six, or None. cl. 5.5, 5.9."""
    six = set(six)
    hits = len(six & set(draw.winning))
    add = draw.additional in six
    if hits == 6:
        return 1
    if hits == 5:
        return 2 if add else 3
    if hits == 4:
        return 4 if add else 5
    if hits == 3:
        return 6 if add else 7
    return None


def winning_shares(entry: TotoEntry, draw: TotoDraw) -> Counter:
    """Count of winning shares/combinations per group for one entry, cl. 5.14-5.16."""
    out: Counter = Counter()
    for six in entry.sets():
        g = grade_set(six, draw)
        if g:
            out[g] += 1
    return out


@dataclass
class TotoResult:
    draw_no: int
    entry: TotoEntry
    shares: Counter
    amount: Optional[float]          # None if any winning group's amount is not yet published
    unpriced_groups: tuple[int, ...]  # groups won but with no published amount


def check_entry(entry: TotoEntry, draw: TotoDraw) -> TotoResult:
    shares = winning_shares(entry, draw)
    total = 0.0
    missing = []
    for g, n in sorted(shares.items()):
        p = draw.prize_for(g)
        if p is None:
            missing.append(g)
        else:
            total += p * n
    return TotoResult(draw.draw_no, entry, shares, None if missing else total, tuple(missing))


def check_ticket(entries: Iterable[TotoEntry], draws: Iterable[TotoDraw]) -> list[TotoResult]:
    """Multi-draw: check every entry against every draw the ticket covers."""
    entries = list(entries)
    return [check_entry(e, d) for d in draws for e in entries]
