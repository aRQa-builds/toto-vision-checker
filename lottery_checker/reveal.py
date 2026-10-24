"""Reveal-screen rules (P4-12): what the result screen is allowed to say.

check_ticket() (P3-05) gives the numbers. This module turns them into the
words and flags the reveal screen shows, so every screen (web reveal, history,
wallet alert) says the same thing in the same cases. The UI only lays it out.

Rules, from the 18 Oct 2026 simulation and the 21 Oct ticket specimens:

1. A won group whose amount is not yet published is PENDING, never S$0.
   The headline names the pending groups. If other lines are already priced,
   it says "at least S$X so far", never a bare total.
2. Claim-by date (P3-06) is shown whenever anything was won or is pending,
   using the earliest draw on the ticket. Never "void" or "expired".
3. Our computed stake is checked against the PRICE: line every ticket prints
   (whole ticket, all draws). A mismatch means we probably misread a bet,
   a sold-out side (S'OUT) or a reduced stake (*), so the result is flagged
   for review and the screen sends the user back to confirm-and-correct (P3-03).
   We still show the result: hiding it would be worse than flagging it.
4. Every draw links to its official result page, and the attribution line is
   always present. The official result is final.

Money: whole amounts print without cents (S$4,000), others with (S$1,566.50).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .ingest import ATTRIBUTION, official_url
from .ticket import Line, TicketResult

CENT = 0.005   # tolerance for comparing dollar amounts held as floats


def money(v: float) -> str:
    """S$ with thousands separators; cents only when there are any."""
    if abs(v - round(v)) < CENT:
        return f"S${round(v):,}"
    return f"S${v:,.2f}"


def _groups(gs) -> str:
    gs = list(gs)
    names = [f"Group {g}" for g in gs]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


@dataclass
class LineView:
    draw_no: int
    label: str
    numbers: str
    stake_text: str
    result_text: str            # "S$4,000", "No win", "Group 2: amount not yet published"
    detail: list[str]
    pending: bool
    won: bool


@dataclass
class StakeCheck:
    state: str                  # "match" | "mismatch" | "not_checked"
    computed: float
    printed: Optional[float]
    message: str


@dataclass
class Reveal:
    state: str                  # "won" | "pending" | "no_win"
    headline: str
    subline: str
    lines: list[LineView]
    stake: StakeCheck
    claim_text: Optional[str]   # None when nothing was won
    needs_review: bool          # True sends the user back to confirm-and-correct
    official_links: list[tuple[int, str]] = field(default_factory=list)
    attribution: str = ATTRIBUTION


def _line_view(ln: Line) -> LineView:
    if ln.pending:
        priced_part = [d for d in ln.detail if "not yet published" not in d]
        n = len(ln.unpriced_groups)
        text = f"{_groups(ln.unpriced_groups)}: amount{'s' if n > 1 else ''} not yet published"
        if priced_part:
            text += " (other prizes on this line shown below)"
        won = True
    elif (ln.won or 0) > CENT:
        text, won = money(ln.won), True
    else:
        text, won = "No win", False
    return LineView(ln.draw_no, ln.label, ln.numbers, money(ln.stake),
                    text, list(ln.detail), ln.pending, won)


def stake_check(result: TicketResult, printed_price: Optional[float]) -> StakeCheck:
    computed = result.total_stake
    if printed_price is None:
        return StakeCheck("not_checked", computed, None,
                          f"We count {money(computed)} staked. "
                          "We could not read the ticket's PRICE line to check it.")
    if abs(printed_price - computed) < CENT:
        return StakeCheck("match", computed, printed_price,
                          f"Stake {money(computed)} matches the ticket.")
    return StakeCheck("mismatch", computed, printed_price,
                      f"The ticket says {money(printed_price)} but we count {money(computed)}. "
                      "A bet may have been misread, or part of it sold out (S'OUT) "
                      "or accepted at a lower stake (*). Please check the bets.")


def build_reveal(result: TicketResult, printed_price: Optional[float] = None,
                 today: Optional[date] = None, results_source: str = "official") -> Reveal:
    """results_source: "official" (captured from the official page), "user"
    (typed in, or read from the user's own screenshot and confirmed, P4-11) or
    "shared" (two other users' screenshots agreed, P3-07)."""
    if results_source not in ("official", "user", "shared"):
        raise ValueError(f"results_source must be 'official', 'user' or 'shared', got {results_source!r}")
    lines = [_line_view(ln) for ln in result.lines]
    stake = stake_check(result, printed_price)

    if result.pending:
        known = sum(ln.won or 0 for ln in result.lines if not ln.pending)
        groups = _groups(result.pending_groups)
        prize = (f"a {groups} prize" if len(result.pending_groups) == 1
                 else f"{groups} prizes")
        amount = ("amount is" if len(result.pending_groups) == 1 else "amounts are")
        state = "pending"
        if known > CENT:
            headline = f"At least {money(known)} so far"
            subline = (f"Plus {prize} whose {amount} not yet published. "
                       "Check back after Singapore Pools publishes it.")
        else:
            headline = f"You won {prize}"
            subline = (f"The {amount} not yet published. "
                       "Check back after Singapore Pools publishes it.")
    elif (result.total_won or 0) > CENT:
        state = "won"
        headline = f"You won {money(result.total_won)}"
        subline = f"Staked {money(result.total_stake)} across {len(result.draw_dates)} draw" + (
            "s" if len(result.draw_dates) != 1 else "")
    else:
        state = "no_win"
        headline = "No win this time"
        subline = f"Staked {money(result.total_stake)}."

    claim = result.claim_hint(today) if state != "no_win" else None

    seen, links = set(), []
    for ln in result.lines:
        if ln.draw_no not in seen:
            seen.add(ln.draw_no)
            links.append((ln.draw_no, official_url(ln.game, ln.draw_no)))

    rv = Reveal(state, headline, subline, lines, stake, claim,
                needs_review=stake.state == "mismatch", official_links=links)
    if results_source == "user":
        _as_user_entered(rv, result)
    elif results_source == "shared":
        rv.attribution = SHARED_ATTRIBUTION
    return rv


# P4-11: results typed in by the user. A missing Group 1-4 amount means they
# did not enter it, not that Singapore Pools has not published it, and the
# numbers are theirs, so the attribution must not claim them as official.
# P3-07: results two users' screenshots agreed on. Not captured by us, so not
# called official; a missing Group 1-4 amount means not enough people agreed on it yet.
SHARED_ATTRIBUTION = (
    "Results read from screenshots of the official page by other users (two agreed). "
    "Check them against the official result published by Singapore Pools, which is final."
)

USER_ATTRIBUTION = (
    "Results as entered by you. Check them against the official result "
    "published by Singapore Pools, which is final."
)


def _as_user_entered(rv: Reveal, result: TicketResult) -> None:
    rv.attribution = USER_ATTRIBUTION
    if rv.state != "pending":
        return
    n = len(result.pending_groups)
    groups = _groups(result.pending_groups)
    amount = "amount" if n == 1 else "amounts"
    rv.subline = (("Plus " + (f"a {groups} prize. " if n == 1 else f"{groups} prizes. "))
                  if rv.headline.startswith("At least") else "")
    rv.subline += f"Add the {groups} {amount} from the official result to see your total."
    for lv in rv.lines:
        lv.result_text = lv.result_text.replace("not yet published", "not entered")
        lv.detail = [d.replace("not yet published", "not entered") for d in lv.detail]
