# P6-15-D: reveal wording for a Group TOTO / iTOTO share

## 0 - Output format contract
Reply with the complete file `lottery_checker/reveal.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk. The file ends with `_as_user_entered`; keep it last.

## 1 - Scope (reveal.py only, four bounded changes)
1. New constant after `CENT`: `UNIT_PRICE_TOL = 0.10`.
2. `Reveal` (dataclass field order matters): add `units_text: Optional[str] = None` directly after `needs_review: bool`, before `official_links`.
3. `stake_check`: tolerance is `CENT` when `result.units is None`, else `UNIT_PRICE_TOL`; the match test becomes `abs(printed_price - computed) < tol + 1e-9`. Messages unchanged.
4. `build_reveal`: when `result.units` is `(kind, a, b)`, `units_text = f"Your share: {a} of {b} units ({'Group TOTO' if kind == 'group' else 'iTOTO'})"`, passed to `Reveal(..., units_text=units_text, ...)`. After the `results_source` branches (so it also survives `_as_user_entered`, which rewrites the subline), if `units_text`: `rv.subline = f"{units_text}. {rv.subline}"`. Ordinary tickets: `units_text` is `None`, subline untouched.
Headline, states, claim text and links do not change.

## 2 - Why
Frame `specs/p6-15-group-toto-frame.md` criterion 5. `TicketResult.units` was added in slice B.

## 3 - Gate
`py -3 -m pytest tests/test_reveal.py -q` (5 red now). Whole suite must stay green.

## 4 - Limits
No rounding. Do not touch `money`, `_line_view` or the attribution texts.
