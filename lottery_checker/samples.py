"""Sample tickets for the testing phase (23 Oct 2026, owner's request).

While bugs are being hunted, a sample ticket is more useful if its draw is one the
results database still lacks: checking it makes the tester add that draw's official
screenshot, so the crowd database fills while the page is being tested.

Tickets are typed text (the short "draw N" form), with random numbers and a PRICE
that matches the bets. Nothing here is a real ticket and nothing is stored.
Only offered while a testing phase is on (api.py).
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from . import results_db
from .ticket_entry import parse_ticket

KINDS = ("toto", "4d", "five")


def _empty_draws(game: str, data_dir: Path) -> list[int]:
    """Draw numbers this year with nothing on file, or only one person's screenshot
    (a second agreeing one makes it usable), newest first."""
    try:
        w = results_db.wanted(game, data_dir)
        return [x["draw_no"] for x in w["wanted"]] or [w["to"]]
    except Exception:                                    # a sample must never fail the page
        return [results_db.latest_drawn(game)]


def _pick(pool: list[int], rng: random.Random, used: set[int], run: int = 1) -> list[int]:
    """`run` consecutive draw numbers from the pool where there are that many, else
    whatever is available; avoids draws already used by another sample ticket."""
    free = [n for n in pool if n not in used] or pool
    n = rng.choice(free)
    out = [n]
    while len(out) < run and out[-1] + 1 in pool and out[-1] + 1 not in used:
        out.append(out[-1] + 1)
    used.update(out)
    return out


def _toto(rng: random.Random, draws: list[int], system: bool) -> str:
    size = 7 if system else 6
    lines = ["TOTO", f"SYSTEM {size}" if system else "ORDINARY"]
    boards = 1 if system else rng.choice((1, 2, 3))
    for i in range(boards):
        nums = sorted(rng.sample(range(1, 50), size))
        lines.append(f"{'ABC'[i]}. " + " ".join(f"{n:02d}" for n in nums) + ("" if system else " QP"))
    price = (7 if system else boards) * len(draws)
    lines += [f"PRICE: ${price}.00", "draw " + " ".join(str(n) for n in draws)]
    return "\n".join(lines)


def _fourd(rng: random.Random, draws: list[int]) -> str:
    lines = ["4D", "ORDINARY"]
    per_draw = 0
    for i in range(rng.choice((1, 2, 3))):
        big, small = rng.choice(((1, 0), (2, 0), (1, 1), (0, 1)))
        num = f"{rng.randrange(10000):04d}"
        parts = [f"{'ABC'[i]} {num}"]
        if big:
            parts.append(f"BIG ${big}")
        if small:
            parts.append(f"SML ${small}")
        per_draw += big + small
        lines.append(" ".join(parts))
    lines += [f"PRICE: ${per_draw * len(draws)}.00", "draw " + " ".join(str(n) for n in draws)]
    return "\n".join(lines)


def make(kind: str, data_dir: Path, rng: Optional[random.Random] = None) -> list[dict]:
    """One ('toto', '4d') or five ('five') sample tickets, as
    {game, label, text, draws}. Five = two TOTO (one System 7, one over 2-4 draws),
    two 4D (one over 2-3 draws) and one more of either game."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    rng = rng or random.Random()
    pool = {g: _empty_draws(g, data_dir) for g in ("toto", "4d")}
    used: dict[str, set[int]] = {"toto": set(), "4d": set()}
    plan = {"toto": [("toto", 1, False)], "4d": [("4d", 1, False)],
            "five": [("toto", 1, True), ("toto", rng.choice((2, 3, 4)), False),
                     ("4d", 1, False), ("4d", rng.choice((2, 3)), False),
                     (rng.choice(("toto", "4d")), 1, False)]}[kind]
    out = []
    for game, run, system in plan:
        draws = _pick(pool[game], rng, used[game], run)
        text = _toto(rng, draws, system) if game == "toto" else _fourd(rng, draws)
        label = f"{'TOTO' if game == 'toto' else '4D'} sample · draw{'s' if len(draws) > 1 else ''} " \
                + ", ".join(str(n) for n in draws)
        out.append({"game": game, "label": label, "text": text, "draws": draws})
    return out
