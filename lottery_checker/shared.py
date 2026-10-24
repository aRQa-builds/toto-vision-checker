"""Shared results from users' screenshots (P3-07, decided by the owner 22 Oct 2026).

Problem: a draw the after-draw capture never stored (anything before it started,
19-21 Oct 2026) needs every user to screenshot the official page themselves.
This lets one user's screenshot help the next, safely:

- Only complete screenshot reads are counted, never typed numbers.
- A draw's numbers are shared only when screenshots from two different people
  read exactly the same, with the same draw date.
- Any conflict voids the draw for good (owner's rule, 22 Oct 10:38): if anyone's
  screenshot reads different numbers or a different date, nothing is shared for
  that draw, even if two people had agreed before. Everyone then adds their own
  screenshot, as if there were no shared data.
- Group 1-4 prize amounts each need two people agreeing and no one disagreeing;
  otherwise that group stays pending on the reveal. Groups 5-7 are fixed by the
  rules.
- A captured official result always wins: nothing is stored or served for a
  draw that has one.
- Draws from 1 January of last year onwards are kept (owner, 22 Oct 2026: the
  whole year's history is built from crowd screenshots, never by pulling the
  official site). Older draws are refused.
- Every entry records who (a salted one-way hash of the connection address,
  data/shared/.salt; the address itself is never stored), the source device
  (a short label such as "Android · Chrome", not the full browser string) and
  when (UTC).
- Served results say they come from other users' screenshots, never "official".
- Off switch: TOTO_SHARED_RESULTS=0 stops both storing and serving.

Files: data/shared/<game>/<draw>.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .store import GAMES, load_record, to_ref
from .ticket import DrawRef

AGREE = 2                 # different people who must read the same thing
MAX_ENTRIES = 50          # per candidate; plenty to show agreement or conflict
KEEP_YEARS = 1            # this year and last year
_lock = threading.Lock()


def enabled() -> bool:
    return os.environ.get("TOTO_SHARED_RESULTS", "1") != "0"


def _dir(data_dir: Path) -> Path:
    return Path(data_dir) / "shared"


def _path(game: str, draw_no: int, data_dir: Path) -> Path:
    if game not in GAMES:
        raise ValueError(f"unknown game {game!r}")
    return _dir(data_dir) / game / f"{int(draw_no)}.json"


def client_id(address: str, data_dir: Path) -> str:
    """Salted one-way hash of a connection address. The address is not kept."""
    salt_file = _dir(data_dir) / ".salt"
    with _lock:
        if not salt_file.is_file():
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.write_text(secrets.token_hex(32), encoding="utf-8")
        salt = salt_file.read_text(encoding="utf-8").strip()
    return hashlib.sha256((salt + "|" + address).encode("utf-8")).hexdigest()[:20]


def device_label(user_agent: Optional[str]) -> str:
    """'Android · Chrome', 'iPhone · Safari', 'Windows · Edge': enough to see where
    an entry came from, not enough to fingerprint anyone."""
    ua = user_agent or ""
    os_name = ("iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else
               "Android" if "Android" in ua else "Windows" if "Windows" in ua else
               "Mac" if "Macintosh" in ua else "Linux" if "Linux" in ua else "Unknown")
    browser = ("App" if "TotoCheckApp" in ua else "Samsung Internet" if "SamsungBrowser" in ua else "Edge" if re.search(r"Edg[A]?/", ua) else
               "Firefox" if re.search(r"Firefox|FxiOS", ua) else "Chrome" if re.search(r"Chrome|CriOS", ua) else
               "Safari" if "Safari" in ua else "Other")
    return f"{os_name} · {browser}"


def _numbers(read) -> Optional[dict]:
    if read.game == "toto":
        return {"winning": list(read.winning), "additional": read.additional}
    if read.game == "4d":
        return {"first": read.first, "second": read.second, "third": read.third,
                "starter": list(read.starter), "consolation": list(read.consolation)}
    return None


def _load(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _add(entries: list, entry: dict) -> None:
    if any(e["who"] == entry["who"] for e in entries) or len(entries) >= MAX_ENTRIES:
        return
    entries.append(entry)


def submit(read, client: str, data_dir: Path, today: Optional[date] = None,
           device: str = "Unknown") -> bool:
    """Count one complete screenshot read from one person. True if recorded."""
    if not enabled() or not read.complete or read.draw_no is None or read.draw_date is None:
        return False
    today = today or date.today()
    if not (date(today.year - KEEP_YEARS, 1, 1) <= read.draw_date <= today):
        return False
    if load_record(read.game, read.draw_no, data_dir) is not None:
        return False                                    # official capture exists
    nums = _numbers(read)
    if nums is None:
        return False
    entry = {"who": client, "device": device,
             "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    fp = json.dumps(nums, sort_keys=True)
    p = _path(read.game, read.draw_no, data_dir)
    with _lock:
        rec = _load(p) or {"game": read.game, "draw_no": read.draw_no,
                           "candidates": {}, "dates": {}, "amounts": {}}
        _add(rec["dates"].setdefault(read.draw_date.isoformat(), []), entry)
        _add(rec["candidates"].setdefault(fp, {"numbers": nums, "entries": []})["entries"], entry)
        if read.game == "toto":
            for g, amount in read.shares.items():
                if 1 <= g <= 4:
                    _add(rec["amounts"].setdefault(str(g), {}).setdefault(f"{amount:.2f}", []), entry)
        state = _state(rec)
        if state == "void" and not rec.get("void"):
            rec["void"] = {"at": entry["at"], "why": _void_reason(rec)}
        rec["state"] = state
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        tmp.replace(p)
    from .results_db import compile_quietly
    compile_quietly(data_dir)                           # keep data/results/ current
    return True


def _people(entries: list) -> int:
    return len({e["who"] for e in entries})


def _single_agreed(options: dict, get) -> Optional[str]:
    """The only option, if at least AGREE people back it. Any second option
    (a conflict) gives None."""
    if len(options) != 1:
        return None
    (key, val), = options.items()
    return key if _people(get(val)) >= AGREE else None


def _void_reason(rec: dict) -> str:
    if len(rec.get("candidates", {})) > 1:
        return "screenshots read different numbers"
    if len(rec.get("dates", {})) > 1:
        return "screenshots read different draw dates"
    return "the draw date read can't belong to this draw number"


def _state(rec: dict) -> str:
    """'void' (any conflict, or a date that can't belong to the draw), 'agreed'
    (two people, no conflict) or 'waiting'."""
    if rec.get("void") or len(rec.get("candidates", {})) > 1 or len(rec.get("dates", {})) > 1:
        return "void"
    from .results_screen import plausible_date
    for d in rec.get("dates", {}):
        if not plausible_date(rec.get("game"), rec.get("draw_no"), date.fromisoformat(d)):
            return "void"                               # e.g. the "Next Draw" date (bug fixed 22 Oct)
    if (_single_agreed(rec.get("candidates", {}), lambda c: c["entries"]) and
            _single_agreed(rec.get("dates", {}), lambda e: e)):
        return "agreed"
    return "waiting"


def status(game: str, draw_no: int, data_dir: Path) -> Optional[str]:
    """'agreed', 'void', 'waiting', or None (nothing shared for this draw, or switched off)."""
    if not enabled() or game not in GAMES:
        return None
    rec = _load(_path(game, draw_no, data_dir))
    if not rec or rec.get("game") != game or rec.get("draw_no") != int(draw_no):
        return None
    return _state(rec)


def load_shared_ref(game: str, draw_no: int, data_dir: Path) -> Optional[DrawRef]:
    """The agreed result for a draw, or None (not enough agreement, void,
    switched off, or a captured result exists and should be used instead)."""
    if status(game, draw_no, data_dir) != "agreed":
        return None
    rec = _load(_path(game, draw_no, data_dir))
    (fp, cand), = rec["candidates"].items()
    (when, _), = rec["dates"].items()
    out = {"game": game, "draw_no": int(draw_no), "draw_date": when, **cand["numbers"]}
    if game == "toto":
        shares = {}
        for g, amounts in rec.get("amounts", {}).items():
            a = _single_agreed(amounts, lambda e: e)     # a disagreeing amount leaves the group pending
            if a is not None:
                shares[g] = {"amount": float(a)}
        out["shares"] = shares                          # groups 5-7 come from the rules
    try:
        return to_ref(out)
    except Exception:                                   # a bad file never becomes a result
        return None
