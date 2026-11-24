# PROJECT_BRAIN — Toto Vision Checker
_LLM context file. Dense. No fluff. Written for cold re-entry._

## Identity
- **What it is**: Free public SG Toto/4D ticket checker: scan ticket (Google Vision), match against draw, show payout.
- **Stack**: Python 3.10+ stdlib core (`lottery_checker/`), pytest; FastAPI web checker (`web/index.html` Arcade Drum UI, PWA) on Grayskull, live locally.
- **Deploy**: toto.zenqi.cc LIVE since 22 Oct 2026 (Cloudflare Tunnel sakura-hud, served from Grayskull); capture runs on Grayskull (Win 11 64-bit, Task Scheduler).
- **Home**: D:\SakuraHydra\HavenPalms\Toto_Vision_Checker (mirror: claude.ai project "Toto OCR Check").
- **Remote**: https://github.com/aRQa-builds/toto-vision-checker (PUBLIC, `main`, since 2026-10-25). Ticket photos, captured Singapore Pools pages (`tests/fixtures/*.jpg`, `*.html`, `screens/`) and `data/` are git-ignored and stay local; never add them. Public repo: no secrets, no `.env`.
- **Version**: v0.2 (matcher + capture + optional accounts, 659 pytest + 9 node tests).

## Architecture Decisions
- Toto Groups 1-4 priced only from published draw amounts; 5-7 fixed ($50/$25/$10), published value overrides (cascade).
- 4D stakes: Roll ×10, System ×perms, iBet once (Singapore Pools bet slip page).
- Results: after-draw capture of official page, 1 request + 1 retry, credited, "we do not own this data" (user's risk decision 2026-10-17). Screenshot/typing flow kept as fallback.
- No iframe/CORS route: official page blocks framing.
- Singapore Pools permission track DEFERRED by owner 2026-11-16 (P2-05 alias, P2-06 email, the permission, P2-04 backfill, paid tier/ads/Play). Do not chase or draft it until the owner reopens it. Still no money, no bulk backfill, no public stats while unpermitted.
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
- Any change to `web/index.html` needs `VERSION` bumped in `web/sw.js` (now v24), or installed apps keep the old page. Splash sound is Web Audio and stays locked until a touch; the first tap unlocks it (hint shown), later taps skip.
- Unit tickets (P6-15): Group TOTO share = entry win / n, iTOTO share = win x u / N, both unrounded floats shown via `money()` (assumption, owner may overrule). Pending stays None, never 0. PRICE check vs unit stake warns above S$0.10. The API check path must go through `scale_to_units`; built from specimen text only, no real photo.
- Special/Hong Bao Toto draws (P2-07, 2026-11-16): the Friday `--catch-up` run fills TOTO draw-number holes between the lowest and highest stored draw, lowest first, one request per run, via the `?sppl` deep link. Never below the lowest stored draw (that would be a backfill). TOTO live; 4D gap check (`--catch-up`, P2-07-J, 17 Nov) coded and tested, its Friday 22:15/22:30 tasks are in `setup-schedule.ps1` but not yet registered. `store` never re-saves a draw already on file (P2-07-I).
- Failure mode seen 9 Nov 2026: the results URL redirected to `toto-results.singaporepools.com.sg/en/index.html`, a promo landing page with no results block, so both runs failed to parse. The Friday gap fill recovers it; the page is kept in `data/failed/toto/`.
- `S'OUT` on a 4D line is a sold-out side (stake 0), not a misread `$1` (rules reference line 171). A fully sold-out line is dropped with a warning, and the printed PRICE is the total of accepted stakes only: the draw 5553 photo prints S$9 for ten lettered lines because line C is sold out. Do not "fix" the parser for it (checked 24 Nov 2026, `tests/test_api.py` draw 5553 test).
- Ticket layout (draw no. vs date) unknown until photos.

## Completed Milestones
- Rules ref v0.2; cl. 5.16 table verified (0/178 mismatches).
- M1 matcher + golden tests; P2-03 capture code + Windows scripts; live on Grayskull (six scheduled tasks, first captures verified 2026-10-21 to 2026-10-24; contact ralph@arqas.io until P2-05).
- P3-01 Vision OCR (`ocr.py`) and P3-02 ticket photo parser (`ticket_ocr.py`) live since 22 Oct 2026; Vision key on Grayskull only. Built on eleven real photos (TOTO, System 7, 4D Roll/iBet/Ordinary); System 8-11 synthetic only. P0-02 closed 2026-11-06. Test OCR input must be the page-processed image (shrink + cleanTicket), not the raw file: raw-file text hid two live bugs.
- P4-02 web checker + P4-06 PWA + P3-07 shared results from screenshots (see docs/web-api.md). Public via tunnel (P4-03 done); P4-04 accounts built 29 Oct 2026 (code and tests done, not yet switched on: needs owner's Cloudflare Email setup, see docs/web-api.md).
- P5-01 descriptive draw statistics (29 Oct 2026): `stats.py`, owner-only `/api/owner/stats` and a Statistics section in `/owner`. Counts only, 30-draw floor, never ranked, nothing public. Publishing stats waits on the Singapore Pools permission question.
- Design canvas: Arcade Drum A, A2 Toto hand-off, A3 4D hand-off.

Docs: docs/toto-4d-rules-reference.md, results-source-decision.md, ingest-schedule.md.

## Roadmap (traffic light: 🟢 done · 🟡 built, awaiting verification or owner pass · 🔴 blocked on a decision or permission · ⚪ not framed)
| # | Module / AD | Scope | Status | Blocker / milestone |
| :-- | :--- | :--- | :---: | :--- |
| 1 | Rules ref v0.2 | Toto/4D rules, cl. 5.16 verified | 🟢 | 0/178 mismatches |
| 2 | M1 matcher | `toto.py` / `fourd.py` with golden tests | 🟢 | |
| 3 | P2-03 capture | After-draw capture on Grayskull | 🟢 | Live since 21 Oct |
| 4 | P2-07 gap fill | Friday catch-up fetches lowest missing draw by number (TOTO and 4D live) | 🟢▲ | 4D tasks registered 17 Nov; 20 Nov logs show "no gaps" on both runs; owner OK 24 Nov |
| 5 | P3-01 / P3-02 OCR + ticket parser | Vision OCR, photo parser | 🟢 | System 8-11 synthetic only |
| 6 | P4-02 / P4-06 / P3-07 | Web checker, PWA, shared results from screenshots | 🟢 | Live at toto.zenqi.cc |
| 7 | P4-09 / P4-10 | Manual entry, results screen reader | 🟢 | |
| 8 | P4-04 accounts | Optional magic-link accounts, saved history | 🟡 | Owner: Cloudflare Email setup + two env vars on Grayskull |
| 9 | P5-01 stats | Owner-only descriptive stats | 🟢 | Public only after permission |
| 10 | P6-15 Group TOTO / iTOTO | In v1: holder share, unit stake, OCR, reveal, web | 🟢 | Live since 17 Nov (checker restarted, typed Group TOTO and iTOTO tickets verified). Specimen text only: no real photo. Share is an unrounded float via `money()`; owner ruled 24 Nov that a share that is not a whole cent reads "You won about S$x" with "The official payout may differ by a few cents" (Singapore Pools may round, cl. 5.7). Live since 24 Nov (checker restarted) |
| 11 | Testing phase | Higher photo limits | 🟢 | Renewed on Grayskull 24 Nov 2026 (4th renewal), on until 1 Dec 2026 11:10 local; decide renew or end then (`tools\testing-phase.ps1`) |
| 12 | P2-05 / P2-06 / permission / P2-04 backfill | Alias, email, permission, backfill | 🔴 | Deferred by owner 16 Nov |
| 13 | Paid tier / ads / Play listing | Monetisation | 🔴 | On hold until permission |
