# P6-15-A: unit share and unit stake (`lottery_checker/units.py`)

## 0 - Output format contract
Reply with the complete file `lottery_checker/units.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk. Keep the docstring and the final `UNIT_KINDS` line.

## 1 - Scope
Replace the two stub bodies (both raise now). `kind` is `"group"` or `"itoto"`; `a` and `b` are the two numbers printed on the ticket (Group TOTO `a/b` = unit k of n; iTOTO `a of b` = units bought of total units).

1. Validate first, in both functions: `kind` not in `UNIT_KINDS`, `b < 1`, `a < 1` or `a > b` raises `ValueError`.
2. `unit_share(win, kind, a, b)`: `None` in gives `None` out. Group: `win / b` (the unit number `a` does not change the share). iTOTO: `win * a / b`. No rounding.
3. `unit_stake(whole_stake, kind, a, b)`: Group: `whole_stake / b`. iTOTO: `whole_stake * a / b`. No rounding.

Do not add imports, functions or files; do not touch any other file.

## 2 - Why
Unit tickets are refused today. The owner put Group TOTO and iTOTO in v1 (2026-11-17); see `specs/p6-15-group-toto-frame.md` for the rules and the slice plan. Rounding follows the existing code: none in the maths.

## 3 - Gate
`py -3 -m pytest tests/test_units.py -q` (red now: all tests but `test_kinds`).

## 4 - Limits
Pure functions only. Wiring into `ticket_entry.py`, `ticket.py` and `reveal.py` is slices B-D.
