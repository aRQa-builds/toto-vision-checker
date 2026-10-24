# After-draw results capture: schedule and guardrails (17 Oct 2026)

Decision: free, non-monetised public checker. Results are captured once per draw from the official page, cited to Singapore Pools, and not claimed as ours. Written permission has been requested. If Singapore Pools objects, switch the kill switch off and stay on the screenshot flow.

## What runs

```
python -m lottery_checker.ingest 4d     # latest 4D draw
python -m lottery_checker.ingest toto   # latest TOTO draw
python -m lottery_checker.ingest toto --draw 4068   # one specific draw (manual use only)
python -m lottery_checker.ingest toto --catch-up    # Friday: fetch only if no draw stored for yesterday or today
```

Environment:
- `TOTO_INGEST_ENABLED=1` turns capture on. Anything else, or unset, means no request is made (kill switch).
- `TOTO_CONTACT=results@zenqi.cc` goes into the user agent so Singapore Pools can reach us. Required.

Output, under `data/` (or `--data <folder>`):
- `raw/<game>/<draw>.html`: the page as fetched, for our records only.
- `draws/<game>/<draw>.json`: parsed draw with `source`, `official_url` and `attribution`.

## Schedule (Singapore time)

Draws: 4D Wed, Sat, Sun 6:30 pm; TOTO Mon, Thu 9:30 pm. One run after results go up, one retry 15 minutes later. The retry makes no request if the draw is already stored.

Special TOTO draws (P0-04, added 21 Oct 2026 as P2-07): in 2026 the New Year (4144, Fri 2 Jan), Reunion (4156, Fri 13 Feb), Hong Bao (4160, Fri 27 Feb) and National Day (4206, Fri 7 Aug) draws were ordinary TOTO draws moved to a Friday in place of that week's Thursday, with the next draw number in sequence. Two Friday tasks (21:45 and 22:00) run with `--catch-up`. On a normal week Thursday's draw is already stored, so they make no request. On a special week the Thursday runs find only Monday's draw, so the Friday run fetches once and stores the special draw. The same run also recovers a normal Thursday draw if both Thursday runs failed. A special draw on any other weekday is still not covered: use a manual `--draw` run or the screenshot flow.

Linux cron (Grayskull, if it runs Linux):
```
CRON_TZ=Asia/Singapore
TOTO_INGEST_ENABLED=1
TOTO_CONTACT=results@zenqi.cc
45 18 * * 0,3,6  cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest 4d   >> logs/ingest.log 2>&1
0  19 * * 0,3,6  cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest 4d   >> logs/ingest.log 2>&1
45 21 * * 1,4    cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest toto >> logs/ingest.log 2>&1
0  22 * * 1,4    cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest toto >> logs/ingest.log 2>&1
45 21 * * 5      cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest toto --catch-up >> logs/ingest.log 2>&1
0  22 * * 5      cd /path/to/Toto_Vision_Checker && python3 -m lottery_checker.ingest toto --catch-up >> logs/ingest.log 2>&1
```

Windows 11 (Grayskull): use the two scripts in `tools\`.
- `run-ingest.cmd 4d|toto [--catch-up]` sets `TOTO_INGEST_ENABLED=1` and `TOTO_CONTACT=results@zenqi.cc`, runs one capture and appends to `logs\ingest.log`.
- `setup-schedule.ps1` registers six tasks under `\ZenQi\TotoChecker\` in Task Scheduler at the times above. It warns if the PC is not on UTC+08:00 (task times are local). Missed runs (PC asleep) start when it wakes.
- Kill switch: `setup-schedule.ps1 -Disable` (resume with `-Enable`, delete with `-Remove`), or set `TOTO_INGEST_ENABLED=0` in `run-ingest.cmd`.

First-time setup on Grayskull:
1. Install Python 3.10+ (python.org, tick "Add to PATH"; the `py` launcher is used if present).
2. In the project folder: `py -3 -m pip install pytest` then `py -3 -m pytest -q` (expect 216 passed as of 21 Oct 2026).
3. Make sure results@zenqi.cc exists and someone reads it (P2-05).
4. `powershell -ExecutionPolicy Bypass -File tools\setup-schedule.ps1`
5. Check `logs\ingest.log` after the next draw.

Not covered by the schedule: a special TOTO draw on a day other than Friday (none seen in 2026 so far; March to early July not yet checked). Use the screenshot flow or a manual `--draw` run.

## Guardrails (built into the code)

| Guardrail | Where |
|---|---|
| Kill switch, off by default | `enabled()`, `TOTO_INGEST_ENABLED` |
| One request per run, no in-run retries, 20 s timeout | `fetch()` |
| No request if the draw is already stored | `already_stored()`, `stored_for_date()` |
| Honest user agent with contact, never a browser string | `user_agent()` |
| Attribution and official link on every record | `ATTRIBUTION`, `official_url()` |
| Loud failure on layout change, never wrong numbers | `parse.py` raises `ParseError`; exit code 2 |
| No bulk history, no other endpoints | only the two results pages are called |

## Attribution text (show on every result screen)

> Results: Singapore Pools (singaporepools.com.sg). We do not own this data. The official results published by Singapore Pools are final. [Official result for this draw ↗]

Also in the site footer: "Not affiliated with Singapore Pools."

## Not done here
- Backfill of history (P2-04) stays on hold.
- No public results API or feed.
- No ads or paid tier while this capture runs without permission.
