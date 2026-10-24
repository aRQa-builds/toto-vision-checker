"""4D matcher and payout.

Rules: 4D Game Rules dated 30 Dec 2024 (Draw 5269/2024), plus the Singapore
Pools bet slip guide for stake treatment (read 17 Oct 2026).
- A draw has 1 first, 1 second, 1 third, 10 starter and 10 consolation numbers.
- Big wins on all five categories; Small wins on first, second and third only.
- A number with more than one winning match gets all those prizes (rule 4.6).
- Stake per draw: Ordinary = amount marked; Roll = amount x 10;
  System = amount x permutations; iBet = amount marked once.

PRIZE TABLES ARE COPIED FROM THE RULES (per $1). Re-check them against the
live rules before release; never derive iBet amounts by division.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
from typing import Iterable, Optional

from .rules import FourDRules, rules_for

CATEGORIES = ("first", "second", "third", "starter", "consolation")
SMALL_CATEGORIES = ("first", "second", "third")

# The prize tables now live in rules.py, one set per rule version (P2-01).
# These two names are the latest version's tables, kept for callers that just
# want "the current amounts"; a draw is always priced from its own rule set.
_LATEST = rules_for("4d")
ORDINARY_PRIZES = _LATEST.ordinary_prizes
IBET_PRIZES = _LATEST.ibet_prizes

KINDS = ("ordinary", "roll", "system", "ibet")


class FourDError(ValueError):
    """Invalid draw or entry."""


def _digits(s: str, what: str) -> str:
    s = str(s).strip()
    if len(s) != 4 or not s.isdigit():
        raise FourDError(f"{what}: {s!r} is not a 4-digit number")
    return s


def permutation_count(number: str) -> int:
    return len(set(permutations(number)))


@dataclass(frozen=True)
class FourDDraw:
    """One 4D draw result.

    rules: the rule set in force for this draw (P2-01). Left out, it defaults
    to the latest version; the parser and the capture pass
    rules_for("4d", draw_no) so a draw older than any known rule set raises
    RulesError instead of being priced from today's tables.
    """

    draw_no: int
    first: str
    second: str
    third: str
    starter: tuple[str, ...]
    consolation: tuple[str, ...]
    rules: Optional[FourDRules] = None

    def __post_init__(self):
        if self.rules is None:
            object.__setattr__(self, "rules", rules_for("4d"))
        for name in ("first", "second", "third"):
            object.__setattr__(self, name, _digits(getattr(self, name), f"draw {self.draw_no} {name}"))
        for name in ("starter", "consolation"):
            nums = tuple(_digits(n, f"draw {self.draw_no} {name}") for n in getattr(self, name))
            if len(nums) != 10:
                raise FourDError(f"draw {self.draw_no}: need 10 {name} numbers, got {len(nums)}")
            object.__setattr__(self, name, nums)

    def positions(self, number: str) -> list[str]:
        """Every winning category this number appears in (can be more than one)."""
        out = [c for c in ("first", "second", "third") if getattr(self, c) == number]
        out += ["starter"] * self.starter.count(number)
        out += ["consolation"] * self.consolation.count(number)
        return out


@dataclass(frozen=True)
class FourDEntry:
    """One 4D bet.

    number: 4 digits; for Roll, exactly one position is 'R' (e.g. "58R2").
    big / small: whole-dollar amount marked per number (per draw).
    """

    kind: str
    number: str
    big: int = 0
    small: int = 0

    def __post_init__(self):
        if self.kind not in KINDS:
            raise FourDError(f"unknown entry kind {self.kind!r}")
        for name in ("big", "small"):
            v = getattr(self, name)
            if not isinstance(v, int) or v < 0:
                raise FourDError(f"{name} stake must be a whole dollar amount, got {v!r}")
        if self.big + self.small < 1:
            raise FourDError("stake must be at least $1 (rule 3.1)")
        num = str(self.number).strip().upper().replace("X", "R")
        if self.kind == "roll":
            if len(num) != 4 or num.count("R") != 1 or not num.replace("R", "").isdigit():
                raise FourDError(f"roll entry needs 3 digits and one R, got {self.number!r}")
        else:
            num = _digits(num, f"{self.kind} entry")
            if self.kind in ("system", "ibet") and permutation_count(num) == 1:
                raise FourDError(f"{num} has one permutation; not allowed as {self.kind}")
        object.__setattr__(self, "number", num)

    @property
    def perms(self) -> int:
        return permutation_count(self.number) if self.kind in ("system", "ibet") else 1

    def covered(self) -> list[str]:
        """Every 4-digit number this bet covers."""
        if self.kind == "ordinary":
            return [self.number]
        if self.kind == "roll":
            return [self.number.replace("R", str(d)) for d in range(10)]
        return sorted({"".join(p) for p in permutations(self.number)})

    @property
    def cost_per_draw(self) -> int:
        """S$ per draw, per the Singapore Pools bet slip guide."""
        base = self.big + self.small
        if self.kind == "roll":
            return base * 10
        if self.kind == "system":
            return base * self.perms
        return base  # ordinary and ibet


@dataclass(frozen=True)
class FourDHit:
    number: str
    category: str
    bet: str        # "big" or "small"
    amount: int


@dataclass
class FourDResult:
    draw_no: int
    entry: FourDEntry
    hits: list[FourDHit] = field(default_factory=list)

    @property
    def amount(self) -> int:
        return sum(h.amount for h in self.hits)


def check_entry(entry: FourDEntry, draw: FourDDraw) -> FourDResult:
    res = FourDResult(draw.draw_no, entry)
    rules = draw.rules                      # price from this draw's own rule set (P2-01)
    for num in entry.covered():
        for cat in draw.positions(num):
            for bet, stake in (("big", entry.big), ("small", entry.small)):
                if not stake:
                    continue
                if entry.kind == "ibet":
                    table = rules.ibet_prizes[bet].get(cat)
                    per_dollar = table[entry.perms] if table else None
                else:
                    per_dollar = rules.ordinary_prizes[bet].get(cat)
                if per_dollar:
                    res.hits.append(FourDHit(num, cat, bet, per_dollar * stake))
    return res


def check_ticket(entries: Iterable[FourDEntry], draws: Iterable[FourDDraw]) -> list[FourDResult]:
    """Multi-draw: check every entry against every draw the ticket covers."""
    entries = list(entries)
    return [check_entry(e, d) for d in draws for e in entries]


def ticket_cost(entries: Iterable[FourDEntry], n_draws: int) -> int:
    """Total stake: per-draw cost x number of draw days (2021 rules example)."""
    return sum(e.cost_per_draw for e in entries) * n_draws
