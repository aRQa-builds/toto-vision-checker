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
    if kind not in ("group", "itoto"):
        raise ValueError(f"Invalid kind: {kind}")
    if b < 1:
        raise ValueError("b must be at least 1")
    if a < 1 or a > b:
        raise ValueError("a must be between 1 and b inclusive")

    if win is None:
        return None

    if kind == "group":
        return win / b
    else:  # itoto
        return win * a / b


def unit_stake(whole_stake: float, kind: str, a: int, b: int) -> float:
    if kind not in ("group", "itoto"):
        raise ValueError(f"Invalid kind: {kind}")
    if b < 1:
        raise ValueError("b must be at least 1")
    if a < 1 or a > b:
        raise ValueError("a must be between 1 and b inclusive")

    if kind == "group":
        return whole_stake / b
    else:  # itoto
        return whole_stake * a / b


UNIT_KINDS = ("group", "itoto")
