"""After-draw results capture (P2-03), with guardrails.

Decision 17 Oct 2026: free, non-monetised public checker; results captured
once per draw from the official page, cited to Singapore Pools, not claimed
as ours. Written permission has been requested; stop if Singapore Pools objects.

Guardrails built in:
- Kill switch: nothing is fetched unless TOTO_INGEST_ENABLED=1.
- One request per run, no retries inside a run (cron runs once more 15 min later).
- Skips the request entirely if the draw is already stored.
- Honest user agent with a contact address (TOTO_CONTACT), never a browser string.
- Stores the raw page for our records and a parsed JSON record with attribution.
- No bulk history and no other Singapore Pools endpoints.

Usage (from the project folder):
    TOTO_INGEST_ENABLED=1 TOTO_CONTACT=you@zenqi.cc python -m lottery_checker.ingest toto
    TOTO_INGEST_ENABLED=1 TOTO_CONTACT=you@zenqi.cc python -m lottery_checker.ingest 4d
    TOTO_INGEST_ENABLED=1 TOTO_CONTACT=you@zenqi.cc python -m lottery_checker.ingest toto --catch-up

Special TOTO draws (P0-04, P2-07): New Year, Reunion, Hong Bao and National Day
draws are ordinary TOTO draws moved to a Friday in place of that week's Thursday.
The Friday task runs with --catch-up: it makes no request when a draw dated
yesterday or today is already stored (a normal week), so it only fetches when
Thursday's run found no new draw.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .parse import ParseError, parse_fourd, parse_toto

BASE = "https://www.singaporepools.com.sg"
PAGES = {
    "toto": BASE + "/en/product/sr/Pages/toto_results.aspx",
    "4d": BASE + "/en/product/Pages/4d_results.aspx",
}
ATTRIBUTION = (
    "Results: Singapore Pools (singaporepools.com.sg). "
    "We do not own this data. The official results published by Singapore Pools are final."
)
TIMEOUT_S = 20


class IngestDisabled(RuntimeError):
    """Kill switch is off."""


def official_url(game: str, draw_no: Optional[int] = None) -> str:
    """Official results page; with a draw number, the deep link to that draw."""
    url = PAGES[game]
    if draw_no is None:
        return url
    token = base64.b64encode(f"DrawNumber={draw_no}".encode()).decode()
    return f"{url}?sppl={token}"


def user_agent() -> str:
    contact = os.environ.get("TOTO_CONTACT", "").strip()
    if not contact:
        raise IngestDisabled("set TOTO_CONTACT to a contact email before fetching")
    return f"ZenQiTotoChecker/0.1 (+https://toto.zenqi.cc; contact: {contact})"


def enabled() -> bool:
    return os.environ.get("TOTO_INGEST_ENABLED", "0") == "1"


def fetch(game: str, draw_no: Optional[int] = None) -> tuple[str, dict]:
    """One GET of the official page.

    Returns the body and a small meta dict (final URL, status, content type,
    length) so a failed parse can be diagnosed without re-requesting the page.
    Raises IngestDisabled if the kill switch is off.
    """
    if not enabled():
        raise IngestDisabled("TOTO_INGEST_ENABLED is not 1; using the screenshot flow instead")
    url = official_url(game, draw_no)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        body = r.read().decode("utf-8", errors="replace")
        meta = {
            "requested_url": url,
            "final_url": r.geturl(),          # differs if we were redirected
            "status": getattr(r, "status", None),
            "content_type": r.headers.get("Content-Type"),
            "bytes": len(body),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    return body, meta


def save_failure(game: str, html: str, meta: dict, data_dir: Path, why: str) -> Path:
    """Keep the page we could not parse, so the next session has evidence.

    A parser that fails loudly is only useful if it keeps what it choked on.
    One file per attempt, timestamped, never overwritten.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = data_dir / "failed" / game
    folder.mkdir(parents=True, exist_ok=True)
    page = folder / f"{stamp}.html"
    page.write_text(html, encoding="utf-8")
    (folder / f"{stamp}.json").write_text(
        json.dumps({**meta, "error": why, "head": html[:2000]}, indent=2), encoding="utf-8")
    return page


def _record(game: str, res) -> dict:
    d = res.draw
    rec = {
        "game": game,
        "draw_no": d.draw_no,
        "draw_date": res.draw_date.isoformat(),
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Singapore Pools",
        "official_url": official_url(game, d.draw_no),
        "attribution": ATTRIBUTION,
        # P2-01: which rule set priced this draw, and whether that version has
        # been checked against its own rules PDF.
        "rules_version": d.rules.version,
        "rules_verified": d.rules.verified,
    }
    if game == "toto":
        rec.update(
            winning=list(d.winning),
            additional=d.additional,
            group1_prize_pool=res.group1_prize_pool,
            shares={str(g): {"amount": a, "winners": n} for g, (a, n) in sorted(res.shares.items())},
        )
    else:
        rec.update(
            first=d.first, second=d.second, third=d.third,
            starter=list(d.starter), consolation=list(d.consolation),
        )
    return rec


