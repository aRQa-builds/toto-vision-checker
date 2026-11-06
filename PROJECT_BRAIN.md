# PROJECT_BRAIN — Toto Vision Checker
_LLM context file. Dense. No fluff. Written for cold re-entry._

## Identity
- **What it is**: Free public SG Toto/4D ticket checker: scan ticket (Google Vision), match against draw, show payout.
- **Stack**: Python 3.10+ stdlib core (`lottery_checker/`), pytest; FastAPI web checker (`web/index.html` Arcade Drum UI, PWA) on Grayskull, live locally.
- **Deploy**: toto.zenqi.cc LIVE since 22 Oct 2026 (Cloudflare Tunnel sakura-hud, served from Grayskull); capture runs on Grayskull (Win 11 64-bit, Task Scheduler).
- **Home**: D:\SakuraHydra\HavenPalms\Toto_Vision_Checker (mirror: claude.ai project "Toto OCR Check").
- **Remote**: https://github.com/aRQa-builds/toto-vision-checker (PUBLIC, `main`, since 2026-10-25). Ticket photos, captured Singapore Pools pages (`tests/fixtures/*.jpg`, `*.html`, `screens/`) and `data/` are git-ignored and stay local; never add them. Public repo: no secrets, no `.env`.
- **Version**: v0.2 (matcher + capture + optional accounts, 558 pytest + 9 node tests).

## Architecture Decisions
- Toto Groups 1-4 priced only from published draw amounts; 5-7 fixed ($50/$25/$10), published value overrides (cascade).
- 4D stakes: Roll ×10, System ×perms, iBet once (Singapore Pools bet slip page).
- Results: after-draw capture of official page, 1 request + 1 retry, credited, "we do not own this data" (user's risk decision 2026-10-17). Screenshot/typing flow kept as fallback.
- No iframe/CORS route: official page blocks framing.
- Accounts (P4-04, optional): email magic link, server-side sessions, SQLite `data/accounts.db`; history = bets + outcome only, no serials/photos/ticket text, kept to 31 Dec of next year, user can delete. Sign-in mail via Cloudflare Email Service from login@zenqi.cc. Paid tier, ads, Play listing ON HOLD until permission.

## Key Patterns
- `toto.py`/`fourd.py` matchers; `parse.py` stdlib HTML parser; `ingest.py` capture.
- Deep link: `?sppl=base64("DrawNumber=N")` (Toto `/en/product/sr/Pages/toto_results.aspx`, 4D `/en/product/Pages/4d_results.aspx`).
- Data: `data/raw/<game>/<n>.html`, `data/draws/<game>/<n>.json` (with attribution).

## Rules
- Never fetch Singapore Pools beyond the scheduled capture; honest UA `ZenQiTotoChecker` + results@zenqi.cc.
- Kill switch: `TOTO_INGEST_ENABLED`, or `tools\setup-schedule.ps1 -Disable`.
- No public results API, no bulk backfill, no money while unpermitted.
- Parser fails loudly on layout change; never guess numbers.
- Roadmap in standard P/M/ID traffic-light format, mobile table with Blocker → next column.

## Watch Points
- Python changes load at server start only. Restart the live web checker by ending the python process (the keep-alive loop restarts it) or `Start-ScheduledTask`. `tools\setup-web.ps1` now registers the task before stopping anything (fixed 5 Nov 2026, not yet run live), but still run it from an elevated window: a task registered elevated (-AtStartup) cannot be replaced from a non-elevated one.
- Photo parser rejects an impossible `SYSTEM n` (outside 7-12) and takes the bet type from the number count; 4D photo text is cut at the footer (time or dashed serial). Now built on eight real tickets (two TOTO Ordinary QP, a System 7 with two draws, a two-board TOTO, 4D Roll, 4D iBet, a 10-line 4D). Vision misreads on the pink watermark: `/` read as 7 or 1 in draw numbers, lost TOTO title (found from the `SYSTEM n` header), glued letters on day names and the PRICE row, a board's first number read as `3.04`. System 8-11 have no real photo and will not get one: tested with synthetic rows in the A04 shape (`specs/p3-02-sys811.md`). Do not scrape Singapore Pools for ticket samples (terms ban it, no permission, and their artwork has no watermark noise).
- iBet two-permutation win payout is an assumption.
- Special/Hong Bao Toto draws not scheduled.
- Ticket layout (draw no. vs date) unknown until photos.

## Completed Milestones
- Rules ref v0.2; cl. 5.16 table verified (0/178 mismatches).
- M1 matcher + golden tests; P2-03 capture code + Windows scripts; live on Grayskull (six scheduled tasks, first captures verified 2026-10-21 to 2026-10-24; contact ralph@arqas.io until P2-05).
- P3-01 Vision OCR (`ocr.py`) and P3-02 ticket photo parser (`ticket_ocr.py`) live since 22 Oct 2026; Vision key on Grayskull only. Built on eleven real photos (TOTO, System 7, 4D Roll/iBet/Ordinary); System 8-11 synthetic only. P0-02 closed 2026-11-06. Test OCR input must be the page-processed image (shrink + cleanTicket), not the raw file: raw-file text hid two live bugs.
- P4-02 web checker + P4-06 PWA + P3-07 shared results from screenshots (see docs/web-api.md). Public via tunnel (P4-03 done); P4-04 accounts built 29 Oct 2026 (code and tests done, not yet switched on: needs owner's Cloudflare Email setup, see docs/web-api.md).
- P5-01 descriptive draw statistics (29 Oct 2026): `stats.py`, owner-only `/api/owner/stats` and a Statistics section in `/owner`. Counts only, 30-draw floor, never ranked, nothing public. Publishing stats waits on the Singapore Pools permission question.
- Design canvas: Arcade Drum A, A2 Toto hand-off, A3 4D hand-off.

Docs: docs/toto-4d-rules-reference.md, results-source-decision.md, ingest-schedule.md.
