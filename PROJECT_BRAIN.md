# PROJECT_BRAIN — Toto Vision Checker
_LLM context file. Dense. No fluff. Written for cold re-entry._

## Identity
- **What it is**: Free public SG Toto/4D ticket checker: scan ticket (Google Vision), match against draw, show payout.
- **Stack**: Python 3.10+ stdlib core (`lottery_checker/`), pytest; web app later (Arcade Drum UI, PWA).
- **Deploy**: toto.zenqi.cc (planned); capture runs on Grayskull (Win 11 64-bit, Task Scheduler).
- **Home**: D:\SakuraHydra\HavenPalms\Toto_Vision_Checker (mirror: claude.ai project "Toto OCR Check").
- **Remote**: https://github.com/aRQa-builds/toto-vision-checker (PUBLIC, `main`, since 2026-10-25). Ticket photos, captured Singapore Pools pages (`tests/fixtures/*.jpg`, `*.html`, `screens/`) and `data/` are git-ignored and stay local; never add them. Public repo: no secrets, no `.env`.
- **Version**: v0.1 (matcher + capture, 149 tests).

## Architecture Decisions
- Toto Groups 1-4 priced only from published draw amounts; 5-7 fixed ($50/$25/$10), published value overrides (cascade).
- 4D stakes: Roll ×10, System ×perms, iBet once (Singapore Pools bet slip page).
- Results: after-draw capture of official page, 1 request + 1 retry, credited, "we do not own this data" (user's risk decision 2026-10-17). Screenshot/typing flow kept as fallback.
- No iframe/CORS route: official page blocks framing.
- Accounts: email magic link. Paid tier, ads, Play listing ON HOLD until permission.

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
- iBet two-permutation win payout is an assumption.
- Special/Hong Bao Toto draws not scheduled.
- Ticket layout (draw no. vs date) unknown until photos.

## Completed Milestones
- Rules ref v0.2; cl. 5.16 table verified (0/178 mismatches).
- M1 matcher + golden tests; P2-03 capture code + Windows scripts.
- Design canvas: Arcade Drum A, A2 Toto hand-off, A3 4D hand-off.

Docs: docs/toto-4d-rules-reference.md, results-source-decision.md, ingest-schedule.md.
