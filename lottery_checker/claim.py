"""Claim period (P3-06).

P0-03, settled 2026-10-18: prizes are claimable for 180 days from the draw
date. Not stated in the TOTO or 4D rules text; the Singapore Sweep rules
cl. 6.5 say the same, and Singapore Pools has stated it publicly.

Product rule, also from P0-03: show this as a hint only. NEVER hide, block or
zero a result once the period has passed — Singapore Pools has extended the
window by announcement before (an extra 90 days for draws 10 Oct 2019 to
5 Apr 2020), and only they can say whether a particular ticket is still good.
"""
from __future__ import annotations

from datetime import date, timedelta

CLAIM_DAYS = 180

OFFICIAL_CLAIM_URL = "https://www.singaporepools.com.sg/en/lottery/Pages/claim-prizes.aspx"


def claim_by(draw_date: date) -> date:
    """Last day of the ordinary 180-day claim period."""
    return draw_date + timedelta(days=CLAIM_DAYS)


def days_left(draw_date: date, today: date | None = None) -> int:
    """Days remaining in the ordinary claim period. Negative once it has passed."""
    return (claim_by(draw_date) - (today or date.today())).days


def claim_hint(draw_date: date, today: date | None = None) -> str:
    """One line for the reveal screen. Never says a ticket is void."""
    n = days_left(draw_date, today)
    d = claim_by(draw_date)
    by = f"{d.day} {d:%b %Y}"          # platform-independent; %-d is not portable
    if n > 1:
        return f"Claim by {by} ({n} days left)."
    if n == 1:
        return f"Claim by {by} (1 day left)."
    if n == 0:
        return f"Claim by {by} (today is the last day)."
    return (f"The usual 180-day claim period ended on {by}. "
            "Singapore Pools has extended it before, so check with them.")
