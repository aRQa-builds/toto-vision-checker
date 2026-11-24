# P6-15-G: unit-ticket share that is not a whole cent says "about"

## Output format (read first)
Reply with the complete file `lottery_checker/reveal.py`, line 1 to the last line, in ONE fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every line you omit is deleted from disk. Copy every line you do not change byte for byte.

## 0 - Why
Owner ruling 2026-11-24 (option 1): Group TOTO and iTOTO shares are unrounded floats shown to the cent. Singapore Pools "may round" prize amounts (cl. 5.7), so a share that is not a whole cent may differ from the official payout by a few cents. Say so.

## 1 - Scope
One file: `lottery_checker/reveal.py`, function `build_reveal` only, the `elif (result.total_won or 0) > CENT:` branch (state "won"). Touch nothing else.

## 2 - Behaviour
In the "won" branch, when `result.units` is not None AND `result.total_won` is not a whole number of cents (`abs(result.total_won * 100 - round(result.total_won * 100)) > 1e-6`):
- headline is `f"You won about {money(result.total_won)}"` (instead of `f"You won {money(...)}"`);
- subline, after the existing `Staked ... across N draw(s)` text, ends with ` The official payout may differ by a few cents.` (a single space before "The", full stop at the end).
Everything else is unchanged: whole-cent shares, ordinary tickets (`result.units is None`), pending and no-win states keep their exact current text. The later `units_text` prefix step stays as is.

## 3 - Gate
`py -3 -m pytest tests/test_reveal.py -q` (the new test `test_unit_share_not_a_whole_cent_says_about` red now, all others green).
