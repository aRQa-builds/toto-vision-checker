"""P5-01 descriptive draw statistics for the owner view. Counts only: no
ranking, no prediction. Built from captured draws (data/draws), never from
crowd results."""
from __future__ import annotations

import json
from pathlib import Path

MIN_DRAWS = 30
NOTE = "Each draw is independent. Past draws do not predict the next."


def _sorted(draws: list) -> list:
    return sorted(draws, key=lambda d: d.get("draw_no", 0))


def toto_stats(draws: list) -> dict:
    ordered = _sorted(draws)
    n = len(ordered)
    drawn = {k: 0 for k in range(1, 50)}
    additional = {k: 0 for k in range(1, 50)}
    last_seen = {}
    for idx, d in enumerate(ordered):
        for k in d.get("winning", []):
            if k in drawn:
                drawn[k] += 1
                last_seen[k] = idx
        a = d.get("additional")
        if a in additional:
            additional[a] += 1
    numbers = [
        {
            "number": k,
            "drawn": drawn[k],
            "additional": additional[k],
            "expected": n * 6 / 49,
            "since": (n - 1 - last_seen[k]) if k in last_seen else None,
        }
        for k in range(1, 50)
    ]
    return {"game": "toto", "draws": n, "enough": n >= MIN_DRAWS, "note": NOTE, "numbers": numbers}


def fourd_stats(draws: list) -> dict:
    ordered = _sorted(draws)
    n = len(ordered)
    first_digits = [[0] * 10 for _ in range(4)]
    distinct = set()
    for d in ordered:
        first = d.get("first")
        if isinstance(first, str) and len(first) == 4 and first.isdigit():
            for p, ch in enumerate(first):
                first_digits[p][int(ch)] += 1
        for key in ("first", "second", "third"):
            v = d.get(key)
            if isinstance(v, str) and len(v) == 4:
                distinct.add(v)
        for key in ("starter", "consolation"):
            for v in d.get(key) or []:
                if isinstance(v, str) and len(v) == 4:
                    distinct.add(v)
    return {
        "game": "4d",
        "draws": n,
        "enough": n >= MIN_DRAWS,
        "note": NOTE,
        "first_digits": first_digits,
        "expected_per_digit": n / 10,
        "distinct_numbers": len(distinct),
    }


def _load_draws(folder: Path) -> list:
    draws = []
    if not folder.is_dir():
        return draws
    for f in folder.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(data, dict):
            draws.append(data)
    return draws


def all_stats(data_dir) -> dict:
    base = Path(data_dir) / "draws"
    return {
        "toto": toto_stats(_load_draws(base / "toto")),
        "4d": fourd_stats(_load_draws(base / "4d")),
        "note": NOTE,
    }


STATS_MODULE_END = True
