"""Manual results entry (P4-11): the user types in a draw's result.

The free-tier fallback when no captured result is on file: the user opens the
official page from the deep link (P4-09), reads the result and types it here.
The output is an ordinary DrawRef, so check_ticket() and build_reveal() treat
it like any other draw (pass results_source="user" to build_reveal so the
screen says the numbers are the user's, not ours).

What the user enters:
- TOTO: six winning numbers and the Additional Number. Group 1-4 amounts are
  optional: a won group with no amount stays pending, never S$0. Group 5-7
  default to the fixed amounts of the draw's rule set; a typed value overrides
  them (cascade draws can change them).
- 4D: all 23 numbers, in page order: 1st, 2nd, 3rd, 10 Starter, 10 Consolation.

Input is forgiving about format (spaces, commas, "S$", thousands separators,
"+" before the Additional Number) and strict about content: wrong counts,
out-of-range or repeated TOTO numbers, and anything that is not exactly four
digits for 4D are refused with a message that says what to fix. 4D numbers
must be typed with their leading zeros ("0273", never "273"), because "273"
could be 0273 or a typo, and guessing would check the wrong number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Optional, Sequence, Union

from . import fourd, toto
from .rules import RulesError, rules_for
from .ticket import DrawRef


class EntryError(ValueError):
    """The typed result cannot be used; the message says what to fix."""


@dataclass
class ManualResult:
    ref: DrawRef
    warnings: list[str] = field(default_factory=list)
    source: str = "user"


# ---------------------------------------------------------------- text helpers

_ADD = re.compile(r"\+|\badd(?:itional)?(?:\s+no\.?|\s+number)?\b[:\s]*", re.I)


def parse_amount(text: Union[str, float, int, None]) -> Optional[float]:
    """'S$68,513' -> 68513.0; blank, '-' or None -> None."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        v = float(text)
    else:
        s = text.strip().replace("S$", "").replace("$", "").replace(",", "").strip()
        if s in ("", "-", "—"):
            return None
        try:
            v = float(s)
        except ValueError:
            raise EntryError(f"{text!r} is not an amount") from None
    if v <= 0:
        raise EntryError(f"amount must be more than 0, got {text!r}")
    return v


def parse_toto_numbers(text: str) -> tuple[list[int], Optional[int]]:
    """'2 15 19 20 27 30 + 5' -> ([2, 15, 19, 20, 27, 30], 5).

    The Additional Number follows '+' or the word 'Additional'. Without a
    marker, a seventh number is taken as the Additional Number.
    """
    parts = _ADD.split(text, maxsplit=1)
    main = [int(t) for t in re.findall(r"\d+", parts[0])]
    if len(parts) == 2:
        extra = [int(t) for t in re.findall(r"\d+", parts[1])]
        if len(extra) != 1:
            raise EntryError(f"expected one Additional Number after '+', got {len(extra)}")
        return main, extra[0]
    if len(main) == 7:
        return main[:6], main[6]
    return main, None


def parse_fourd_numbers(text: str) -> list[str]:
    """Every 4-digit token, leading zeros kept. Anything else is refused.

    Digits glued to letters are labels, not numbers ("1st", "2nd", "3rd"), so
    a copy of the prize block with its headings works as typed.
    """
    tokens = re.findall(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])", text)
    bad = [t for t in tokens if len(t) != 4]
    if bad:
        raise EntryError(
            f"4D numbers have exactly 4 digits, including leading zeros (0273, not 273): "
            f"check {', '.join(bad)}")
    return tokens


# ---------------------------------------------------------------- TOTO

def toto_result(draw_no: int, draw_date: date, numbers: Union[str, Sequence[int]],
                additional: Optional[int] = None,
                group_amounts: Optional[Mapping[int, Union[str, float, None]]] = None) -> ManualResult:
    if isinstance(numbers, str):
        numbers, parsed_add = parse_toto_numbers(numbers)
        additional = parsed_add if additional is None else additional
    numbers = list(numbers)
    if len(numbers) != 6:
        raise EntryError(f"TOTO needs 6 winning numbers, got {len(numbers)}")
    if additional is None:
        raise EntryError("enter the Additional Number too (after '+')")

    amounts: dict[int, float] = {}
    for g, raw in (group_amounts or {}).items():
        g = int(g)
        if not 1 <= g <= 7:
            raise EntryError(f"there is no Group {g}; groups run 1 to 7")
        v = parse_amount(raw)
        if v is not None:
            amounts[g] = v

    rules = _rules("toto", draw_no)
    try:
        draw = toto.TotoDraw(draw_no, tuple(numbers), additional, amounts, rules)
    except toto.TotoError as e:
        raise EntryError(_toto_message(e)) from None

    warnings = []
    priced = sorted(amounts)
    for a, b in zip(priced, priced[1:]):
        if amounts[a] < amounts[b]:
            warnings.append(f"Group {a} ({amounts[a]:,.0f}) is less than Group {b} "
                            f"({amounts[b]:,.0f}). Please double-check both.")
    for g in (5, 6, 7):
        fixed = rules.fixed_prizes.get(g)
        if g in amounts and fixed is not None and amounts[g] != fixed:
            warnings.append(f"Group {g} is usually S${fixed:,.0f}; you entered "
                            f"S${amounts[g]:,.0f}. Fine after a cascade, otherwise check it.")
    missing = [g for g in (1, 2, 3, 4) if g not in amounts]
    if missing:
        warnings.append("No amount entered for " + ", ".join(f"Group {g}" for g in missing)
                        + ". A win in those groups will show as pending until you add it.")
    return ManualResult(DrawRef(draw, draw_date), warnings)


def _toto_message(e: Exception) -> str:
    msg = str(e)
    if "duplicate" in msg:
        return "a number appears twice; each winning number is different"
    if "outside 1-49" in msg:
        return "TOTO numbers run from 1 to 49: " + msg.split(":")[-1].strip()
    if "repeats a winning number" in msg:
        return "the Additional Number cannot be one of the six winning numbers"
    return msg


# ---------------------------------------------------------------- 4D

def fourd_result(draw_no: int, draw_date: date, numbers: Union[str, Sequence[str]]) -> ManualResult:
    if isinstance(numbers, str):
        nums = parse_fourd_numbers(numbers)
    else:
        nums = [str(n).strip() for n in numbers]
        bad = [n for n in nums if len(n) != 4 or not n.isdigit()]
        if bad:
            raise EntryError(f"4D numbers have exactly 4 digits, including leading zeros: check {', '.join(bad)}")
    if len(nums) != 23:
        raise EntryError(f"4D needs 23 numbers (1st, 2nd, 3rd, 10 Starter, 10 Consolation), "
                         f"got {len(nums)}. Enter only the prize numbers, not the draw number or date.")
    rules = _rules("4d", draw_no)
    draw = fourd.FourDDraw(draw_no, nums[0], nums[1], nums[2],
                           tuple(nums[3:13]), tuple(nums[13:23]), rules)
    warnings = []
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    if dupes:
        warnings.append(f"{', '.join(dupes)} appears more than once. That is rare; "
                        "please check against the official result.")
    return ManualResult(DrawRef(draw, draw_date), warnings)


def _rules(game: str, draw_no: int):
    if not isinstance(draw_no, int) or draw_no < 1:
        raise EntryError(f"draw number must be a positive whole number, got {draw_no!r}")
    try:
        return rules_for(game, draw_no)
    except RulesError:
        raise EntryError(f"draw {draw_no} is older than the rules this checker knows; "
                         "it cannot be priced correctly") from None
