# Toto Vision Checker: SG TOTO and 4D ticket checker

A free public checker for Singapore TOTO and 4D tickets. You give it a ticket
(typed now, photo later) and the draw result (captured after each draw, typed,
or read from a screenshot of the official page); it works out what the ticket
won, with the claim-by date and a stake check against the printed PRICE.

- Python 3.10+ (Grayskull runs 3.11.9). The checking core is stdlib only.
- The web checker adds `fastapi` and `uvicorn` (`requirements.txt`).
- Home: `D:\SakuraHydra\HavenPalms\Toto_Vision_Checker` on Grayskull; mirror in the
  claude.ai project "Toto OCR Check" under `claude/lottery-checker/`.
- Rules source: `docs/toto-4d-rules-reference.md` (v0.3). Roadmap: project memory.

Not affiliated with Singapore Pools. Official results published by Singapore Pools are final.

## Quick start (Grayskull)
```
cd D:\SakuraHydra\HavenPalms\Toto_Vision_Checker
py -3 -m pip install -r requirements.txt
py -3 -m pytest -q                      # 494 passed (25 Oct 2026)
tools\run-web.cmd                       # web checker on http://127.0.0.1:8765, Ctrl+C to stop
```
Try the TOTO and 4D example buttons: they use draws 4227 and 5551 from the capture.

