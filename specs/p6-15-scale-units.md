# P6-15-B: `scale_to_units` turns a whole-entry result into the holder's share

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk. Keep the final line `# end of ticket.py`.

## 1 - Scope
Target `lottery_checker/ticket.py` only. Replace the body of `scale_to_units(result, kind, a, b)` (stub, raises now) and add one import line, `from .units import unit_share, unit_stake`, with the other relative imports (`dataclasses.replace` is also needed: add `replace` to the existing `from dataclasses import ...` line). `TicketResult` already has the new `units` field; do not change any class.

The function returns a NEW `TicketResult` and never changes its input:
- every `Line` is copied with `stake = unit_stake(ln.stake, kind, a, b)` and `won = unit_share(ln.won, kind, a, b)` (a `None` win stays `None`); `detail`, `unpriced_groups` and everything else are kept;
- `total_stake` is the sum of the new line stakes;
- `total_won` is `None` if any new line's `won` is `None`, else the sum of the new `won` values;
- `draw_dates` is kept, and `units = (kind, a, b)`.
A bad `kind`, `a` or `b` raises `ValueError` (the two `units.py` functions already do this; let it through).

Do not change `check_ticket` or any other function.

## 2 - Why
Group TOTO and iTOTO tickets pay the holder a share of the whole-entry win (frame: `specs/p6-15-group-toto-frame.md`). `units.py` (slice A) has the maths; this applies it to a graded ticket so the reveal, history and wallet all read one scaled result.

## 3 - Gate
`py -3 -m pytest tests/test_ticket.py -q` (red now: the four `scale` tests at the end; everything else stays green).

## 4 - Limits
No rounding. The existing `check_ticket` result for an ordinary ticket is unchanged and has `units = None`.
