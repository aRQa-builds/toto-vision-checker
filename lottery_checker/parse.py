"""Parse official TOTO and 4D results pages into matcher draws.

Stdlib only (html.parser). Works on the server-rendered `.tables-wrap` block
of the official results pages (layout checked 17 Oct 2026). Every parsed draw
is cross-checked for shape; a layout change raises ParseError instead of
returning wrong numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Optional

from .fourd import FourDDraw
from .rules import rules_for
from .toto import TotoDraw


class ParseError(ValueError):
    """The page did not look like an official results block."""


@dataclass
class _Cell:
    tag: str
    classes: frozenset
    ancestors: frozenset
    wrap: int
    text: str


class _Collector(HTMLParser):
    """Collects every td/th text with its own and ancestor classes."""

    VOID = {"br", "img", "hr", "input", "meta", "link", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, frozenset]] = []
        self.cells: list[_Cell] = []
        self.wrap = -1
        self._buf: Optional[list[str]] = None

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        classes = frozenset((dict(attrs).get("class") or "").split())
        if tag == "div" and "tables-wrap" in classes:
            self.wrap += 1
        self.stack.append((tag, classes))
        if tag in ("td", "th"):
            self._buf = []

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        while self.stack:
            t, classes = self.stack.pop()
            if t in ("td", "th") and self._buf is not None:
                anc = frozenset().union(*(c for _, c in self.stack)) if self.stack else frozenset()
                text = " ".join("".join(self._buf).split())
                self.cells.append(_Cell(t, classes, anc, self.wrap, text))
                self._buf = None
            if t == tag:
                break

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


def _cells(html: str) -> list[_Cell]:
    c = _Collector()
    c.feed(html)
    c.close()
    if c.wrap < 0:
        raise ParseError("no results block (.tables-wrap) found; page layout may have changed")
    return c.cells


def _one(cells, cls) -> str:
    found = [c.text for c in cells if cls in c.classes]
    if len(found) != 1:
        raise ParseError(f"expected one '{cls}', found {len(found)}")
    return found[0]


def _draw_no(cells) -> int:
    text = _one(cells, "drawNumber")  # "Draw No. 4068"
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        raise ParseError(f"no draw number in {text!r}")
    return int(digits)


def _draw_date(cells) -> date:
    text = _one(cells, "drawDate")  # "Thu, 10 Apr 2025"
    try:
        return datetime.strptime(text, "%a, %d %b %Y").date()
    except ValueError as e:
        raise ParseError(f"unexpected draw date {text!r}") from e


def _money(text: str) -> Optional[float]:
    t = text.replace("$", "").replace(",", "").strip()
    if t in ("", "-"):
        return None
    try:
        return float(t)
    except ValueError as e:
        raise ParseError(f"unexpected amount {text!r}") from e


def _count(text: str) -> Optional[int]:
    t = text.replace(",", "").strip()
    if t in ("", "-"):
        return None
    if not t.isdigit():
        raise ParseError(f"unexpected count {text!r}")
    return int(t)


def _by_wrap(cells):
    out: dict[int, list[_Cell]] = {}
    for c in cells:
        if c.wrap >= 0:
            out.setdefault(c.wrap, []).append(c)
    return [out[k] for k in sorted(out)]


# ---------------- TOTO ----------------

@dataclass
class TotoResult:
    draw: TotoDraw
    draw_date: date
    group1_prize_pool: Optional[float]           # "Group 1 Prize" headline (may roll over)
    shares: dict[int, tuple[Optional[float], Optional[int]]] = field(default_factory=dict)  # group -> (amount, winners)


def _parse_toto_block(cells) -> TotoResult:
    draw_no = _draw_no(cells)
    win = tuple(int(_one(cells, f"win{i}")) for i in range(1, 7))
    add = int(_one(cells, "additional"))
    pool = None
    jp = [c.text for c in cells if "jackpotPrize" in c.classes]
    if jp:
        pool = _money(jp[0])

    rows = [c.text for c in cells if c.tag == "td" and "tableWinningShares" in c.ancestors]
    if len(rows) % 3:
        raise ParseError("winning-shares table is not in rows of 3")
    shares = {}
    for i in range(0, len(rows), 3):
        label, amount, winners = rows[i:i + 3]
        g = "".join(ch for ch in label if ch.isdigit())
        if not g or not 1 <= int(g) <= 7:
            raise ParseError(f"unexpected prize group {label!r}")
        shares[int(g)] = (_money(amount), _count(winners))
    if set(shares) != set(range(1, 8)):
        raise ParseError(f"expected Groups 1-7, got {sorted(shares)}")

    # Published per-share amounts feed the matcher; '-' (no winners) is left out.
    prizes = {g: amt for g, (amt, _) in shares.items() if amt is not None}
    # The draw number decides which rule set prices it (P2-01); an unknown one raises.
    draw = TotoDraw(draw_no, win, add, group_prizes=prizes, rules=rules_for("toto", draw_no))
    return TotoResult(draw, _draw_date(cells), pool, shares)


def parse_toto(html: str) -> list[TotoResult]:
    return [_parse_toto_block(b) for b in _by_wrap(_cells(html))]


# ---------------- 4D ----------------

@dataclass
class FourDResult:
    draw: FourDDraw
    draw_date: date


def _parse_fourd_block(cells) -> FourDResult:
    draw_no = _draw_no(cells)
    starter = tuple(c.text for c in cells if c.tag == "td" and "tbodyStarterPrizes" in c.ancestors)
    consol = tuple(c.text for c in cells if c.tag == "td" and "tbodyConsolationPrizes" in c.ancestors)
    draw = FourDDraw(
        draw_no,
        _one(cells, "tdFirstPrize"),
        _one(cells, "tdSecondPrize"),
        _one(cells, "tdThirdPrize"),
        starter,
        consol,
        rules=rules_for("4d", draw_no),      # P2-01: priced by the rules of its own draw
    )  # FourDDraw validates 4 digits and exactly 10 starter / 10 consolation
    return FourDResult(draw, _draw_date(cells))


def parse_fourd(html: str) -> list[FourDResult]:
    return [_parse_fourd_block(b) for b in _by_wrap(_cells(html))]
