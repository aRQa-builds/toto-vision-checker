"""Results screenshot reader (P4-10): read the official results page from
the user's screenshot(s) and hand back a draw to confirm.

Flow (free tier, bring-your-own-result): ticket -> deep link to the official
page (P4-09) -> user screenshots it -> OCR (P3-01, ocr.recognize) -> this
module -> confirm screen -> check_ticket -> build_reveal.

What the pages look like on a phone (read 21 Oct 2026, draws 4227 and 5551,
375 px wide; samples in tests/fixtures/screens/):
- One screenshot does NOT hold the whole result. TOTO shows the numbers and
  Groups 1-2; Groups 3-7 are below the fold. 4D shows 1st-3rd and 8 of the 10
  Starters; the last Starters and all Consolation prizes are below the fold.
  So this reader takes several screenshots, merges them, and says exactly
  what is still missing instead of guessing.
- Noise to ignore: the "Next Draw" date, the Next Jackpot amount, and on 4D a
  Singapore Sweep banner with its own "DRAW DATE:" and "$2.3 MILLION".
- The header row "Mon, 19 Oct 2026 | Draw No. 4227" is the anchor for the
  draw number and date.
- TOTO "Group 1 Prize" is the POOL, not a share: with two winners each gets
  half. Only the Winning Shares table rows are read as share amounts. A group
  with no winners shows "-" and stays unread.

Safety rules:
- Never invent a number. Anything not found is listed in `missing`.
- The share table must read top to bottom in falling amounts. OCR that reads
  the table column by column could pair a group with the wrong amount, so an
  out-of-order table is dropped and reported, and those groups stay pending.
- Screenshots of different draws are refused, not merged.
- The result always goes to the confirm screen (P3-03) before the reveal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Optional, Sequence, Union

from .manual import EntryError, ManualResult, fourd_result, toto_result

_DATE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})\b")
_DRAW_NO = re.compile(r"Draw\s*No\.?\s*:?\s*(\d{3,5})", re.I)
_NOISE_BEFORE_DATE = re.compile(r"(Next\s+Draw|DRAW\s+DATE\s*:)\s*$", re.I)
_GROUP_ROW = re.compile(r"Group\s*([1-7])\s+\$\s?([\d,]+(?:\.\d+)?)\s+([\d,]+)\b")
_FOURD_TOKEN = re.compile(r"(?<![\d.,$])\b\d{4}\b(?![\d.,])")


class ScreenError(ValueError):
    """The screenshots cannot be read as one official result."""


@dataclass
class ScreenRead:
    game: Optional[str] = None
    draw_no: Optional[int] = None
    draw_date: Optional[date] = None
    # TOTO
    winning: list[int] = field(default_factory=list)
    winning_partial: list[int] = field(default_factory=list)     # numbers seen when fewer than 6 were read
    additional: Optional[int] = None
    shares: dict[int, float] = field(default_factory=dict)     # group -> share amount
    # 4D
    first: Optional[str] = None
    second: Optional[str] = None
    third: Optional[str] = None
    starter: list[str] = field(default_factory=list)
    starter_tail: list[str] = field(default_factory=list)       # last Starters, read without their heading
    consolation: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        out = []
        if self.draw_no is None:
            out.append("draw number")
        if self.draw_date is None:
            out.append("draw date")
        if self.game == "toto":
            if len(self.winning) != 6:
                out.append("winning numbers")
            if self.additional is None:
                out.append("Additional Number")
        elif self.game == "4d":
            for name in ("first", "second", "third"):
                if getattr(self, name) is None:
                    out.append({"first": "1st", "second": "2nd", "third": "3rd"}[name] + " Prize")
            if len(self.starter) != 10:
                out.append(f"Starter prizes ({len(self.starter)} of 10 read)")
            if len(self.consolation) != 10:
                out.append(f"Consolation prizes ({len(self.consolation)} of 10 read)")
        return out

    @property
    def missing_groups(self) -> list[int]:
        """TOTO groups with no share amount read (pending on the reveal, not an error)."""
        # Groups 5-7 are fixed prizes (cl. 5.5), so only 1-4 can be pending.
        return [g for g in range(1, 5) if g not in self.shares] if self.game == "toto" else []

    @property
    def complete(self) -> bool:
        return self.game is not None and not self.missing

    # Fields printed in the top part of the result. If one of these is missing the
    # user needs a better shot of the top, not a scroll down.
    _TOP = ("draw number", "draw date", "winning numbers", "Additional Number",
            "1st Prize", "2nd Prize", "3rd Prize")

    @property
    def top_missing(self) -> list[str]:
        return [m for m in self.missing if m in self._TOP]

    @property
    def top_incomplete(self) -> bool:
        """Looks like the top of a result page (it has a draw number) but the numbers
        didn't all read. Worth keeping the raw OCR for, to see why (diag.py)."""
        return self.game is not None and self.draw_no is not None and bool(self.top_missing)

    def _seen_note(self) -> str:
        if self.game == "toto" and len(self.winning) != 6:
            seen = self.winning or self.winning_partial
            if seen:
                return f" (only {len(seen)} of 6 read: {' '.join(map(str, seen))})"
        return ""

    def prompt(self) -> str:
        """What to tell the user when something is missing."""
        if self.complete:
            if self.missing_groups:
                gs = ", ".join(f"Group {g}" for g in self.missing_groups)
                return (f"Read the draw. No share amount found for {gs}: scroll down and add "
                        "a screenshot of the Winning Shares table, or carry on and any win in "
                        "those groups will show as pending.")
            return "Read the whole result. Please check it against your screen."
        head = "Still missing: " + ", ".join(self.missing) + self._seen_note() + ". "
        if self.top_missing:
            return head + ("Take a fresh screenshot of the top of the result (the date, Draw No. and "
                           "number rows, with nothing covering them), or type the numbers.")
        return head + "Scroll down on the official page and add another screenshot."