## What runs where
| Piece | How it runs | Docs |
|---|---|---|
| After-draw capture | Task Scheduler, `\ZenQi\TotoChecker\`: 4D Wed/Sat/Sun 18:45 + 19:00, TOTO Mon/Thu 21:45 + 22:00, TOTO Friday catch-up 21:45 + 22:00. Set up with `tools\setup-schedule.ps1` | `docs/ingest-schedule.md` |
| Web checker | `tools\run-web.cmd` by hand, or always on with `tools\setup-web.ps1` (starts at logon, runs hidden through `tools\web-service.cmd`, which restarts the server 10 s after it stops; logs to `logs\web.log`) | `docs/web-api.md` |
| Going public | Cloudflare Tunnel to `127.0.0.1:8765` (P4-03, not done yet) | `docs/web-api.md` |

Kill switches: `tools\setup-schedule.ps1 -Disable` stops the capture; `tools\setup-web.ps1 -Stop` or `-Disable` stops the web checker.

## Modules (`lottery_checker/`)
Checking core
- `rules.py`: rule versions keyed by first draw number (`toto-2022` from 3751, `toto-2026-03-02` from 4161, `4d-2024-12-30` from 5269). `rules_for(game, draw_no)` raises for older draws.
- `toto.py`: Ordinary, System 7-12, System Roll. Grades every set of six, counts shares per group, prices them from the draw.
- `fourd.py`: Ordinary, Roll, System, iBet with Big/Small; covered numbers, prizes, stake per draw.
- `ticket.py`: `check_ticket(entries, draws)` rolls a whole ticket up: lines, total stake, total won (None if any group is pending), net, claim-by.
- `claim.py`: 180 days from the earliest draw on the ticket; a hint, never "void".
- `reveal.py`: what the result screen may say. Pending is never S$0; stake vs printed PRICE; captured vs "as entered by you" attribution.

Getting tickets and results in
- `ticket_entry.py`: typed ticket, laid out as printed (headers, QP, DRAW lines, PRICE, S'OUT, `*`) or short forms. Returns a `TicketDraft`, the shared model the photo parser (P3-02) will also produce.
- `manual.py`: typed draw results (TOTO 6 + Additional with optional Group 1-4 amounts; 4D all 23 numbers).
- `results_screen.py`: reads phone screenshots of the official results page (via OCR text), merges several, says what is missing.
- `ocr.py`: Google Vision client. Needs `GOOGLE_VISION_API_KEY` (P3-01; key on Grayskull since 22 Oct, project zenqi-toto).
- `ticket_ocr.py`: ticket photo -> the ticket as typed text -> `parse_ticket` (P3-02). Drops the SINGAPORE POOLS watermark, rebuilds boards from word rows, fills a missing board letter. Built on two real TOTO Ordinary tickets; 4D photos untested.
- `parse.py`: parses the official TOTO and 4D results pages; fails loudly on layout change.
- `ingest.py`: after-draw capture with guardrails (kill switch, one request plus one retry, honest user agent, attribution, failed pages kept in `data\failed\`). `--catch-up` for Friday special draws.
- `store.py`: reads captured draws from `data\draws\<game>\<n>.json`.
- `shared.py`: results from users' screenshots, served only when two people agree and nobody disagrees; any conflict voids the draw; each entry keeps hashed person, device label and time (P3-07); `TOTO_SHARED_RESULTS=0` turns it off. See docs/web-api.md.

Web
- `api.py`: FastAPI app: `/api/health`, `/api/ticket`, `/api/check`, `/api/ticket/photo`, `/api/results/screenshot` and the batch `/api/results/screenshots` (all need the Vision key; limits in `limits.py` and docs/web-api.md), and the page at `/`. No endpoint lists results.
- `web/index.html`: the Arcade Drum page (one file). Ticket → Confirm → Unlock → Reveal.
- `web/manifest.webmanifest`, `web/sw.js`, `web/offline.html`, `web/icons/`: installable app (P4-06). Add to a phone's home screen over HTTPS (the tunnel) or on Grayskull itself. The service worker never caches `/api/`; bump `VERSION` in `sw.js` when the page changes.

Accounts (P4-04, optional: anonymous use is unchanged)
- `accounts.py`: SQLite `dataccounts.db`. Magic-link sign-in (15 minute single-use token, 30 day session, both stored only as SHA-256 hashes) and saved history: game, draw, bets and outcome only, never serials, barcodes, photos or ticket text. Kept to 31 Dec of the year after it was saved; 500 entries a user; delete one entry or the whole account.
- `limits.py`: sign-in mail limits (3 per email and 10 per connection an hour, 200 a day; `TOTO_LINK_PER_EMAIL`, `TOTO_LINK_PER_IP`, `TOTO_LINK_PER_DAY`).
- `mailer.py`: sends the link through the Cloudflare Email Service from `login@zenqi.cc` (`TOTO_MAIL_FROM`; `CLOUDFLARE_EMAIL_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` in the environment). `TOTO_DEV_LINKS=1` logs the link instead when unconfigured (never the address).
- `account_routes.py`: `/api/auth/*`, `/api/me`, `/api/history`, `/api/account`. `web/account.js` is the browser client.

Tools
- `tools/run-ingest.cmd`, `tools/setup-schedule.ps1`: capture.
- `tools/run-web.cmd` (one-off, by hand), `tools/web-service.cmd` (keep-alive loop for the task), `tools/setup-web.ps1`: web checker.
- `tools/simulate_user.py`, `tools/verify_cl516.py`, `tools/toto_system_shares.py`: checks and derivations.
- `tools/testing-phase.ps1`: testing phase with higher ticket-photo limits for 7 days (`-Start`, `-Renew`, `-End`).
- `tools/vision_smoke.py`: real Vision run on the results screenshots (PASS/DIFFERS against the typed reference) and on any photos you name; `--save` keeps the text in `tests/fixtures/ocr/` (real tickets: those files hold serial numbers, keep them on Grayskull).

## Data
- `data/raw/<game>/<n>.html`: page as captured. `data/draws/<game>/<n>.json`: parsed draw with `source`, `official_url`, `attribution`, `rules_version`.
- `data/failed/<game>/`: pages that did not parse, with request details.
- Ticket text sent to the web checker is not stored or logged. Photos and screenshots go to Google Cloud Vision to be read and are not kept.

## Tests (`tests/`)
569 pytest tests plus 9 `node --test` tests for `web/account.js` (`node --test tests/web/account.test.cjs`) (`tests/conftest.py` clears `GOOGLE_VISION_API_KEY`, so tests never make a real, billed Vision call). Highlights: two real ticket photos read by Vision (`test_ticket_ocr.py`, serials replaced); the full official 2026 cl. 5.16 System table (`golden_cl516.py`); parsers on real pages (TOTO 4068, 4D 5500); real phone screenshots of the official pages for draws 4227 and 5551 (`fixtures/screens/`); the 2026 special draws (`fixtures/special_draws_2026.json`); the API against draws the capture really stored.

## Design rules
- Rule versions are keyed by draw number, not date ("from Draw N"; the 2026 TOTO rules started mid-day).
- A draw with a real number always carries its own rule set; an unknown old draw raises instead of being priced from today's rules. Released versions are never edited.
- TOTO Groups 1-4 are never computed: the amount comes from the published result. Missing means pending, never S$0. Groups 5-7 default to $50/$25/$10; a published value overrides (cascade).
- 4D prize tables are per $1 from the rules; iBet amounts are looked up, never divided. iBet is charged once (official specimen).
- Special TOTO draws (New Year, Reunion, Hong Bao, National Day) are ordinary draws moved to a Friday in place of that week's Thursday; all of 2026 to 19 Oct checked.
- The server never fetches Singapore Pools; only the scheduled capture does, once per draw plus one retry.

## Open assumptions and gaps
- iBet with two different permutations winning in one draw pays each match (rules reference, open item 7).
- No 4D rule version before draw 5269; add one before any backfill (P2-04).
- Group TOTO / iTOTO unit tickets are recognised but refused: payout per unit and rounding not worked out (P6-15).
- System 7-11 and System Roll printed layouts not yet seen on a real ticket (P0-02).
- Screenshot reading is tested on OCR-shaped text; real Vision output order to be checked once a key exists.
