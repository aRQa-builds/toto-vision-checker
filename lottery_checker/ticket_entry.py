"""Manual ticket entry (P4-01): the user types what is printed on the ticket.

This is also the shared ticket model. The OCR ticket parser (P3-02) will
produce the same TicketDraft from Vision text, and the confirm-and-correct
screen (P3-03) edits a TicketDraft. So the typed format follows the printed
ticket line for line (rules reference v0.3, "Printed ticket layout"), and a
person can copy what they see:

    TOTO                                4D
    ORDINARY                            IBET
    A. 03 11 19 25 33 47 QP             A 1234 BIG $10 SML $10
    B. 05 09 21 30 41 44                  24 PERMUTATIONS
    DRAW:                               B R888 BIG $1
    THU 24/09/26  4220/26               C 5950 BIG S'OUT SML $2*
    MON 28/09/26  4221/26               DRAW: WED 21/10/26 5551/26
    PRICE: $4.00                        PRICE: $13.00

Short forms work too: "1 2 3 4 5 6 7" is a System 7 (TOTO kind follows the
count: 5 = System Roll, 6 = Ordinary, 7-12 = System), "1234 B2 S1" is a 4D
Ordinary, "draw 4220 4221" lists draws.

Printed markers honoured: QP (ignored for matching), S'OUT (that side was
sold out, stake 0), "*" (accepted at a lower stake; the printed amount is
what was accepted and what pays), "n PERMUTATIONS" (checked against ours).
4D Roll prints under ORDINARY with an R in the number, so the R decides Roll.

Every problem is reported per line in `errors` so the confirm screen can
point at it; nothing is silently dropped. Group TOTO and iTOTO unit tickets
are recognised but not yet priced per unit, so they are marked unsupported
rather than shown with a whole-entry amount.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional, Union

from . import fourd, toto
from .ticket import DrawRef, TicketResult, check_ticket

Entry = Union[toto.TotoEntry, fourd.FourDEntry]

_DRAW_LINE = re.compile(r"(?:\b(\d{2})/(\d{2})/(\d{2})\s+)?\b(\d{3,4})/(\d{2})\b")
_DRAW_WORD = re.compile(r"\bdraws?\b\s*:?\s*((?:\d{3,4}[\s,]*)+)", re.I)
_PRICE = re.compile(r"\bPRICE\s*:?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_PERMS = re.compile(r"\b(\d{1,2})\s+PERMUTATIONS?\b", re.I)
_UNITS = re.compile(r"UNIT\s+NUMBER\s*:?\s*(\d+)\s*/\s*(\d+)|UNITS\s+PURCHASED\s*:?\s*(\d+)\s+of\s+(\d+)", re.I)
_BOARD_LETTER = re.compile(r"^\s*([A-J])[.)]?\s+(?=[\dR])", re.I)
_FOURD_NUM = re.compile(r"(?<![\w$\-/:.])([0-9R]{4})(?![\w\-/:.])", re.I)
_SIDE = re.compile(r"\b(BIG|SML|SMALL|B|S)(?![A-Za-z'])\s*:?\s*(S'?OUT|\$?\s*\d+\*?)", re.I)
_TOTO_HEADER = re.compile(
    r"^\s*(?:GROUP\s+TOTO\s*-\s*|ITOTO\s*-\s*)?(ORDINARY|SYSTEM\s+ROLL|SYSTEM\s*(\d{1,2}))\s*$", re.I)
_TOTO_INLINE = re.compile(
    r"^\s*(?:[A-J][.)]?\s+)?(ORDINARY|SYSTEM\s*ROLL|ROLL|SYSTEM\s*(\d{1,2}))\s*:?\s*(?=\d)", re.I)
_FOURD_HEADER = re.compile(r"^\s*(ORDINARY|SYSTEM|IBET|I-BET)\s*$", re.I)


@dataclass
class LineError:
    line_no: int          # 1-based, as the user sees it
    text: str
    message: str


@dataclass
class TicketDraft:
    game: Optional[str] = None
    entries: list[Entry] = field(default_factory=list)
    entry_lines: list[int] = field(default_factory=list)      # source line of each entry
    draws: list[tuple[int, Optional[date]]] = field(default_factory=list)
    printed_price: Optional[float] = None
    units: Optional[tuple[int, int]] = None                  # Group TOTO 3/3, iTOTO 1 of 28
    quick_pick: bool = False
    errors: list[LineError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def draw_numbers(self) -> list[int]:
        return [n for n, _ in self.draws]

    @property
    def supported(self) -> bool:
        return self.units is None

    @property
    def ready(self) -> bool:
        """Good enough to check: bets, at least one draw, no errors, supported."""
        return bool(self.entries) and bool(self.draws) and not self.errors and self.supported

    def problems(self) -> list[str]:
        out = [f"Line {e.line_no}: {e.message}" for e in self.errors]
        if not self.entries:
            out.append("No bets found. Type each board as printed, one per line.")
        if not self.draws:
            out.append("No draw found. Add the DRAW line, e.g. \"THU 24/09/26 4220/26\" or \"draw 4220\".")
        if not self.supported:
            out.append("Group TOTO and iTOTO unit tickets are not supported yet: "
                       "the payout per unit is not worked out.")
        return out

    def stake(self) -> int:
        """Our stake for the whole ticket, all draws: what PRICE should say."""
        per_draw = sum(e.stake if isinstance(e, toto.TotoEntry) else e.cost_per_draw
                       for e in self.entries)
        return per_draw * max(len(self.draws), 1)

    def check(self, lookup: Callable[[int], Optional[DrawRef]]) -> TicketResult:
        """Grade against the draws `lookup` can supply (stored capture, typed or screenshot)."""
        if not self.ready:
            raise ValueError("ticket not ready: " + "; ".join(self.problems()))
        refs, missing = [], []
        for n, _ in self.draws:
            ref = lookup(n)
            (refs if ref is not None else missing).append(ref if ref is not None else n)
        if missing:
            raise LookupError(f"no result on file for draw(s) {missing}; "
                              "open the official page and add it")
        return check_ticket(self.entries, refs)


# ---------------------------------------------------------------- parsing

def parse_ticket(text: str) -> TicketDraft:
    d = TicketDraft()
    lines = text.splitlines()
    d.game = _detect_game(lines)
    if d.game is None:
        d.errors.append(LineError(1, lines[0] if lines else "", "can't tell if this is TOTO or 4D; "
                                  "start with a line saying TOTO or 4D"))
        return d

    toto_kind: Optional[str] = None        # from a header line: "ordinary", "system", "roll"
    toto_size: Optional[int] = None
    fourd_kind = "ordinary"
    pending: Optional[tuple[int, str, list[int]]] = None   # TOTO System board wrapping lines

    def flush():
        nonlocal pending
        if pending:
            _add_toto(d, *pending, kind=toto_kind, size=toto_size)
            pending = None

    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        up = line.upper()

        m = _UNITS.search(line)
        if m:
            k, n = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            d.units = (int(k), int(n))
            continue
        m = _PRICE.search(line)
        if m:
            d.printed_price = float(m.group(1).replace(",", ""))
            continue
        if _read_draws(d, line, i):
            flush()
            continue
        if up in ("TOTO", "4D", "DRAW:", "DRAW"):
            continue

        if d.game == "toto":
            if "GROUP TOTO" in up or "ITOTO" in up:
                d.units = d.units or (0, 0)            # unit ticket; counts come on a later line
            h = _TOTO_HEADER.match(line)
            if h:
                flush()
                toto_kind, toto_size = _toto_kind(h.group(1), h.group(2))
                continue
            line_kind = line_size = None
            h = _TOTO_INLINE.match(line)
            if h:                                       # typed "System 7: 1 2 3 ..." on one line
                flush()
                line_kind, line_size = _toto_kind(h.group(1), h.group(2))
                nums, _, junk = _toto_numbers(line[h.end():])
                if nums is None or junk:
                    d.errors.append(LineError(i, raw, "couldn't read the numbers after the bet type"))
                else:
                    _add_toto(d, i, raw, nums, kind=line_kind, size=line_size)
                continue
            nums, letter, junk = _toto_numbers(line)
            if nums is None:
                continue                                # notice, timestamp, serial: not a board
            if "QP" in up.split():
                d.quick_pick = True
            if letter is None and pending and toto_size and len(pending[2]) < toto_size:
                pending[2].extend(nums)                 # System 12 wraps over two lines
                continue
            flush()
            if junk:
                d.errors.append(LineError(i, raw, f"don't understand {', '.join(junk)}"))
                continue
            pending = (i, raw, nums)

        else:
            if _FOURD_HEADER.match(line):
                fourd_kind = up.replace("-", "").lower()
                continue
            m = _PERMS.search(line)
            if m:
                _check_perms(d, int(m.group(1)), i)
                continue
            _add_fourd(d, i, raw, line, fourd_kind)
    flush()

    if d.units == (0, 0):
        d.warnings.append("Group TOTO or iTOTO ticket: add the UNIT NUMBER line too.")
    if d.printed_price is not None and d.ready:
        ours = d.stake()
        if abs(ours - d.printed_price) > 0.005:
            d.warnings.append(f"PRICE says S${d.printed_price:,.2f} but these bets come to "
                              f"S${ours:,.2f}. Check the amounts and the number of draws.")
    return d


def _toto_kind(word: str, size: Optional[str]) -> tuple[str, int]:
    word = word.upper()
    if word == "ORDINARY":
        return "ordinary", 6
    if "ROLL" in word:
        return "roll", 5
    return "system", int(size)


def _detect_game(lines: list[str]) -> Optional[str]:
    for line in lines[:4]:
        up = line.strip().upper()
        if up.startswith("TOTO") or "GROUP TOTO" in up or "ITOTO" in up:
            return "toto"
        if up.startswith("4D"):
            return "4d"
    text = "\n".join(lines).upper()
    if re.search(r"\b(BIG|SML)\b|\b[0-9R]{4}\s+[BS]\s*\$?\d", text):
        return "4d"
    if any((_toto_numbers(l)[0] or []) for l in lines):
        return "toto"
    return None


def _read_draws(d: TicketDraft, line: str, i: int) -> bool:
    found = False
    for m in _DRAW_LINE.finditer(line):
        dd, mm, yy, num, ny = m.groups()
        when = None
        if dd:
            try:
                when = date(2000 + int(yy), int(mm), int(dd))
            except ValueError:
                d.errors.append(LineError(i, line, f"{dd}/{mm}/{yy} is not a date"))
            if when and when.year % 100 != int(ny):
                d.warnings.append(f"Line {i}: draw {num}/{ny} and date {dd}/{mm}/{yy} are in different years.")
        _add_draw(d, int(num), when)
        found = True
    if not found:
        m = _DRAW_WORD.search(line)
        if m:
            for num in re.findall(r"\d{3,4}", m.group(1)):
                _add_draw(d, int(num), None)
            found = True
    return found


def _add_draw(d: TicketDraft, num: int, when: Optional[date]) -> None:
    if num not in d.draw_numbers:
        d.draws.append((num, when))


def _toto_numbers(line: str) -> tuple[Optional[list[int]], Optional[str], list[str]]:
    """Board numbers on a TOTO line, its letter, and anything unreadable.

    Returns (None, None, []) for lines that are not boards (notices, the
    timestamp, serial numbers): those carry long or hyphenated digit runs, or
    fewer than two small numbers.
    """
    m = _BOARD_LETTER.match(line)
    letter = m.group(1).upper() if m else None
    body = line[m.end():] if m else line
    body = re.sub(r"\bQP\b", " ", body, flags=re.I)
    if re.search(r"\d{3,}|\d[-:/]\d", body):
        return None, None, []
    tokens = body.replace(",", " ").split()
    nums = [int(t) for t in tokens if t.isdigit()]
    junk = [t for t in tokens if not t.isdigit()]
    if len(nums) < 2:
        return None, None, []
    return nums, letter, junk


def _add_toto(d: TicketDraft, i: int, raw: str, nums: list[int], kind: Optional[str], size: Optional[int]):
    n = len(nums)
    if kind is None:
        kind = {5: "roll", 6: "ordinary"}.get(n, "system" if 7 <= n <= 12 else None)
    if size and n != size:
        d.errors.append(LineError(i, raw, f"expected {size} numbers for this bet type, found {n}"))
        return
    if kind is None:
        d.errors.append(LineError(i, raw, f"a TOTO board has 5, 6 or 7-12 numbers, found {n}"))
        return
    try:
        d.entries.append(toto.TotoEntry(kind, tuple(nums)))
        d.entry_lines.append(i)
    except toto.TotoError as e:
        d.errors.append(LineError(i, raw, _plain(str(e))))


def _add_fourd(d: TicketDraft, i: int, raw: str, line: str, kind: str) -> None:
    m = _BOARD_LETTER.match(line)
    body = line[m.end():] if m else line
    nums = _FOURD_NUM.findall(body.split("BIG")[0] if "BIG" in body.upper() else body)
    nums = [n for n in nums if any(c.isdigit() for c in n)]
    if not nums:
        if re.search(r"\d", body) and not re.search(r"\d{5,}|\d-\d|\d[:/]\d", body):
            d.errors.append(LineError(i, raw, "no 4-digit number found; type it with leading zeros"))
        return                                           # timestamp, serials: not a board
    number = nums[0].upper()
    big = small = 0
    reduced = sold_out = False
    sides = _SIDE.findall(body[body.upper().find(number) + 4:])
    if not sides:
        d.errors.append(LineError(i, raw, "no stake found; add BIG and/or SML amounts, e.g. BIG $1"))
        return
    for side, val in sides:
        v = val.upper().replace("$", "").replace(" ", "")
        if "OUT" in v:
            amount, sold_out = 0, True
        else:
            reduced = reduced or v.endswith("*")
            amount = int(v.rstrip("*"))
        if side.upper() in ("BIG", "B"):
            big = amount
        else:
            small = amount
    if sold_out:
        d.warnings.append(f"Line {i}: {number} has a sold-out side (S'OUT); that side is not counted.")
    if reduced:
        d.warnings.append(f"Line {i}: {number} was accepted at a lower stake (*); "
                          "the printed amount is what counts.")
    if big + small == 0:
        d.warnings.append(f"Line {i}: {number} was fully sold out, so it is not a bet.")
        return
    bet_kind = "roll" if "R" in number else kind
    try:
        d.entries.append(fourd.FourDEntry(bet_kind, number, big, small))
        d.entry_lines.append(i)
    except fourd.FourDError as e:
        d.errors.append(LineError(i, raw, _plain(str(e))))


def _check_perms(d: TicketDraft, printed: int, i: int) -> None:
    if not d.entries or not isinstance(d.entries[-1], fourd.FourDEntry):
        return
    ours = d.entries[-1].perms
    if d.entries[-1].kind in ("system", "ibet") and printed != ours:
        d.warnings.append(f"Line {i}: ticket says {printed} permutations, "
                          f"{d.entries[-1].number} has {ours}. Check the number.")


def _plain(msg: str) -> str:
    msg = re.sub(r"^(ordinary|system|roll|ibet) entry:?\s*", "", msg)
    if "duplicate" in msg:
        return "a number appears twice on this board"
    if "outside 1-49" in msg:
        return "TOTO numbers run from 1 to 49" + msg.split("1-49")[-1]
    if "one permutation" in msg:
        return msg.replace("not allowed as", "can't be played as")
    return msg
