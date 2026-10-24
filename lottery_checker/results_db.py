"""Results database: every draw we hold, from both sources, by draw number and by date.

Owner's request, 22 Oct 2026: "store the crowd scan and compile the results,
by draw no and by date". Two sources feed it, each kept in its own files:

- official   data/draws/<game>/<n>.json   the after-draw capture (ingest.py)
- crowd      data/shared/<game>/<n>.json  users' screenshot reads (shared.py):
                                          every read, who (hashed), device, when

compile() merges them into data/results/<game>.json (by_draw, by_date, years),
data/results/<game>.csv (everything) and data/results/<game>-<year>.csv (one
year, every draw number from YEAR_FIRST to the latest, gaps marked "missing").
The CSVs open in Excel. It runs after every capture and every
crowd read, and from the command line:

    py -3 -m lottery_checker.results_db                  # compile, list both games
    py -3 -m lottery_checker.results_db toto --draw 4227
    py -3 -m lottery_checker.results_db 4d --date 2026-10-21

States: official (captured), agreed (two people's screenshots read the same,
served to users), waiting (one person so far), void (screenshots disagreed or
the date can't belong to the draw; never served). Only official and agreed
draws are ever used to check a ticket; waiting and void are kept for the owner.
A waiting draw is in this database with its numbers AND the Group 1-4 amounts
that one screenshot showed (owner, 22 Oct 2026: a screenshot taken straight from
the official page belongs in the compiled database even before a second person
confirms it); the state says it is one person's reading, and `shares_confirmed`
is false until two agree.

This is the owner's file on Grayskull. The web API does not serve it as a list
(api.py guardrail: no results feed), pending Singapore Pools' reply (P2-02).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import shared
from .store import GAMES, load_record

ROOT = Path(__file__).resolve().parent.parent

# First draw of each year, so a year's CSV lists every draw number from there to the
# latest on file, with the ones we don't hold marked "missing" (owner, 22 Oct 2026:
# 4D from 5426 and TOTO from 4144 for 2026). A year not listed here starts at its
# first draw on file. Add each new year's first draw when it is known.
YEAR_FIRST = {"toto": {2026: 4144}, "4d": {2026: 5426}}


def _read(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _numbers(game: str, rec: dict) -> dict:
    if game == "toto":
        return {"winning": list(rec.get("winning", [])), "additional": rec.get("additional")}
    return {k: rec.get(k) for k in ("first", "second", "third", "starter", "consolation")}


def _official_row(game: str, rec: dict) -> dict:
    row = {"game": game, "draw_no": rec["draw_no"], "draw_date": rec.get("draw_date"),
           "state": "official", "source": "Singapore Pools (captured)",
           "captured_at": rec.get("captured_at"), **_numbers(game, rec)}
    if game == "toto":
        row["shares"] = {g: v.get("amount") for g, v in rec.get("shares", {}).items()}
    return row


def _crowd_row(game: str, rec: dict, state: str) -> dict:
    entries = [e for c in rec.get("candidates", {}).values() for e in c.get("entries", [])]
    people = {e["who"] for e in entries}
    devices: dict[str, int] = {}
    seen = set()
    for e in entries:
        if e["who"] not in seen:
            seen.add(e["who"])
            devices[e.get("device", "Unknown")] = devices.get(e.get("device", "Unknown"), 0) + 1
    times = sorted(e["at"] for e in entries if e.get("at"))
    dates = list(rec.get("dates", {}))
    row = {"game": game, "draw_no": rec["draw_no"], "draw_date": dates[0] if len(dates) == 1 else None,
           "state": state, "source": "users' screenshots",
           "crowd": {"people": len(people), "devices": devices,
                     "first_at": times[0] if times else None, "last_at": times[-1] if times else None,
                     "readings": [{"numbers": c["numbers"], "people": len({e["who"] for e in c["entries"]})}
                                  for c in rec.get("candidates", {}).values()],
                     "dates_read": {d: len({e["who"] for e in es}) for d, es in rec.get("dates", {}).items()},
                     "void_why": (rec.get("void") or {}).get("why")}}
    if state in ("agreed", "waiting") and len(rec.get("candidates", {})) == 1:
        (c,) = rec["candidates"].values()
        row.update(c["numbers"])
    return row


def collect(game: str, data_dir: Path) -> list[dict]:
    """Every draw on file for one game, newest first. An official capture wins
    over crowd reads of the same draw (the crowd record is then noted only)."""
    data_dir = Path(data_dir)
    rows: dict[int, dict] = {}
    for p in sorted((data_dir / "draws" / game).glob("*.json")):
        if not p.stem.isdigit():
            continue
        rec = load_record(game, int(p.stem), data_dir)
        if rec:
            rows[rec["draw_no"]] = _official_row(game, rec)
    for p in sorted((data_dir / "shared" / game).glob("*.json")):
        rec = _read(p)
        if not rec or not p.stem.isdigit() or rec.get("draw_no") != int(p.stem) or rec.get("game") != game:
            continue
        n = rec["draw_no"]
        state = shared._state(rec)
        if n in rows:
            rows[n]["crowd_also"] = state           # official wins; note that users sent screenshots too
            continue
        row = _crowd_row(game, rec, state)
        if state in ("agreed", "waiting") and game == "toto":
            amounts = {}
            for g, opts in rec.get("amounts", {}).items():
                if state == "agreed":
                    a = shared._single_agreed(opts, lambda e: e)
                else:                                    # one person so far: the amount they read, if they read one value
                    a = next(iter(opts)) if len(opts) == 1 else None
                amounts[g] = float(a) if a is not None else None
            row["shares"] = amounts
            row["shares_confirmed"] = state == "agreed"
        rows[n] = row
    return [rows[n] for n in sorted(rows, reverse=True)]


def compile(data_dir: Path) -> dict:
    """Write data/results/<game>.json and .csv. Returns {game: compiled}."""
    data_dir = Path(data_dir)
    out_dir = data_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    done = {}
    for game in GAMES:
        rows = collect(game, data_dir)
        by_date: dict[str, list[int]] = {}
        for r in rows:
            if r.get("draw_date"):
                by_date.setdefault(r["draw_date"], []).append(r["draw_no"])
        comp = {"game": game, "compiled_at": now,
                "counts": {s: sum(r["state"] == s for r in rows) for s in ("official", "agreed", "waiting", "void")},
                "by_draw": {str(r["draw_no"]): r for r in rows},
                "by_date": dict(sorted(by_date.items(), reverse=True))}
        tmp = out_dir / f"{game}.json.tmp"
        _csv(game, rows, out_dir / f"{game}.csv")
        years = by_year(game, rows)
        comp["years"] = {}
        for year, yrows in years.items():
            _csv(game, yrows, out_dir / f"{game}-{year}.csv")
            comp["years"][str(year)] = coverage(yrows)
        tmp.write_text(json.dumps(comp, indent=1), encoding="utf-8")
        tmp.replace(out_dir / f"{game}.json")
        done[game] = comp
    return done


def by_year(game: str, rows: list[dict]) -> dict[int, list[dict]]:
    """Rows per draw year, newest first, with "missing" rows for draw numbers in
    the year's range that we hold nothing for. Draws with no readable date are
    placed by draw number between dated draws."""
    dated = sorted((r["draw_no"], int(r["draw_date"][:4])) for r in rows if r.get("draw_date"))
    years: dict[int, list[dict]] = {}
    if not dated:
        return years
    by_no = {r["draw_no"]: r for r in rows}

    def year_of(n: int) -> int:
        for y, first in sorted(YEAR_FIRST.get(game, {}).items(), reverse=True):
            if n >= first:
                return y
        before = [y for dn, y in dated if dn <= n]
        return before[-1] if before else dated[0][1]

    all_years = {y for _, y in dated} | {year_of(n) for n in by_no}
    for y in sorted(all_years):
        first = YEAR_FIRST.get(game, {}).get(y)
        nos = [n for n in by_no if year_of(n) == y]
        if not nos:
            continue
        lo = first if first is not None else min(nos)
        nxt = YEAR_FIRST.get(game, {}).get(y + 1)
        hi = max(nos) if nxt is None else min(max(nos), nxt - 1)
        years[y] = [by_no.get(n) or {"game": game, "draw_no": n, "draw_date": None, "state": "missing",
                                     "source": "not on file"}
                    for n in range(hi, lo - 1, -1)]
    return years


def coverage(yrows: list[dict]) -> dict:
    nos = [r["draw_no"] for r in yrows]
    usable = sum(r["state"] in ("official", "agreed") for r in yrows)
    return {"from": min(nos), "to": max(nos), "draws": len(nos), "usable": usable,
            "missing": sum(r["state"] == "missing" for r in yrows),
            "missing_draws": [r["draw_no"] for r in yrows if r["state"] == "missing"][::-1]}


# Draws are at 18:30 (TOTO 21:30 cut-off varies); by 22:00 SGT a draw is on the official page.
RESULTS_UP_BY_HOUR = 22


DRAW_WEEKDAYS = {"toto": {0, 3}, "4d": {2, 5, 6}}     # Mon/Thu; Wed/Sat/Sun


def latest_drawn(game: str, now: Optional[datetime] = None) -> int:
    """The newest draw number that should have a published result by now (SGT),
    counted on the draw-day calendar from the timetable anchor in results_screen.
    A special draw that moves a Thursday to the Friday doesn't change the count."""
    from datetime import timedelta
    from .results_screen import _ANCHORS
    now = now or datetime.now(timezone(timedelta(hours=8)))
    today = now.date()
    if now.hour < RESULTS_UP_BY_HOUR:
        today -= timedelta(days=1)                      # today's draw isn't up yet
    n0, d0, _ = _ANCHORS[game]
    days = DRAW_WEEKDAYS[game]
    step = 1 if today >= d0 else -1
    n, d = n0, d0
    while d != today:
        if step > 0:
            d += timedelta(days=1)
            n += d.weekday() in days
        else:
            n -= d.weekday() in days
            d -= timedelta(days=1)
    return n


