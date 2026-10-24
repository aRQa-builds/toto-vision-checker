"""Ticket result aggregator (P3-05) — the seam between the parser and the UI.

The matchers grade one entry against one draw. Everything above them needs the
whole ticket: what each line did, what it cost, what it paid, what is still
pending, and by when it must be claimed. Without this, each caller (the reveal
screen, the history list, the wallet alerts) re-invents the roll-up and they
drift apart. This is the one place that roll-up lives.

Input is deliberately game-agnostic: a list of entries (TOTO or 4D, mixed is
allowed on separate tickets but not on one) and a list of DrawRef, each pairing
a draw with its date. parse.py results convert with DrawRef.from_parsed();
hand-entered results (P4-11) build one directly.

Money is in whole dollars for 4D and float dollars for TOTO, matching the
matchers. The UI formats; this module does not.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional, Sequence, Union

from . import fourd, toto
from .claim import claim_by, claim_hint, days_left

Entry = Union[toto.TotoEntry, fourd.FourDEntry]
Draw = Union[toto.TotoDraw, fourd.FourDDraw]


class TicketError(ValueError):
    """The ticket and the draws cannot be checked together."""


@dataclass(frozen=True)
class DrawRef:
    """A draw plus the date it was drawn (the matchers do not carry dates)."""

    draw: Draw
    draw_date: date

    @classmethod
    def from_parsed(cls, parsed) -> "DrawRef":
        """Build from a parse.py TotoResult or FourDResult."""
        return cls(parsed.draw, parsed.draw_date)

    @property
    def game(self) -> str:
        return "toto" if isinstance(self.draw, toto.TotoDraw) else "4d"


@dataclass
class Line:
    """One entry against one draw, as the reveal screen shows it."""

    game: str
    draw_no: int
    draw_date: date
    label: str                      # "Ordinary", "System 7", "iBet", "4D Roll"
    numbers: str                    # as printed on the ticket
    stake: float
    won: Optional[float]            # None if any winning group has no published amount
    detail: list[str] = field(default_factory=list)   # human-readable hit lines
    unpriced_groups: tuple[int, ...] = ()

    @property
    def pending(self) -> bool:
        return self.won is None


@dataclass
class TicketResult:
    """The whole ticket across every draw it covers."""

    lines: list[Line]
    total_stake: float
    total_won: Optional[float]      # None if ANY line is pending — never silently 0
    draw_dates: tuple[date, ...]

    @property
    def pending(self) -> bool:
        return self.total_won is None

    @property
    def pending_groups(self) -> tuple[int, ...]:
        out: set[int] = set()
        for ln in self.lines:
            out.update(ln.unpriced_groups)
        return tuple(sorted(out))

    @property
    def won_anything(self) -> bool:
        return self.pending or (self.total_won or 0) > 0

    @property
    def net(self) -> Optional[float]:
        return None if self.total_won is None else self.total_won - self.total_stake

    # --- claim period (P3-06), computed from the EARLIEST draw on the ticket,
    # --- because that is the one whose window closes first.
    @property
    def earliest_draw_date(self) -> date:
        return min(self.draw_dates)

    def claim_by(self) -> date:
        return claim_by(self.earliest_draw_date)

    def claim_days_left(self, today: Optional[date] = None) -> int:
        return days_left(self.earliest_draw_date, today)

    def claim_hint(self, today: Optional[date] = None) -> str:
        return claim_hint(self.earliest_draw_date, today)


_TOTO_GROUP = {1: "Group 1", 2: "Group 2", 3: "Group 3", 4: "Group 4",
               5: "Group 5", 6: "Group 6", 7: "Group 7"}


def _toto_line(entry: toto.TotoEntry, ref: DrawRef) -> Line:
    r = toto.check_entry(entry, ref.draw)
    detail = []
    for g, n in sorted(r.shares.items()):
        amt = ref.draw.prize_for(g)
        shown = "not yet published" if amt is None else f"{amt:,.2f}"
        detail.append(f"{_TOTO_GROUP[g]}: {n} x {shown}")
    return Line(
        game="toto", draw_no=ref.draw.draw_no, draw_date=ref.draw_date,
        label=entry.label, numbers=" ".join(str(n) for n in entry.numbers),
        stake=float(entry.stake), won=r.amount, detail=detail,
        unpriced_groups=r.unpriced_groups,
    )


def _fourd_line(entry: fourd.FourDEntry, ref: DrawRef) -> Line:
    r = fourd.check_entry(entry, ref.draw)
    label = {"ordinary": "Ordinary", "roll": "4D Roll",
             "system": f"System ({entry.perms} perms)", "ibet": "iBet"}[entry.kind]
    detail = [f"{h.number} {h.category} ({h.bet}): {h.amount:,}" for h in r.hits]
    return Line(
        game="4d", draw_no=ref.draw.draw_no, draw_date=ref.draw_date,
        label=label, numbers=entry.number,
        stake=float(entry.cost_per_draw), won=float(r.amount), detail=detail,
    )


def check_ticket(entries: Sequence[Entry], draws: Iterable[DrawRef]) -> TicketResult:
    """Grade every entry against every draw the ticket covers.

    Raises TicketError on an empty ticket, no draws, or a game mismatch —
    pricing a 4D bet against a TOTO draw is a bug, never a zero result.
    """
    entries = list(entries)
    refs = list(draws)
    if not entries:
        raise TicketError("ticket has no entries")
    if not refs:
        raise TicketError("no draws to check against")

    games = {("toto" if isinstance(e, toto.TotoEntry) else "4d") for e in entries}
    if len(games) > 1:
        raise TicketError(f"one ticket cannot mix games: {sorted(games)}")
    game = games.pop()
    wrong = [r.draw.draw_no for r in refs if r.game != game]
    if wrong:
        raise TicketError(f"{game} ticket checked against non-{game} draw(s) {wrong}")

    lines = [
        _toto_line(e, r) if game == "toto" else _fourd_line(e, r)
        for r in refs for e in entries
    ]
    total_stake = sum(ln.stake for ln in lines)
    total_won = (None if any(ln.pending for ln in lines)
                 else sum(ln.won or 0 for ln in lines))
    return TicketResult(lines, total_stake, total_won,
                        tuple(r.draw_date for r in refs))