# ---------------------------------------------------------------- one screenshot

def _game(text: str) -> Optional[str]:
    t = text.lower()
    toto = sum(k in t for k in ("winning numbers", "additional number", "winning shares", "toto"))
    fourd = sum(k in t for k in ("1st prize", "starter", "consolation", "4d"))
    if _GROUP_ROW.search(text):
        toto += 2                                       # a bottom-of-page shot holds only Group rows
    if toto > fourd:
        return "toto"
    if fourd > toto:
        return "4d"
    return None


# Draw-number anchors and spacing, to sanity-check a date read off a screenshot.
# TOTO: Mon and Thu (3.5 days a draw on average); 4D: Wed, Sat, Sun (7/3 days).
# Special draws and holidays shift things by days, never by weeks.
_ANCHORS = {"toto": (4227, date(2026, 10, 19), 3.5), "4d": (5551, date(2026, 10, 21), 7 / 3)}
DATE_TOLERANCE_DAYS = 12


def expected_date(game: Optional[str], draw_no: Optional[int]) -> Optional[date]:
    if game not in _ANCHORS or draw_no is None:
        return None
    n0, d0, step = _ANCHORS[game]
    return d0 + timedelta(days=round((draw_no - n0) * step))


def plausible_date(game: Optional[str], draw_no: Optional[int], when: Optional[date]) -> bool:
    """False when a date can't belong to that draw number (e.g. the page's "Next
    Draw" date read as draw 4216's date, live 22 Oct 2026)."""
    exp = expected_date(game, draw_no)
    return when is None or exp is None or abs((when - exp).days) <= DATE_TOLERANCE_DAYS


def _header(text: str, game: Optional[str] = None) -> tuple[Optional[int], Optional[date]]:
    m = _DRAW_NO.search(text)
    draw_no = int(m.group(1)) if m else None
    # "Next Draw" and its date can land on different lines in Vision's text, with the
    # jackpot in between: skip the first date after any "Next Draw" label.
    skip = set()
    for nd in re.finditer(r"Next\s+Draw", text, re.I):
        d = _DATE.search(text, nd.end())
        if d and d.start() - nd.end() < 120:
            skip.add(d.start())
    best, best_gap = None, None
    for d in _DATE.finditer(text):
        if d.start() in skip or _NOISE_BEFORE_DATE.search(text[:d.start()]):
            continue                                    # "Next Draw ..." or banner "DRAW DATE: ..."
        when = datetime.strptime(" ".join(d.groups()), "%d %b %Y").date()
        if not plausible_date(game, draw_no, when):
            continue                                    # can't be this draw's date
        gap = abs(d.start() - m.start()) if m else d.start()
        if best_gap is None or gap < best_gap:
            best, best_gap = (d, when), gap
    return draw_no, (best[1] if best else None)


def _after(text: str, label: str, stop: Sequence[str] = ()) -> Optional[str]:
    i = text.lower().find(label.lower())
    if i < 0:
        return None
    rest = text[i + len(label):]
    cut = len(rest)
    for s in stop:
        j = rest.lower().find(s.lower())
        if 0 <= j < cut:
            cut = j
    return rest[:cut]


