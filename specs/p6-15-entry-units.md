# P6-15-C: accept unit tickets in `ticket_entry.py` and grade them as the holder's share

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_entry.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk. The file ends with the function `_plain`; keep it as the last function.

## 1 - Scope (one file, five bounded changes; touch nothing else)
1. Imports: `from .ticket import DrawRef, TicketResult, check_ticket, scale_to_units` and a new line `from .units import unit_stake`.
2. `TicketDraft` gets a field `unit_kind: Optional[str] = None` (after `units`): `"group"` or `"itoto"`.
3. In `parse_ticket`, where `_UNITS` matches and `d.units` is set: also set `d.unit_kind = "group"` if `m.group(1)` matched (UNIT NUMBER k/n), else `"itoto"` (UNITS PURCHASED u of N).
4. `supported`: True when `units is None`; otherwise True only when `unit_kind` is set and `1 <= a <= b` for `units == (a, b)`. So `(0, 0)` (header, no unit line) and `4/3` are unsupported, hence not `ready`. Replace the `problems()` text for the unsupported case with: `Group TOTO or iTOTO ticket: the unit line is missing or not valid. Add it as printed, e.g. UNIT NUMBER: 1/3 or NUMBER OF UNITS PURCHASED: 1 of 28.` Keep the existing `(0, 0)` warning line.
5. PRICE check at the end of `parse_ticket`: for a unit ticket (`d.units is not None`), `ours = unit_stake(d.stake(), d.unit_kind, *d.units)` and the tolerance is `0.10`; for every other ticket `ours = d.stake()` and the tolerance stays `0.005`. The warning text is unchanged. `stake()` itself does not change.
6. `check()`: after `check_ticket(...)`, if `self.units is not None` return `scale_to_units(result, self.unit_kind, *self.units)`, else the result unchanged.

## 2 - Why
Frame `specs/p6-15-group-toto-frame.md`, criteria 1, 4, 6, 7. `units.py` and `ticket.scale_to_units` (slices A, B) hold the maths.

## 3 - Gate
`py -3 -m pytest tests/test_ticket_entry.py -q` (4 red now). Then the whole suite must stay green.

## 4 - Limits
Ordinary and System tickets and all 4D paths behave exactly as before. No rounding anywhere. Do not edit the docstring (a later slice does).
