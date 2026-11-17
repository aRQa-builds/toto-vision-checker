"""Group TOTO and iTOTO unit tickets (P6-15, cl. 2.6): the holder's share.

Group TOTO prints `UNIT NUMBER: k/n`: the entry is split into n equal units and
the prize is split equally across them, so every holder gets 1/n whatever k is.
iTOTO prints `NUMBER OF UNITS PURCHASED: u of N`: the prize is split by all N
units, sold and unsold, and the buyer gets u/N.

Amounts are plain floats, never rounded here; display goes through reveal.money().
A win of None (amount not published yet) stays None, never 0.
"""
from typing import Optional


def unit_share(win: Optional[float], kind: str, a: int, b: int) -> Optional[float]:
    raise NotImplementedError


def unit_stake(whole_stake: float, kind: str, a: int, b: int) -> float:
    raise NotImplementedError


UNIT_KINDS = ("group", "itoto")