def _strip_noise(text: str) -> str:
    """Remove dates, draw numbers and money so stray 4-digit years and amounts are not read as numbers."""
    text = _DATE.sub(" ", text)
    text = _DRAW_NO.sub(" ", text)
    return re.sub(r"\$\s?[\d.,]+", " ", text)


_MONTHS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}


def _rows(items: list) -> list:
    """Words in page order: top to bottom by row, then left to right. A row is every
    word whose centre is within 0.6 of a word height of the row's first word, so a
    two-column table reads across (0273 0436 / 2089 2837), not down each column."""
    out, row = [], []
    for it in sorted(items, key=lambda i: i[1]):
        if row and it[1] - row[0][1] > 0.6 * max(it[3], row[0][3]):
            out += sorted(row, key=lambda i: i[0])
            row = []
        row.append(it)
    return out + sorted(row, key=lambda i: i[0])


def _fourd_from_words(words) -> dict:
    """4D numbers from word positions instead of text order.

    The desktop results page is a two-column table. Vision reads such a table
    column by column, so the text order puts the labels first and the numbers
    after, or the left column before the right one (23 Oct 2026: 1st, 2nd and 3rd
    all read as the first Starter, and 5 of 10 Starters and Consolations came back).
    Positions don't depend on that: the 1st/2nd/3rd numbers sit on their label's
    row, Starters between the two headings, Consolations below the second.
    Returns whatever it could place: first, second, third, starter, consolation.
    """
    ws = [w for w in words if w.text.strip()]
    if not ws:
        return {}
    def cx(w): return (w.box[0] + w.box[2]) / 2
    def cy(w): return (w.box[1] + w.box[3]) / 2
    def ht(w): return max(1, w.box[3] - w.box[1])
    toks = []                                            # (cx, cy, text, h, box top, box bottom)
    for i, w in enumerate(ws):
        t = w.text.strip()
        if not re.fullmatch(r"\d{4}", t):
            continue
        prev = ws[i - 1].text.strip().strip(".,").lower() if i else ""
        if prev in _MONTHS or prev == "no":              # a year in a date, or the Draw No.
            continue
        toks.append((cx(w), cy(w), t, ht(w), w))
    heads = {}
    for w in ws:
        k = re.sub(r"[^a-z]", "", w.text.lower())
        if k.startswith("starter") and "starter" not in heads:
            heads["starter"] = w
        elif k.startswith("consolation") and "consolation" not in heads:
            heads["consolation"] = w
    out: dict = {}
    for name, label in (("first", "1st"), ("second", "2nd"), ("third", "3rd")):
        lab = next((w for w in ws if w.text.strip().lower() == label), None)
        if lab is None:
            continue
        near = [t for t in toks if abs(t[1] - cy(lab)) <= 0.7 * max(t[3], ht(lab)) and t[0] > cx(lab)]
        if near:
            out[name] = min(near, key=lambda t: t[0] - cx(lab))[2]
    labelled = {out.get(n) for n in ("first", "second", "third")}
    top_s = heads.get("starter")
    top_c = heads.get("consolation")
    if top_s is not None:
        lo = top_s.box[3]
        hi = top_c.box[1] if top_c is not None else float("inf")
        band = [t for t in toks if lo <= t[1] < hi]
        out["starter"] = [t[2] for t in _rows(band)][:10]
    if top_c is not None:
        band = [t for t in toks if t[1] >= top_c.box[3]]
        out["consolation"] = [t[2] for t in _rows(band)][:10]
    return out


