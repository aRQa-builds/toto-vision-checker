"""Ticket photo -> TicketDraft (P3-02).

Vision (ocr.py) gives words with boxes. This module rebuilds the ticket as the
user would type it (ticket_entry's printed layout) and hands that text to
parse_ticket, so a photo and a typed ticket go through exactly the same
checks and land on the same confirm screen (P3-03), where the user can fix
anything we misread.

Built on two real TOTO Ordinary QP tickets (22 Oct 2026, draws 4216/4217 and
4220/4221). What real photos look like, and what this handles:
- The ticket paper is printed all over with a faint "SINGAPORE POOLS"
  watermark. Vision reads bits of it everywhere: SINGAPORE, POOLS, SINGAPO,
  OOLS, COOLS, BOOLS, PUBLS, SGAPO, PO, SIN, ORE ... These are dropped.
- Rows come from word positions (OcrResult.lines()), not Vision's reading
  order: on one ticket the reading order put the last two numbers of board B
  at the very end of the text.
- A board can be split over two rows ("A. 12 13 14" / "16 26 39 QP"), its
  letter can stick to the first number ("B.04") or be missing ("10 13 26 28
  36 42" with no "A."). Numbers are taken in row order and filled into boards
  of the bet type's size; a letter starts a new board.
- Only the header-to-PRICE part is read for boards, so the purchase time and
  serial numbers below the draws are never mistaken for numbers.

4D tickets: no real photo yet. The rows are cleaned the same way and passed
through; parse_ticket already reads 4D lines. Treat 4D photo reading as
untested until the outlet trip (P0-02).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .ticket_entry import TicketDraft, parse_ticket

_WATERMARK = ("SINGAPORE", "POOLS")
# Words a ticket really prints. Never treated as watermark even when short.
_KEEP = {
    "TOTO", "4D", "ORDINARY", "SYSTEM", "ROLL", "QP", "DRAW", "PRICE", "BIG", "SML", "SMALL",
    "IBET", "I-BET", "PERMUTATIONS", "PERMUTATION", "S'OUT", "GROUP", "ITOTO", "UNIT", "UNITS",
    "NUMBER", "PURCHASED", "OF", "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN", "PM", "AM",
}
_DAY = r"(?:MON|TUE|WED|THU|FRI|SAT|SUN)"
_DRAW = re.compile(rf"\b{_DAY}\s+\d{{2}}/\d{{2}}/\d{{2}}\s+\d{{3,4}}/\d{{2}}\b", re.I)
_DRAW_NO_ONLY = re.compile(r"\b\d{4}/\d{2}\b")
_PRICE = re.compile(r"\bPRICE\s*:?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_TOTO_HEAD = re.compile(r"\b(ORDINARY|SYSTEM\s*ROLL|SYSTEM\s*(\d{1,2}))\b", re.I)
_LETTER_NUM = re.compile(r"^([A-J])[.,]\s*(\d{1,2})$", re.I)    # "B.04" stuck together
_LETTER = re.compile(r"^([A-J])[.,]$", re.I)                    # "A."
_NUM = re.compile(r"^\d{1,2}$")
LOW_CONFIDENCE = 0.80

# Vision sometimes reads a printed zero as the letter O (or one as I/l), above all
# on blurred photos: "O2", "19/1O/26", "A.O5". Inside anything that is otherwise
# digits, those letters are put back to digits. A lone "O" is left alone.
_LOOKALIKE = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})
_NUMLIKE = re.compile(r"^(?=.*\d)[\dOoIl|]{1,2}$")
_DATELIKE = re.compile(r"^(?=.*\d)[\dOoIl]{2}/[\dOoIl]{2}/[\dOoIl]{2}$")
_DRAWNOLIKE = re.compile(r"^(?=.*\d)[\dOoIl]{3,4}/[\dOoIl]{2}$")
_LETTER_NUMLIKE = re.compile(r"^([A-J])[.,]\s*((?=.*\d)[\dOoIl|]{1,2})$", re.I)
# Printed bet-type words, matched loosely: a blurred ORDINARY can come back as
# ORDlNARY or 0RDINARY.
_HEADS = ("ORDINARY", "SYSTEM")
_SPACED_DATE = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{2}\w?)")
# digits with a run of watermark letters before or after (a lone leading R is a 4D Roll, kept)
_GLUED = re.compile(r"^(?:[A-Za-z]{2,9}|[A-QS-Za-qs-z])?([\dOoIl]{1,4}(?:/[\dOoIl]{2,4}){0,2})(?:[A-Za-z]{1,9})?$")


@dataclass
class PhotoRead:
    text: str                       # the ticket as typed text: what the confirm screen edits
    draft: TicketDraft
    notes: list[str] = field(default_factory=list)


def _subsequence(small: str, big: str) -> bool:
    it = iter(big)
    return all(c in it for c in small)


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_watermark(token: str) -> bool:
    """True for bits of the SINGAPORE POOLS background print."""
    if _LETTER.match(token) or _LETTER_NUM.match(token):
        return False                 # board letter "A." / "B.04"
    t = token.upper().strip(".,:;'\"")
    if not t.isalpha() or t in _KEEP:
        return False
    for w in _WATERMARK:
        if _subsequence(t, w) or _edit_distance(t, w) <= 2:
            return True
    return len(t) <= 2               # stray F, P, S, RE: no ticket field is a lone letter pair


def fix_token(tok: str) -> str:
    """Undo O-for-0 style misreads in number-like tokens and loose bet-type words."""
    if _NUMLIKE.match(tok) or _DATELIKE.match(tok) or _DRAWNOLIKE.match(tok):
        return tok.translate(_LOOKALIKE)
    m = _LETTER_NUMLIKE.match(tok)
    if m:
        return f"{m.group(1)}.{m.group(2).translate(_LOOKALIKE)}"
    up = tok.upper().strip(".,:;")
    if len(up) >= 5:
        letters = up.replace("0", "O").replace("1", "I").replace("L", "I")
        for w in _HEADS:
            # the watermark often eats the end of the word: ORDINARY -> ORDING (live test, 22 Oct)
            if _edit_distance(letters, w) <= 1 or letters.startswith(w[:4]):
                return w
    m = _GLUED.match(tok)
    if m and up not in _KEEP and re.search(r"\d", m.group(1)) and m.group(1) != tok:
        return fix_token(m.group(1))          # "26E", "SING02": watermark letters stuck to a number
    return tok


def clean_row(row: str) -> str:
    # Vision can space out a date: "19 / 10 / 26E" -> "19/10/26E" (then the E is dropped below)
    row = _SPACED_DATE.sub(lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}", row)
    toks = [fix_token(t) for t in row.split()]
    return " ".join(t for t in toks if not is_watermark(t))


def rows_from_text(text: str) -> list[str]:
    """Rows from a saved OCR file: the '# lines' section when present (geometry
    rows from OcrResult.lines()), else the plain text lines."""
    if "\n# lines\n" in text:
        text = text.split("\n# lines\n", 1)[1]
    return [r for r in text.splitlines() if r.strip()]


def read_rows(rows: Sequence[str]) -> PhotoRead:
    rows = [clean_row(r) for r in rows]
    rows = [r for r in rows if r]
    joined = "\n".join(rows).upper()
    notes: list[str] = []

    if re.search(r"\bTOTO\b", joined):
        text = _toto_text(rows, notes)
    elif re.search(r"\b4D\b|\bBIG\b|\bSML\b", joined):
        text = "4D\n" + "\n".join(rows)
        notes.append("4D photo reading is new: check every number and stake.")
    else:
        text = "\n".join(rows)
        notes.append("Couldn't tell TOTO from 4D on this photo.")
    return PhotoRead(text, parse_ticket(text), notes)


def read_ocr(result) -> PhotoRead:
    """From an ocr.OcrResult."""
    if result.empty:
        return PhotoRead("", parse_ticket(""), ["No text found. Retake the photo: flat, well lit, "
                                                "whole ticket in the frame."])
    out = read_rows(result.lines())
    conf = result.mean_confidence
    if conf is not None and conf < LOW_CONFIDENCE:
        out.notes.append("The photo was hard to read. Check every number carefully, or retake it.")
    return out


def _toto_text(rows: list[str], notes: list[str]) -> str:
    head_i, kind, size = None, "ORDINARY", 6
    for i, r in enumerate(rows):
        m = _TOTO_HEAD.search(r)
        if m:
            head_i = i
            word = m.group(1).upper()
            if "ROLL" in word:
                kind, size = "SYSTEM ROLL", 5
            elif m.group(2):
                kind, size = f"SYSTEM {int(m.group(2))}", int(m.group(2))
            break
    price_i = next((i for i, r in enumerate(rows) if _PRICE.search(r)), None)
    draw_i = next((i for i, r in enumerate(rows) if _DRAW.search(r)), None)
    if head_i is None:
        notes.append("Bet type (ORDINARY or SYSTEM) not found; assumed ORDINARY.")
        head_i = -1
    end = min(i for i in (price_i, draw_i, len(rows)) if i is not None)

    boards: list[tuple[Optional[str], list[str], bool]] = []   # letter, numbers, quick pick
    cur_letter, cur, cur_qp = None, [], False

    def close():
        nonlocal cur_letter, cur, cur_qp
        if cur:
            boards.append((cur_letter, cur, cur_qp))
        cur_letter, cur, cur_qp = None, [], False

    for r in rows[head_i + 1:end]:
        for tok in r.replace(",", " ").split():
            m = _LETTER_NUM.match(tok)
            if m:
                close()
                cur_letter, tok = m.group(1).upper(), m.group(2)
            elif _LETTER.match(tok):
                close()
                cur_letter = tok[0].upper()
                continue
            if tok.upper() == "QP":
                if cur or not boards:
                    cur_qp = True
                else:                               # QP printed after a board just closed
                    boards[-1] = (boards[-1][0], boards[-1][1], True)
                continue
            if _NUM.match(tok):
                if len(cur) == size:
                    close()
                cur.append(f"{int(tok):02d}")
    close()

    out = ["TOTO", kind]
    used = {b[0] for b in boards if b[0]}
    spare = iter(c for c in "ABCDEFGHIJ" if c not in used)
    for letter, nums, qp in boards:
        out.append(f"{letter or next(spare)}. {' '.join(nums)}{' QP' if qp else ''}")
    if any(b[0] is None for b in boards):
        notes.append("A board letter was missing on the photo; letters were filled in.")

    draws = [m.group(0).upper() for r in rows for m in _DRAW.finditer(r)]
    if draws:
        out.append("DRAW:")
        out.extend(re.sub(r"\s+", " ", d) for d in draws)
    else:
        nums = [m.group(0) for r in rows for m in _DRAW_NO_ONLY.finditer(r)]
        if nums:
            out.append("draw " + " ".join(n.split("/")[0] for n in nums))
            notes.append("Draw dates weren't readable; only draw numbers were taken.")
    if price_i is not None:
        p = _PRICE.search(rows[price_i]).group(1)
        out.append(f"PRICE: ${p}")
    return "\n".join(out)
