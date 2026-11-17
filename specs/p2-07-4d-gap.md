# P2-07-J: `--catch-up` fills 4D draw-number holes too

## 0 - Output format contract
Reply with the complete file `lottery_checker/ingest.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target `lottery_checker/ingest.py` only, function `run`. Two changes:

1. The first line, `holes = missing_draws(game, data_dir) if game == "toto" and catch_up else []`, becomes `holes = missing_draws(game, data_dir) if catch_up else []` (`missing_draws` already works for any game).
2. Directly after the existing `if catch_up and not holes and stored_for_date(...)` early-return block, add: if `catch_up` and `game == "4d"` and `not holes`, print `[4d] catch-up: no gaps; no request made` and `return 0`. Without it a 4D catch-up with no hole would fall through and ask for the next draw number.

Everything else is unchanged: the `want = holes[0]` line already makes a 4D hole request go out by draw number; a 4D run without `--catch-up` still asks for `next_fourd_draw`; TOTO behaviour is unchanged.

Do not change any other line or function.

## 2 - Why
A 4D draw that fails both capture runs (Wed, Sat, Sun) is never retried: the next run asks for the highest stored number plus one, so the hole stays forever. TOTO got the Friday gap fill in P2-07-G/H; 4D has none. Owner chose to extend it (2026-11-17).

## 3 - Gate
`py -3 -m pytest tests/test_ingest.py -q` (red now: `test_4d_catch_up_fetches_the_lowest_hole_by_number`, `test_4d_catch_up_makes_no_request_without_a_hole`; `test_4d_normal_run_still_asks_for_the_next_draw` is a guard). All other tests stay green.

## 4 - Limits
One request per run, lowest hole first, never below the lowest stored draw (not a backfill). The schedule entry for 4D catch-up is a separate PowerShell edit by Lead, not Hand.
