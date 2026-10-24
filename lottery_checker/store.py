"""Read captured draws back from data/draws/<game>/<n>.json (written by ingest.py).

A stored record becomes the same DrawRef the checker uses for typed and
screenshot results, priced from the draw's own rule set. Group amounts with
no winners are stored as null and stay unpriced. A record that does not load
cleanly is treated as not on file, so the user is sent to the official page
instead of being shown a result built from a bad file.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from . import fourd, toto
from .rules import RulesError, rules_for
from .ticket import DrawRef

GAMES = ("toto", "4d")


def record_path(game: str, draw_no: int, data_dir: Path) -> Path:
    if game not in GAMES:
        raise ValueError(f"unknown game {game!r}")
    return Path(data_dir) / "draws" / game / f"{int(draw_no)}.json"


def load_record(game: str, draw_no: int, data_dir: Path) -> Optional[dict]:
    p = record_path(game, draw_no, data_dir)
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rec if rec.get("game") == game and rec.get("draw_no") == int(draw_no) else None


def to_ref(rec: dict) -> DrawRef:
    game, n = rec["game"], int(rec["draw_no"])
    when = date.fromisoformat(rec["draw_date"])
    rules = rules_for(game, n)
    if game == "toto":
        prizes = {int(g): float(v["amount"]) for g, v in rec.get("shares", {}).items()
                  if v.get("amount") is not None}
        draw = toto.TotoDraw(n, tuple(rec["winning"]), int(rec["additional"]), prizes, rules)
    else:
        draw = fourd.FourDDraw(n, rec["first"], rec["second"], rec["third"],
                               tuple(rec["starter"]), tuple(rec["consolation"]), rules)
    return DrawRef(draw, when)


def load_ref(game: str, draw_no: int, data_dir: Path) -> Optional[DrawRef]:
    rec = load_record(game, draw_no, data_dir)
    if rec is None:
        return None
    try:
        return to_ref(rec)
    except (KeyError, TypeError, ValueError, RulesError, toto.TotoError, fourd.FourDError):
        return None
