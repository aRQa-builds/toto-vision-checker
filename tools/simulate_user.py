"""Walk the intended user journey end to end against the real matcher.

The user here is a physical ticket buyer: they hold a printed Singapore Pools
ticket, open toto.zenqi.cc, photograph the ticket, and want to know what it paid.

Run:  py -3 tools\\simulate_user.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lottery_checker import fourd, toto                      # noqa: E402
from lottery_checker.ingest import official_url              # noqa: E402
from lottery_checker.parse import parse_fourd, parse_toto    # noqa: E402
from lottery_checker.ticket import DrawRef, check_ticket     # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
RULE = "-" * 68


def head(n, title):
    print(f"\n{RULE}\nSTEP {n}  {title}\n{RULE}")


def gap(text):
    print(f"   [GAP] {text}")


def money(v):
    return "not yet published" if v is None else f"S${v:,.2f}"


# ---------------------------------------------------------------- 4D journey

def journey_4d():
    print("\n\n######  JOURNEY A — 4D, physical ticket, iBet + Ordinary  ######")

    head(1, "User photographs the ticket")
    # What OCR is expected to return. Values hand-written here because P3-01
    # (Vision OCR) and P3-02 (ticket parser) do not exist yet.
    ocr = {
        "game": "4D",
        "draw_no": 5500,
        "draw_date": "24 Jun 2026",
        "bets": [
            {"kind": "ordinary", "number": "5950", "big": 2, "small": 0},
            {"kind": "ibet",     "number": "0398", "big": 1, "small": 0},
            {"kind": "roll",     "number": "59R0", "big": 1, "small": 0},
        ],
        "printed_total": None,   # unknown: no real ticket photographed yet
    }
    print("   OCR hands back:")
    for b in ocr["bets"]:
        print(f"     {b['kind']:<9} {b['number']}  Big ${b['big']}  Small ${b['small']}")
    gap("P3-01 Vision OCR not built; this dict is typed by hand.")
    gap("P3-02 parser not built; no real ticket photo to learn the layout from.")
    gap("P0-02: unknown whether tickets print the draw number or only the date. "
        "The whole flow below assumes a draw number.")

    head(2, "User confirms what we read (P3-03)")
    print("   Screen would show the three bets for correction. Assume confirmed.")
    gap("P3-03 confirm-and-correct screen not built.")

    head(3, "We price the stake and show it back")
    entries = [fourd.FourDEntry(b["kind"], b["number"], b["big"], b["small"]) for b in ocr["bets"]]
    total_stake = sum(e.cost_per_draw for e in entries)
    for e in entries:
        print(f"     {e.kind:<9} {e.number}  perms={e.perms:<3} cost/draw=S${e.cost_per_draw}")
    print(f"   Our computed stake: S${total_stake}")
    gap("P0-06: the iBet line assumes 'charged once'. If an outlet quotes "
        "$24 for a $1 iBet on four different digits, this total is wrong.")
    print("   Cross-check against the printed total:",
          "IMPOSSIBLE — no ticket" if ocr["printed_total"] is None else ocr["printed_total"])

    head(4, "User opens the official draw page (the hand-off)")
    print(f"   Deep link: {official_url('4d', ocr['draw_no'])}")
    print("   User sees the official result, screenshots it, comes back.")

    head(5, "We read the result")
    # Stands in for either the screenshot OCR (P4-10) or the scheduled capture (P2-03).
    (res,) = parse_fourd((FIX / "fourd_5500.html").read_text(encoding="utf-8"))
    d = res.draw
    print(f"   Draw {d.draw_no}, {res.draw_date}   rules: {d.rules.version}")
    print(f"   1st {d.first}   2nd {d.second}   3rd {d.third}")
    print(f"   Starter      {' '.join(d.starter)}")
    print(f"   Consolation  {' '.join(d.consolation)}")
    gap("P4-10 screenshot OCR not built. Tonight's scheduled capture (P2-03) "
        "will cover the auto path for this draw onward.")

    head(6, "Reveal  (through the P3-05 aggregator)")
    result = check_ticket(entries, [DrawRef.from_parsed(res)])
    for ln in result.lines:
        print(f"     {ln.label:<9} {ln.numbers:<6} stake S${ln.stake:,.0f}  "
              f"-> {'; '.join(ln.detail) if ln.detail else 'no win'}")
    print(f"\n   TOTAL WON  S${result.total_won:,.0f}      "
          f"stake S${result.total_stake:,.0f}      net S${result.net:,.0f}")
    print(f"   {result.claim_hint()}")


# -------------------------------------------------------------- TOTO journey

def journey_toto():
    print("\n\n######  JOURNEY B — TOTO, physical ticket, System 7  ######")

    head(1, "User photographs the ticket")
    ocr = {"game": "TOTO", "draw_no": 4068,
           "entry": ("system", (14, 26, 27, 30, 46, 10, 1))}
    print(f"   OCR hands back: System 7  {ocr['entry'][1]}")

    head(2, "Stake")
    entry = toto.TotoEntry(*ocr["entry"])
    print(f"   {entry.label}, {len(list(entry.sets()))} sets, stake S${entry.stake}")

    head(3, "Hand-off")
    print(f"   Deep link: {official_url('toto', ocr['draw_no'])}")

    head(4, "Result")
    (res,) = parse_toto((FIX / "toto_4068.html").read_text(encoding="utf-8"))
    d = res.draw
    print(f"   Draw {d.draw_no}, {res.draw_date}   rules: {d.rules.version} "
          f"(verified={d.rules.verified})")
    print(f"   Winning {d.winning}   Additional {d.additional}")
    print("   Published per-share amounts:")
    for g, (amt, winners) in sorted(res.shares.items()):
        print(f"     Group {g}: {money(amt)}   winners: {winners if winners is not None else '-'}")
    if not d.rules.verified:
        gap(f"This draw is priced with {d.rules.version}, whose values were copied "
            "from the 2026 rules and never checked against the 2022 PDF.")

    head(5, "Reveal  (through the P3-05 aggregator)")
    result = check_ticket([entry], [DrawRef.from_parsed(res)])
    for ln in result.lines:
        print(f"     {ln.label}  {ln.numbers}")
        for line in ln.detail or ["no win"]:
            print(f"        {line}")
    print(f"\n   TOTAL WON  {money(result.total_won)}      "
          f"stake S${result.total_stake:,.0f}")
    print(f"   {result.claim_hint()}")
    if result.pending_groups:
        print(f"   PENDING: groups {result.pending_groups} have no published amount. "
              "P4-12: the screen must say pending, never S$0.")


if __name__ == "__main__":
    journey_4d()
    journey_toto()
    print(f"\n{RULE}\nEnd of simulation.\n{RULE}")
