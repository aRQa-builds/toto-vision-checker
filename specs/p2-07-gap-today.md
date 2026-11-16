# P2-07-H: catch-up gap fill is not blocked by "today's draw already stored"

## 0 - Output format contract
Reply with the complete file `lottery_checker/ingest.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target `lottery_checker/ingest.py` only, function `run`. The line `if draw_no is None and stored_for_date(game, today_sgt(), data_dir):` (the "today's draw already stored; no request made" return) must also require `not holes`, so it only returns when there are no holes. `holes` is already computed at the top of `run` (it is `[]` unless `game == "toto"` and `catch_up`). Change that one condition and nothing else.

Do not change any other line or function.

## 2 - Why
2026-11-16 live run of `--catch-up` made no request although draw 4233 was missing: draw 4235 was stored for that day, and the "today already stored" return ran before the hole could be fetched. On a special Friday the 21:45 run stores that day's draw, so the 22:00 catch-up would skip an older hole the same way and it would wait a week. Follow-up to P2-07-G (`specs/p2-07-gap-catchup.md`).

## 3 - Gate
`py -3 -m pytest tests/test_ingest.py -q` (red now: `test_gap_fill_runs_even_when_todays_draw_is_stored`; `test_todays_draw_stored_still_skips_when_no_hole` is the guard that must stay green).

## 4 - Limits
Normal runs (not `--catch-up`) never compute holes, so they behave as before. A normal-week Friday with no hole and Thursday stored still makes no request.