def read_screen(text: str, words=None) -> ScreenRead:
    r = ScreenRead(game=_game(text))
    r.draw_no, r.draw_date = _header(text, r.game)

    if r.game == "toto":
        seg = _after(text, "Winning Numbers", ("Additional Number", "Group 1 Prize", "Winning Shares"))
        if seg is not None:
            nums = [int(n) for n in re.findall(r"\b\d{1,2}\b", _strip_noise(seg)) if 1 <= int(n) <= 49]
            r.winning = nums[:6]
        seg = _after(text, "Additional Number", ("Group 1 Prize", "Winning Shares"))
        if seg is not None:
            nums = [int(n) for n in re.findall(r"\b\d{1,2}\b", _strip_noise(seg)) if 1 <= int(n) <= 49]
            r.additional = nums[0] if nums else None
        rows = {int(g): float(a.replace(",", "")) for g, a, _n in _GROUP_ROW.findall(text)}
        r.shares = _ordered_shares(rows, r.notes)

    elif r.game == "4d":
        clean = _strip_noise(text)
        for name, label in (("first", "1st Prize"), ("second", "2nd Prize"), ("third", "3rd Prize")):
            seg = _after(clean, label)
            if seg:
                tok = _FOURD_TOKEN.findall(seg)
                setattr(r, name, tok[0] if tok else None)
        seg = _after(clean, "Starter", ("Consolation",))
        if seg is not None:
            r.starter = _FOURD_TOKEN.findall(seg)[:10]
        seg = _after(clean, "Consolation")
        if seg is not None:
            r.consolation = _FOURD_TOKEN.findall(seg)[:10]
            if not r.starter and r.third is None:
                # Scrolled shot: numbers above "Consolation" with no "Starter" heading
                # are the LAST Starters. Their position is known from the end.
                i = clean.lower().find("consolation")
                r.starter_tail = _FOURD_TOKEN.findall(clean[:i])[-10:]
        elif not r.first and _FOURD_TOKEN.findall(clean) and not r.starter:
            r.notes.append("only bare numbers on this screenshot, no section headings; "
                           "not used, because their place in the table is unknown")
        if words:
            g = _fourd_from_words(words)
            # Position beats text order, but only where it found more than the text did.
            if all(g.get(n) for n in ("first", "second", "third")):
                r.first, r.second, r.third = g["first"], g["second"], g["third"]
            for name in ("starter", "consolation"):
                got = g.get(name) or []
                if len(got) > len(getattr(r, name)) or (len(got) == 10 and getattr(r, name) != got):
                    setattr(r, name, got)
                    if name == "starter":
                        r.starter_tail = []
    return r


def _ordered_shares(rows: dict[int, float], notes: list[str]) -> dict[int, float]:
    groups = sorted(rows)
    amounts = [rows[g] for g in groups]
    if any(a < b for a, b in zip(amounts, amounts[1:])):
        notes.append("the Winning Shares table did not read top to bottom in falling amounts, "
                     "so none of its amounts were used")
        return {}
    return rows


# ---------------------------------------------------------------- several screenshots

def merge(reads: Sequence[ScreenRead]) -> ScreenRead:
    """Combine screenshots of one result (top and bottom of the page)."""
    reads = [r for r in reads if r.game or r.draw_no]
    if not reads:
        raise ScreenError("no TOTO or 4D result found in the screenshot")
    games = {r.game for r in reads if r.game}
    if len(games) > 1:
        raise ScreenError("these screenshots mix a TOTO and a 4D result")
    draws = {r.draw_no for r in reads if r.draw_no is not None}
    if len(draws) > 1:
        raise ScreenError(f"these screenshots show different draws: {sorted(draws)}")

    out = ScreenRead(game=games.pop() if games else None,
                     draw_no=draws.pop() if draws else None)
    dates = {r.draw_date for r in reads if r.draw_date}
    if len(dates) > 1:
        raise ScreenError("these screenshots show different draw dates")
    out.draw_date = dates.pop() if dates else None

    for r in reads:
        out.notes += r.notes
        if len(r.winning) == 6 and not out.winning:
            out.winning = r.winning
        elif 0 < len(r.winning) < 6 and not out.winning_partial:
            out.winning_partial = r.winning
        if r.additional is not None and out.additional is None:
            out.additional = r.additional
        for g, a in r.shares.items():
            if g in out.shares and out.shares[g] != a:
                raise ScreenError(f"Group {g} reads {out.shares[g]:,.0f} on one screenshot "
                                  f"and {a:,.0f} on another")
            out.shares[g] = a
        for name in ("first", "second", "third"):
            if getattr(out, name) is None:
                setattr(out, name, getattr(r, name))
        out.starter = _join_rows(out.starter, r.starter)
        out.starter_tail = r.starter_tail or out.starter_tail
        out.consolation = _join_rows(out.consolation, r.consolation)
    if len(out.starter) < 10 and out.starter_tail:
        out.starter = _head_tail(out.starter, out.starter_tail)
    out.shares = _ordered_shares(out.shares, out.notes)
    return out


def _join_rows(a: list[str], b: list[str]) -> list[str]:
    """Join two partial reads of the same section where the screenshots overlap.

    Rows read two numbers at a time, so the overlap is matched on whole pairs:
    a = [..8 starters ending 7394 8072], b = [7394 8072 8468 9574] -> 10.
    """
    if not b:
        return a
    if not a:
        return b[:10]
    if len(a) >= 10:
        return a
    for k in range(min(len(a), len(b)), 0, -1):
        if a[-k:] == b[:k]:
            return (a + b[k:])[:10]
    return (a + b)[:10]


