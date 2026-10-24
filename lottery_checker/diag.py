"""Keep the raw OCR of a results screenshot that didn't read cleanly (22 Oct 2026),
and turn it into a learning record (22 Oct 2026).

Why: draw 4145 was uploaded and refused with "Still missing: winning numbers",
yet web.log held nothing about it, so there was no way to tell whether Vision
dropped a number, reordered the row or the parser misread it. Now every
top-of-page read that comes up short leaves one log line and one small JSON file
(the OCR text and word boxes) in data/failed/screens/.

Learning record (owner, 22 Oct 2026: "log errors to records for learning and
improving vision"): the same event is also appended, uncapped, to
data/learning/vision_reads.jsonl, one line per short read (when, game, draw, what
was missing, the numbers that did read, the OCR text). Once the true result for
that draw is known (the official capture, or a crowd result two people agreed
on), review() lines the read up against it and names the kind of error: a number
dropped, an extra one, or a wrong one. tools/vision_review.py prints that and
writes data/learning/vision_review.csv. Screenshots of results pages only: ticket
photos are never recorded (their text has serial numbers).

What is kept: the OCR text and word positions of an official RESULTS page only
(the read found a game and a draw number). Never the image. Capped at KEEP files,
oldest removed first. Never raises: a diagnostics problem must not fail an upload.
"""
from __future__ import annotations

import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# uvicorn's own logger, so the line lands in logs\web.log with the server output
log = logging.getLogger("uvicorn.error")

KEEP = 60
MAX_WORDS = 500
LEDGER_MAX_BYTES = 5_000_000        # past this the ledger is moved aside to vision_reads.jsonl.1
TEXT_MAX = 4000


def ledger_path(data_dir: Path) -> Path:
    return Path(data_dir) / "learning" / "vision_reads.jsonl"


def _numbers(read: Any) -> dict:
    """The part of a read worth lining up against the truth."""
    if read.game == "toto":
        return {"winning": list(read.winning or read.winning_partial), "additional": read.additional}
    return {"first": read.first, "second": read.second, "third": read.third}


def _append_ledger(data_dir: Path, read: Any, text: str, name: str, words: int) -> None:
    path = ledger_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > LEDGER_MAX_BYTES:
        path.replace(path.with_name(path.name + ".1"))
    line = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": "screenshot",
            "game": read.game, "draw_no": read.draw_no,
            "date": read.draw_date.isoformat() if read.draw_date else None,
            "missing": read.missing, "read": _numbers(read), "text": text[:TEXT_MAX],
            "words": words, "file": name}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def save_failed(data_dir: Path, ocr_result: Any, read: Any) -> None:
    try:
        text = getattr(ocr_result, "text", "") or ""
        words = [[w.text, *w.box] for w in (getattr(ocr_result, "words", None) or [])][:MAX_WORDS]
        folder = Path(data_dir) / "failed" / "screens"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        name = f"{stamp}_{read.game}_{read.draw_no}.json"
        n = 1
        while (folder / name).exists():                 # two reads in the same second
            n += 1
            name = f"{stamp}_{read.game}_{read.draw_no}_{n}.json"
        payload = {"game": read.game, "draw_no": read.draw_no,
                   "date": read.draw_date.isoformat() if read.draw_date else None,
                   "missing": read.missing, "winning_read": read.winning or read.winning_partial,
                   "text": text, "words": words}
        (folder / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        _append_ledger(data_dir, read, text, name, len(words))
        for old in sorted(folder.glob("*.json"))[:-KEEP]:
            old.unlink(missing_ok=True)
        log.warning("screenshot read came up short: %s draw %s, missing %s; raw OCR saved to data/failed/screens/%s",
                    read.game, read.draw_no, ", ".join(read.missing), name)
    except Exception:                                    # noqa: BLE001 - diagnostics only
        log.exception("could not save the failed screenshot read")


def check_reads(data_dir: Path, ocrs: list, reads: list) -> None:
    """For each screenshot that looks like the top of a result but didn't read fully."""
    for o, r in zip(ocrs, reads):
        if r.top_incomplete:
            save_failed(data_dir, o, r)


# ---------------------------------------------------------------- learning: read vs the truth

def compare_numbers(read: list, truth: list) -> dict:
    """How a numbers row differs from the true row: {"kind": ok|dropped|extra|wrong, ...}."""
    r, t = sorted(read), sorted(truth)
    if r == t:
        return {"kind": "ok"}
    sr, st = set(r), set(t)
    if sr < st:
        return {"kind": "dropped", "missing": sorted(st - sr)}
    if st < sr:
        return {"kind": "extra", "extra": sorted(sr - st)}
    return {"kind": "wrong", "missing": sorted(st - sr), "extra": sorted(sr - st)}


def truth_for(game: str, draw_no: int, data_dir: Path) -> tuple[Optional[dict], Optional[str]]:
    """The known result for a draw and where it came from: (numbers, "official" | "crowd-agreed")."""
    from . import shared, store
    for source, loader in (("official", store.load_ref), ("crowd-agreed", shared.load_shared_ref)):
        try:
            ref = loader(game, draw_no, data_dir)
        except Exception:                                # noqa: BLE001
            ref = None
        if ref is None:
            continue
        d = ref.draw
        if game == "toto":
            return {"winning": sorted(d.winning), "additional": d.additional}, source
        return {"first": d.first, "second": d.second, "third": d.third}, source
    return None, None


def review(data_dir: Path) -> list[dict]:
    """One row per ledger line, with the truth and the kind of error once the truth is known."""
    path = ledger_path(data_dir)
    rows = []
    if not path.is_file():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        truth, source = (truth_for(e["game"], e["draw_no"], data_dir) if e.get("draw_no") else (None, None))
        row = {"at": e["at"], "game": e["game"], "draw_no": e["draw_no"], "missing": ", ".join(e["missing"]),
               "read": e["read"], "truth": truth, "truth_source": source, "kind": "no truth yet", "detail": ""}
        if truth:
            if e["game"] == "toto":
                c = compare_numbers(e["read"].get("winning", []), truth["winning"])
                row["kind"] = c["kind"]
                row["detail"] = " ".join(f"{k} {v}" for k, v in c.items() if k != "kind")
                if e["read"].get("additional") not in (None, truth["additional"]):
                    row["detail"] += f" additional read {e['read']['additional']} true {truth['additional']}"
            else:
                bad = [k for k in ("first", "second", "third") if e["read"].get(k) not in (None, truth[k])]
                row["kind"] = "wrong" if bad else ("dropped" if any(e["read"].get(k) is None for k in truth) else "ok")
                row["detail"] = " ".join(bad)
        rows.append(row)
    return rows


def write_review_csv(data_dir: Path) -> Path:
    rows = review(data_dir)
    out = Path(data_dir) / "learning" / "vision_review.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["logged_at_utc", "game", "draw_no", "missing", "read", "truth", "truth_source", "kind", "detail"])
        for r in rows:
            w.writerow([r["at"], r["game"], r["draw_no"], r["missing"], json.dumps(r["read"]),
                        json.dumps(r["truth"]) if r["truth"] else "", r["truth_source"] or "", r["kind"], r["detail"]])
    return out
