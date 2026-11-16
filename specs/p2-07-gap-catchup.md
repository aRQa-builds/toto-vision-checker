# P2-07-G: Friday catch-up fetches a missing TOTO draw number

## 0 - Output format contract
Reply with the complete file `lottery_checker/ingest.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target `lottery_checker/ingest.py` only. Two changes:

1. Replace the body of `missing_draws(game, data_dir)` (stub, raises now). Return the draw numbers missing between the lowest and the highest stored draw of that game, ascending. Read the stored numbers from the `<n>.json` file names in `data_dir/draws/<game>/` (digit-only stems, as `latest_stored` does). Nothing stored, or one draw stored, returns `[]`. Numbers below the lowest stored draw are never holes (this must not become a backfill).
2. In `run`, in the `catch_up` branch only: when `game == "toto"` and `missing_draws` is not empty, do not return early, and set the requested draw to the lowest hole (`want = holes[0]`) so the existing fetch, store and "not published" NOTE path runs with the deep link. The existing early return ("yesterday's draw already stored, no special draw expected") applies only when there are no holes. With no holes, behaviour is unchanged. A non-catch-up run, `--draw`, and 4D are unchanged.

One request per run, even with several holes. No loop, no retry inside the run.

Do not change `fetch`, `store`, `official_url`, `latest_stored`, `stored_for_date`, `main` or any other function.

## 2 - Why
Draw 4233 (Mon 9 Nov 2026) is missing: both capture runs were redirected to `toto-results.singaporepools.com.sg/en/index.html` and failed with "no results block" (`logs/ingest.log`, lines 86-94). Friday's catch-up then saw yesterday's draw (4234, Thu 12 Nov) stored and made no request, so the gap stays. A special draw on any weekday other than Friday leaves the same hole. Owner chose draw-number gap detection (2026-11-16).

## 3 - Gate
`py -3 -m pytest tests/test_ingest.py -q` (red now: six `missing_draws` and gap-fill tests at the end of the file; the 25 older tests stay green).

## 4 - Acceptance after the gate is green (Lead, not Hand)
1. One manual run on Grayskull: `tools\run-ingest.cmd toto --catch-up` (or `--draw 4233`). Expect `stored draw 4233 (2026-11-09)` in `logs\ingest.log`. A PARSE FAILED or "not published" line means the redirect is still happening; report it, do not retry in a loop.
2. Web parse test (no physical bet exists for this draw): on the web checker (`http://127.0.0.1:8765`), type a TOTO ticket for draw 4233 as text, reveal it and confirm the winning numbers and date shown match the stored `data/draws/toto/4233.json`. Use any typed numbers, no photo. This proves the recovered draw is usable end to end.

## 5 - Limits
- TOTO only. 4D has no Friday catch-up and already asks for the next number by draw number; a 4D gap check is a separate item.
- `store` rewrites any draw the page returns, so a page that returns the latest draw instead of the requested one re-saves that draw (same data, new `captured_at`). Accepted for now; the requested number is never saved unless the page carries it.
- The 9 Nov redirect has no known cause. If it recurs, see `data/failed/toto/` for the saved page.