def store(game: str, html: str, data_dir: Path) -> list[dict]:
    """Parse a page and store raw + JSON per draw. Returns the records stored."""
    results = parse_toto(html) if game == "toto" else parse_fourd(html)
    out = []
    for res in results:
        rec = _record(game, res)
        n = rec["draw_no"]
        raw_p = data_dir / "raw" / game / f"{n}.html"
        json_p = data_dir / "draws" / game / f"{n}.json"
        raw_p.parent.mkdir(parents=True, exist_ok=True)
        json_p.parent.mkdir(parents=True, exist_ok=True)
        raw_p.write_text(html, encoding="utf-8")
        json_p.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        out.append(rec)
    if out:
        from .results_db import compile_quietly
        compile_quietly(data_dir)                       # keep data/results/ current
    return out


def already_stored(game: str, draw_no: int, data_dir: Path) -> bool:
    return (data_dir / "draws" / game / f"{draw_no}.json").exists()


def stored_for_date(game: str, day: str, data_dir: Path) -> bool:
    """True if a draw dated `day` (YYYY-MM-DD) is already stored, so the retry run makes no request."""
    folder = data_dir / "draws" / game
    if not folder.exists():
        return False
    for p in folder.glob("*.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("draw_date") == day:
                return True
        except (OSError, ValueError):
            continue
    return False


# 4D page note (diagnosed 21 Oct 2026): the plain 4d_results.aspx is filled in by
# script after load, so a plain GET carries no .tables-wrap block (both 18 Oct runs
# failed this way). The deep link ?sppl=DrawNumber=N is server-rendered like the TOTO
# page, and a number not yet drawn falls back to the latest published draw. So 4D
# always asks for the next draw by number and checks what came back.
FOURD_SEED_DRAW = 5551   # first draw after 5550 (Sun 18 Oct 2026); used only when nothing is stored


def latest_stored(game: str, data_dir: Path) -> Optional[int]:
    folder = data_dir / "draws" / game
    nums = [int(p.stem) for p in folder.glob("*.json") if p.stem.isdigit()] if folder.exists() else []
    return max(nums) if nums else None


def next_fourd_draw(data_dir: Path) -> int:
    last = latest_stored("4d", data_dir)
    return last + 1 if last is not None else FOURD_SEED_DRAW


def today_sgt() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=8)).date().isoformat()


def yesterday_sgt() -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(today_sgt()) - timedelta(days=1)).isoformat()


def run(game: str, data_dir: Path, draw_no: Optional[int] = None, catch_up: bool = False) -> int:
    if catch_up and stored_for_date(game, yesterday_sgt(), data_dir):
        print(f"[{game}] catch-up: yesterday's draw already stored, no special draw expected; no request made")
        return 0
    if draw_no is not None and already_stored(game, draw_no, data_dir):
        print(f"[{game}] draw {draw_no} already stored; no request made")
        return 0
    if draw_no is None and stored_for_date(game, today_sgt(), data_dir):
        print(f"[{game}] today's draw already stored; no request made")
        return 0
    want = draw_no
    if game == "4d" and want is None:
        want = next_fourd_draw(data_dir)
    try:
        html, meta = fetch(game, want)
    except IngestDisabled as e:
        print(f"[{game}] ingest off: {e}")
        return 0
    if meta["final_url"] != meta["requested_url"]:
        print(f"[{game}] NOTE redirected to {meta['final_url']}", file=sys.stderr)
    try:
        recs = store(game, html, data_dir)
    except (ParseError, ValueError) as e:
        saved = save_failure(game, html, meta, data_dir, str(e))
        print(f"[{game}] PARSE FAILED: {e}", file=sys.stderr)
        print(f"[{game}]   status={meta['status']} type={meta['content_type']} "
              f"bytes={meta['bytes']} url={meta['final_url']}", file=sys.stderr)
        print(f"[{game}]   page saved for diagnosis: {saved}", file=sys.stderr)
        return 2
    for r in recs:
        print(f"[{game}] stored draw {r['draw_no']} ({r['draw_date']})")
    if want is not None and want not in {r["draw_no"] for r in recs}:
        got = ", ".join(str(r["draw_no"]) for r in recs) or "nothing"
        print(f"[{game}] NOTE draw {want} not published yet; page returned {got}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Capture one official TOTO or 4D result after a draw.")
    p.add_argument("game", choices=["toto", "4d"])
    p.add_argument("--draw", type=int, help="specific draw number (default: latest on the page)")
    p.add_argument("--data", type=Path, default=Path("data"), help="data folder (default ./data)")
    p.add_argument("--catch-up", action="store_true",
                   help="only fetch if no draw is stored for yesterday or today (Friday special-draw run)")
    a = p.parse_args(argv)
    return run(a.game, a.data, a.draw, catch_up=a.catch_up)


if __name__ == "__main__":
    sys.exit(main())