def _head_tail(head: list[str], tail: list[str]) -> list[str]:
    """First n Starters plus last m Starters -> all 10, if they meet and agree where they overlap."""
    n, m = len(head), len(tail)
    if n + m < 10:
        return head                                     # a gap in the middle: leave it missing
    start = 10 - m                                      # position of tail[0] in the full list
    for i in range(start, n):
        if head[i] != tail[i - start]:
            raise ScreenError(f"Starter {i + 1} reads {head[i]} on one screenshot and "
                              f"{tail[i - start]} on another")
    return head[:start] + tail


# ---------------------------------------------------------------- to a draw

def read_screens(texts: Iterable[str]) -> ScreenRead:
    """OCR text of one or more screenshots of the same official result."""
    return merge([read_screen(t) for t in texts])


@dataclass
class BatchRead:
    """Screenshots for several draws, sorted to the draws on the ticket."""
    draws: dict[int, ScreenRead] = field(default_factory=dict)
    others: dict[int, ScreenRead] = field(default_factory=dict)   # draws not on this ticket
    notes: list[str] = field(default_factory=list)


def sort_by_draw(reads: Sequence[ScreenRead], wanted: Sequence[tuple[int, Optional[date]]]) -> BatchRead:
    """Put each screenshot with its draw (multi-draw tickets, one batch upload).

    A screenshot goes to the draw number it shows; if the number didn't read,
    to the ticket draw with the same date; if it shows neither (a prize table
    scrolled below the header), to the screenshot before it, because people
    screenshot the top of a result and then scroll down. Each draw's
    screenshots are then merged like any top-and-bottom pair.
    """
    by_date = {d: n for n, d in wanted if d}
    wanted_nos = [n for n, _ in wanted]
    groups: dict[int, list[ScreenRead]] = {}
    out = BatchRead()
    last: Optional[int] = None
    for i, r in enumerate(reads, 1):
        key = r.draw_no
        if key is None and r.draw_date in by_date:
            key = by_date[r.draw_date]
        if key is None:
            key = last
        if key is None and len(wanted_nos) == 1:
            key = wanted_nos[0]                  # one draw on the ticket: it can only be that one
        if key is None:
            if r.game or r.shares or r.winning:
                out.notes.append(f"Screenshot {i} doesn't show which draw it is, so it was skipped. "
                                 "Include the top of the result, with the draw number.")
            continue
        groups.setdefault(key, []).append(r)
        last = key
    for n, rs in groups.items():
        if n not in wanted_nos:
            out.notes.append(f"A screenshot shows draw {n}, which isn't on this ticket.")
            try:
                out.others[n] = merge(rs)          # still a read of the official page: kept for others
            except ScreenError:
                pass
            continue
        try:
            m = merge(rs)
        except ScreenError as e:
            out.notes.append(f"Draw {n}: {e}")
            continue
        printed = dict(wanted).get(n)
        if m.draw_date is None and printed and plausible_date(m.game, n, printed):
            m.draw_date = printed                       # the date printed on the ticket for this draw
        out.draws[n] = m
    missing = [n for n in wanted_nos if n not in out.draws]
    if missing and out.draws:
        out.notes.append("No screenshot yet for draw " + ", ".join(map(str, missing)) + ".")
    return out


def read_images(images: Iterable[bytes], recognize: Optional[Callable] = None) -> ScreenRead:
    """Screenshot bytes -> ScreenRead, via Vision OCR (P3-01)."""
    if recognize is None:
        from .ocr import recognize
    return read_screens(recognize(img).text for img in images)


def to_result(read: ScreenRead) -> ManualResult:
    """A complete read becomes a draw. Incomplete reads raise with what is missing."""
    if not read.complete:
        raise EntryError(read.prompt())
    try:
        if read.game == "toto":
            m = toto_result(read.draw_no, read.draw_date, read.winning, read.additional,
                            group_amounts=read.shares)
        else:
            m = fourd_result(read.draw_no, read.draw_date,
                             [read.first, read.second, read.third, *read.starter, *read.consolation])
    except EntryError as e:
        raise EntryError(f"the screenshot was read but does not add up: {e}") from None
    m.source = "screenshot"
    m.warnings = read.notes + m.warnings
    return m