def wanted(game: str, data_dir: Path, now: Optional[datetime] = None) -> dict:
    """This year's draws that crowd screenshots can still fill: draw numbers only,
    never results. 'missing' (nothing on file) or 'waiting' (one person so far;
    one more screenshot makes it usable). Void draws are left out: they never
    become usable."""
    from datetime import timedelta
    now = now or datetime.now(timezone(timedelta(hours=8)))
    year = now.year
    first = YEAR_FIRST.get(game, {}).get(year)
    last = latest_drawn(game, now)
    rows = {r["draw_no"]: r for r in collect(game, data_dir)}
    if first is None:                                   # a year with no start set yet: from its first draw on file
        dated = [n for n, r in rows.items() if (r.get("draw_date") or "").startswith(str(year))]
        first = min(dated) if dated else last
    out = []
    for n in range(last, first - 1, -1):
        r = rows.get(n)
        state = "missing" if r is None else r["state"]
        if state in ("missing", "waiting"):
            from .ingest import official_url
            out.append({"draw_no": n, "state": state, "official_url": official_url(game, n)})
    usable = sum(1 for n in range(first, last + 1) if n in rows and rows[n]["state"] in ("official", "agreed"))
    waiting = sum(1 for x in out if x["state"] == "waiting")
    return {"game": game, "year": year, "from": first, "to": last, "draws": last - first + 1,
            "usable": usable, "waiting": waiting, "missing": len(out) - waiting,
            "on_file": usable + waiting, "wanted": out}


def compile_quietly(data_dir: Path) -> None:
    """For the capture and crowd-read hooks: a failed compile never fails those."""
    try:
        compile(data_dir)
    except Exception as e:                       # noqa: BLE001
        print(f"[results_db] compile failed: {e}", file=sys.stderr)


def _numbers_text(r: dict) -> str:
    if r["game"] == "toto":
        if not r.get("winning"):
            return ""
        return " ".join(f"{n:02d}" for n in r["winning"]) + (f" + {r['additional']:02d}" if r.get("additional") else "")
    if not r.get("first"):
        return ""
    return (f"1st {r['first']} 2nd {r['second']} 3rd {r['third']} | S: {' '.join(r.get('starter') or [])}"
            f" | C: {' '.join(r.get('consolation') or [])}")


def _csv(game: str, rows: list[dict], path: Path) -> None:
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        head = ["draw_no", "draw_date", "state", "source", "numbers"]
        if game == "toto":
            head += [f"group{g}" for g in range(1, 5)]
        head += ["people", "devices", "note"]
        w.writerow(head)
        for r in rows:
            c = r.get("crowd") or {}
            line = [r["draw_no"], r.get("draw_date") or "", r["state"], r["source"], _numbers_text(r)]
            if game == "toto":
                sh = r.get("shares") or {}
                line += [sh.get(str(g)) if sh.get(str(g)) is not None else "" for g in range(1, 5)]
            note = (c.get("void_why") or
                    (f"users also sent screenshots ({r['crowd_also']})" if r.get("crowd_also") else "") or
                    ("one person's screenshot so far, not yet confirmed" if r["state"] == "waiting" else ""))
            line += [c.get("people", ""), "; ".join(f"{k} x{v}" for k, v in (c.get("devices") or {}).items()), note]
            w.writerow(line)
    tmp.replace(path)


def find(game: str, data_dir: Path, draw_no: Optional[int] = None, day: Optional[str] = None) -> list[dict]:
    rows = collect(game, data_dir)
    if draw_no is not None:
        rows = [r for r in rows if r["draw_no"] == draw_no]
    if day:
        rows = [r for r in rows if r.get("draw_date") == day]
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Compile and look up the results database.")
    p.add_argument("game", nargs="?", choices=GAMES)
    p.add_argument("--draw", type=int)
    p.add_argument("--date", help="YYYY-MM-DD")
    p.add_argument("--data", default=str(ROOT / "data"))
    a = p.parse_args(argv)
    data_dir = Path(a.data)
    comp = compile(data_dir)
    for game in ([a.game] if a.game else GAMES):
        rows = find(game, data_dir, a.draw, a.date)
        c = comp[game]["counts"]
        for y, cv in comp[game]["years"].items():
            print(f"\n{game.upper()} {y}: draws {cv['from']}-{cv['to']} ({cv['draws']}), usable {cv['usable']}, "
                  f"missing {cv['missing']}   -> data\\results\\{game}-{y}.csv")
        print(f"\n{game.upper()}  official {c['official']} · crowd agreed {c['agreed']} · "
              f"waiting {c['waiting']} · void {c['void']}   -> data\\results\\{game}.json / .csv")
        if not rows:
            print("  (nothing on file" + (" for that draw/date" if a.draw or a.date else "") + ")")
        for r in rows:
            crowd = r.get("crowd") or {}
            extra = f"  [{crowd.get('people')} people]" if crowd else ""
            if crowd.get("void_why"):
                extra += f"  void: {crowd['void_why']}"
            print(f"  {r['draw_no']}  {r.get('draw_date') or '????-??-??'}  {r['state']:<8} {_numbers_text(r)}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
