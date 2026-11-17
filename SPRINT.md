# SPRINT — Toto Vision Checker
_Current work state. Updated every session close._

## Status
- **Sprint**: 1, rules + matcher + results capture
- **Phase**: Active build, capture live on Grayskull
- **Last session**: 2026-11-17 (session 7, closed)
- **Next session intent**: watch the Friday 20 Nov catch-up runs (first live runs of the gap fill); owner steps for accounts switch-on; register 4D Friday catch-up tasks on Grayskull (elevated); frame Group TOTO (P6-15).

## Current Task
P2-07 gap catch-up landed (`3a8fc44`, `f158f43`). Friday catch-up fetches the lowest missing TOTO draw by number, one request per run. Draw 4233 recovered by hand 2026-11-16.

## Task Queue (next 3)
1. Check `logs\ingest.log` after Fri 20 Nov 21:45/22:00: no holes now, so both runs should make no request.
2. Accounts switch-on (P4-04): owner's Cloudflare Email steps, then two env vars on Grayskull.
3. Fix stale `tools/simulate_user.py:90` message ("P4-10 screenshot OCR not built"; it is built).

## Blockers
- Singapore Pools permission track DEFERRED by owner 2026-11-16 (P2-05, P2-06, permission, P2-04 backfill, paid tier, ads, Play). Not a blocker; do not chase.
- Accounts switch-on waits on owner's Cloudflare Email setup.

## Open Decisions
- DECIDED 2026-11-17: Group TOTO/iTOTO is in v1 (P6-15). Framed and built (slices A-F); unrounded share via `money()` is an assumption awaiting owner pass.
- Currency S$ vs US$; paid cap 150 vs 300/week (deferred with permission).

## Session Notes
Rules gap closed, matcher built (135→149 tests), SP terms reviewed (scraping banned, 7 repos scrape anyway), user chose free non-monetised capture with citation. Parser on real pages (4068, 4D 5500), Windows scheduler scripts. Hand-off reveal designs A2/A3 on canvas.

## Session 1 close (2026-10-25)

### Done
- Put the repo under git (nested repo, branch `main`, source-only `.gitignore`) and into the HavenPalms index and inventory.
- Vault: historian node, Session_Log_Hub and Session_01 created under HavenPalms_INDEX.
- Recorded the remote in PROJECT_BRAIN.md and SPRINT.md.
- Published to GitHub: public, aRQa-builds/toto-vision-checker (`b3bc029`, then `60cf89c`). Ticket photos, captured Singapore Pools pages and `tests/fixtures/screens/` removed from the commit before publishing.
- INCIDENT: a first push went out with those files before the cleanup ran, so the repo was briefly public with commit `4900cb3`. It was deleted and recreated clean. Lesson: build and verify the file list before creating a public remote; never chain a push after a step whose failure is not checked.

Tally: LEAD DIRECT 1 (onboarding is git and inventory setup, no gated code slice, no Hand attempt). LOCAL 0 · L1 0 · L2 0 · SPEC FAULT 0. `Delegable: 0 of 0`.
Escalation: LOCAL 0 · L1 0 · L2 0 (uncatalogued 0). Hand lessons landed: 0 (no corrections to learn from).

### Blocked
| Type | What |
| --- | --- |
| input | Real ticket photos to harden P3-02 (4D, System 7-11, Roll), P4-09, P4-10. |
| decision | Singapore Pools permission gates P2-04 backfill, paid tier, ads, Play listing. |
| input | P2-05 results@zenqi.cc alias (capture contact is ralph@arqas.io meanwhile). |

### Next
Re-enter at the Task Queue above. P3-01 Vision OCR and P3-02 ticket parser are already built and live (22 Oct 2026, `ocr.py`, `ticket_ocr.py`); this file was stale on that.

### Merged
None.

### Deployed
None.

### Discoveries
None.

## Session 2 close (2026-10-29)

### Done
- P4-04 optional accounts with saved ticket history, built in 7 slices (plan: `docs/superpowers/plans/2026-10-29-p4-04-accounts.md`). Server: `accounts.py`, `limits.py`, `mailer.py`, `account_routes.py`. Browser: `web/account.js`, sign-in and history UI in `web/index.html`. 558 pytest + 9 node tests green; browser smoke on a scratch data dir (link sign-in in a fresh and an already-open tab, save, no double save, history list, delete account, no serial in the stored row).
- Anonymous use unchanged; privacy line now "Tickets are not stored unless you sign in and choose to save them."
- Nothing pushed to the remote (22+ commits ahead of origin/main).

### Tally
LOCAL 2 (limiter, mailer) · L1 5 (core, history, routes, account.js, UI; Hand failed the first four, the UI went to Fixer by design) · L2 0 · LEAD DIRECT 2 (static serving and service worker, docs) · SPEC FAULT 0 · RESOURCE FAULT 1 (preflight timeout while the GPU was held; not tallied). Hand lessons landed: 6.
`Delegable: 6 of 8`. Reasons for zero: `index.html UI` `too-large` (85 KB, over the 80 KB cap); `static serving + sw bump` `needs-judgement` (two-line wiring, done direct).
Escalation: `handoff-01..04.md` kept local (untracked; the repo is public).
Process miss: slice 4 was launched on a BLOCKED preflight verdict because I piped preflight through grep and hid the exit code. It went green, so no harm, but the run was not a valid attempt by the rule. Disclosed at the time; preflight is now read by exit code.

### Blocked
| Type | What |
| --- | --- |
| owner | Onboard zenqi.cc for Cloudflare Email Sending (SPF/DKIM) and create a token with "Email Sending: Edit". |
| owner | Set `CLOUDFLARE_EMAIL_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` for the Grayskull service, then re-run `tools\setup-web.ps1`. Until then sign-in returns 503 and nothing else changes. |
| decision | Testing phase expired 2026-10-29 03:09 UTC: renew or end (`tools	esting-phase.ps1`). Untouched. |
| decision | Push to the public remote. |

### Next
Switch accounts on (owner steps above), then P2-05 alias, P0-02 ticket photos, P5-01 stats framing.

### Discoveries
- A login link opened in a tab already on the page changes only the hash, so nothing reloads; fixed with a `hashchange` listener.
- The sign-in sheet stayed open after a successful link sign-in; fixed.

## Session 2 addendum: P5-01 owner stats (2026-10-29)

### Done
- `lottery_checker/stats.py` (descriptive counts only, 30-draw floor, fixed "draws are independent" note) and owner-only `GET /api/owner/stats`, shown in a Statistics section of `web/owner.html`. Nothing added to the public page or API. 569 pytest tests green; browser smoke on a scratch data dir for both Toto and 4D.

### Tally
L1 1 (`stats.py`; Hand failed twice) · LEAD DIRECT 1 (route and owner.html wiring, small) · SPEC FAULT 0 · RESOURCE FAULT 0. Hand lesson to land: check the type of each field in the test fixtures before iterating it (Hand iterated the int `additional` as a list).

## Session 3 close (2026-11-05)

### Done
- Config sync: pulled `fix.md`, `open.md`, `run.md` from Coffee_Crew_HQ (REPEAT FAILURE now goes to L1; HLQT heartbeat rule). Committed with `hlqt.md`.
- Testing phase checked: already renewed to 2026-11-09 23:57 UTC (2 renewals), so no renewal made. Date above corrected.
- Accounts switch-on (#12) checked, not done: `CLOUDFLARE_EMAIL_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` unset on Grayskull; Cloudflare Email Sending status unreadable (API 401). Owner steps unchanged.
- P3-02-H parser hardening (`specs/p3-02-harden.md`; `91cf9f3` red tests, `c25b8a3` fix): impossible `SYSTEM n` header takes the type from the count; more than 10 boards no longer raises `StopIteration`; 4D drops footer rows. Hand, attempt 1, `uncatalogued`. 575 pytest + 9 node tests green.
- Live web checker restarted onto the new parser.

### Tally
LOCAL 1 (P3-02-H, uncatalogued) · L1 0 · L2 0 · LEAD DIRECT 0 · SPEC FAULT 0 · RESOURCE FAULT 0. Hand lessons landed: 1.
`Delegable: 1 of 1`.
Escalation: LOCAL 1 · L1 0 · L2 0 (uncatalogued 1).

### Blocked
| Type | What |
| --- | --- |
| input | Switch accounts on: Cloudflare Email Sending for zenqi.cc (SPF/DKIM), token with "Email Sending: Edit", set both env vars on Grayskull. |
| input | P2-05 results@zenqi.cc alias, then P2-06 permission email. |
| input | Real ticket photos (System 7-11, Roll, 4D) for P0-02, P4-09, P4-10. |
| decision | Push to the public remote (25+ commits ahead). |
| decision | Singapore Pools permission (gates P2-04 backfill, paid tier, ads, Play, publishing stats). |

### Next
Owner steps above, accounts switch-on first. Then P2-05, then P2-06. Unframed: Special/Hong Bao draws.

### Merged
None.

### Deployed
Parser hardening live on toto.zenqi.cc, 2026-11-05 00:16 (service restart).

### Discoveries
- `MISS` (process): `tools\setup-web.ps1` run from a non-elevated session stopped the server, then `Register-ScheduledTask` was denied, so the site was down (502) about 2 minutes until `Start-ScheduledTask` restored it. Safe restart after a .py change: end the python process (keep-alive loop restarts it) or `Start-ScheduledTask`.
- `SCOPE`: make `setup-web.ps1` check it can register before it stops anything, or skip re-registering when the task exists.

2026-11-05 | delegable: 1 of 1 | reasons: none | LOCAL: 1 · L1: 0 · L2: 0 (uncatalogued: 1) | lessons landed: 1

## Session 4 close (2026-11-05)

### Done
- `tools\setup-web.ps1`: registers the task before stopping the server (`676b6b4`). Parse-checked only, not run live.
- P3-02-R1 row grouping uses the row mean (`abb0338`): a tall watermark word no longer splits a board row. Hand, attempt 2, `uncatalogued`.
- P3-02-R2 parser fixes from six real photos (`c09e91b`): slash read as a digit in a draw number, glued day name, TOTO found from a `SYSTEM n` header, 4D header noise, glued PRICE row, orphan digit on a board. Hand failed twice (`handoff-06`, `handoff-07`; first run was a spec/fixture fault, re-planned in `0b804ed`), Fixer fixed forward from `handoff-07`. `uncatalogued`.
- P3-02-S System 8-11 guard tests from synthetic A04-shaped rows (`3288c0c`, `specs/p3-02-sys811.md`). All green on arrival, so nothing for Hand. P0-02 now has System 7 (a04), Roll (a03), iBet (a06), 10-line Ordinary (a05), two-draw TOTO (a02). System 8-11 real photos will not exist; no scraping.
- Gate: `py -3 -m pytest tests/test_ticket_ocr.py -q` 42 passed.

### Tally
LOCAL 1 (R1) · L1 1 (R2) · L2 0 · LEAD DIRECT 2 (`setup-web.ps1`, System 8-11 tests; both `no-runner`) · SPEC FAULT 1 (R2 first run) · RESOURCE FAULT 0. Hand lessons landed: 2 (repo tier 10, 11; 10 repeats generic HL-175).
`Delegable: 2 of 4`. Reasons for zero: `setup-web.ps1` `no-runner`; System 8-11 tests `no-runner` (gate already green).
Escalation: LOCAL 1 · L1 1 · L2 0 (uncatalogued 2).

### Blocked
| Type | What |
| --- | --- |
| input | Switch accounts on: Cloudflare Email Sending for zenqi.cc (SPF/DKIM), token with "Email Sending: Edit", set both env vars on Grayskull. |
| input | P2-05 results@zenqi.cc alias, then P2-06 permission email. |
| decision | Push to the public remote (about 30 commits ahead). |
| decision | Singapore Pools permission (gates P2-04 backfill, paid tier, ads, Play, publishing stats). |
| input | 5 Grace refresh proposals AWAITING OWNER. |

### Next
1. Restart the live web checker onto the new parser (end the python process or `Start-ScheduledTask`; not `setup-web.ps1` from a non-elevated window).
2. Owner steps above, accounts switch-on first.
3. Verify `setup-web.ps1` live from an elevated window.

### Merged
None.

### Deployed
Nothing. Parser changes are committed but the live checker still runs the old code.

### Discoveries
- `SCOPE` (closed 2026-11-06): scrub serials. Owner ruled the public repo is fine; serial rows dropped from new fixtures.
- `SCOPE`: `ocr.py` leaves an unused `row_words` variable from Hand's R1 attempt.
- `MISS` (process): none. Handoffs 05-07 stay local and untracked.

2026-11-05 | delegable: 2 of 4 | reasons: no-runner x2 | LOCAL: 1 · L1: 1 · L2: 0 (uncatalogued: 2) | lessons landed: 2

## Session 6 close (2026-11-17)

### Done
- Roadmap walk-through: 20-row traffic-light table. P3-02 confirmed live (web checker process started 12 Nov, after the last parser commit). P4-09/P4-10 are built (`manual.py`, `results_screen.py`); the "needs ticket photos" note was stale.
- Owner deferred the Singapore Pools permission track (items P2-05, P2-06, permission, P2-04, paid/ads/Play).
- P2-07-G Friday catch-up fetches the lowest missing TOTO draw by number (`97cb270` red tests + stub, `3a8fc44` fix). Hand failed twice identically (`handoff-09`): it left the "yesterday stored" early return ahead of the hole check. Fixer fixed forward. `uncatalogued`.
- P2-07-H gap fill not blocked by "today's draw already stored" (`df340db` red test, `f158f43`). Hand, attempt 1. `uncatalogued`.
- Draw 4233 (Mon 9 Nov) recovered by one manual `--draw 4233` run. Web parse test: typed ticket for 4233 through `/api/ticket` and `/api/check` on the live checker revealed correctly against the stored draw.
- Gate `py -3 -m pytest tests/test_ingest.py -q` 33 passed; full suite 619 passed.

### Tally
LOCAL 1 (P2-07-H) · L1 1 (P2-07-G, handoff-09) · L2 0 · LEAD DIRECT 0 · SPEC FAULT 0 · RESOURCE FAULT 0. Hand lessons landed: 1 (generic HL-199).
`Delegable: 2 of 2`.
Escalation: LOCAL 1 · L1 1 · L2 0 (uncatalogued 2).

### Blocked
| Type | What |
| --- | --- |
| input | Switch accounts on: Cloudflare Email Sending for zenqi.cc (SPF/DKIM), token with "Email Sending: Edit", set both env vars on Grayskull. |
| decision | Group TOTO / iTOTO support in v1 (P6-15). |
| decision | Testing phase expired 2026-11-09 23:57 UTC: renew or close out (`tools	esting-phase.ps1`). |
| decision | Push to the public remote (about 35 commits ahead). |

### Next
1. Read the 20 Nov Friday catch-up lines in `logs\ingest.log`.
2. Owner steps above, accounts switch-on first.
3. `simulate_user.py` stale P4-10 message.

### Merged
None (work on `main`).

### Deployed
Capture code (P2-07-G, P2-07-H) is live for the next scheduled run; tasks start a fresh process each run. Draw 4233 stored 2026-11-16.

### Discoveries
- `MISS` (process): `--catch-up` first version skipped the hole when today's draw was stored; caught by the live acceptance run, fixed same session as P2-07-H.
- `SCOPE`: 9 Nov failure was a redirect to `toto-results.singaporepools.com.sg/en/index.html`, a promo landing page ("$12 Million Hong Bao Draw") with no results block. May recur before big draws; gap fill now recovers it on Friday.
- `SCOPE`: 4D has no gap check (P2-07 is TOTO only).
- `SCOPE`: `tools/simulate_user.py:90` says P4-10 is not built; it is.
- `SCOPE`: `store` re-saves any draw the page returns, so a gap request answered with the latest page rewrites that draw's `captured_at`.
- `SCOPE`: HQ `roadmap-report.mjs` parses 0 modules from this repo's PROJECT_BRAIN format.

2026-11-17 | delegable: 2 of 2 | reasons: none | LOCAL: 1 · L1: 1 · L2: 0 (uncatalogued: 2) | lessons landed: 1

## Session 7 close (2026-11-17)

### Done
- Roadmap walk-through; owner config sync applied, testing phase renewed to 24 Nov 13:57, push approved.
- `simulate_user.py` stale P4-10 message fixed. LEAD DIRECT (no-runner).
- P2-07-I `store` never re-saves a stored draw: LOCAL after a SPEC FAULT (spec broke an existing test; `handoff-10`). `uncatalogued`.
- P2-07-J 4D gap catch-up: LOCAL, `uncatalogued`. Friday schedule and docs LEAD DIRECT.
- P6-15 Group TOTO / iTOTO, framed (`specs/p6-15-group-toto-frame.md`) and built: A `units.py` share and stake, B `scale_to_units` (`b2af25e`), C entry (`bdf4e87`), D reveal (`0335aef`): all LOCAL, attempt 1, uncatalogued. E photo reader (`fcfebea`): L1, `handoff-11`. F API, web, docs (`81ec3c7`): LEAD DIRECT, `too-large` (index.html 85 KB). Full suite 658 passed.
- Pushed to origin/main.

### Tally
LOCAL 6 (P2-07-I, P2-07-J, P6-15-A, B, C, D) · L1 1 (P6-15-E) · L2 0 · LEAD DIRECT 3 (simulate_user, 4D schedule/docs, P6-15-F) · SPEC FAULT 1 (P2-07-I) · RESOURCE FAULT 0. Hand lessons landed: 6 (HL-204 to HL-209, generic).
`Delegable: 5 of 6` for P6-15 (F `too-large`).
Escalation: LOCAL 6 · L1 1 · L2 0 (uncatalogued 7).

### Blocked
| Type | What |
| --- | --- |
| input | Switch accounts on: Cloudflare Email Sending for zenqi.cc, token, two env vars on Grayskull. |
| input | Register the 4D Friday catch-up tasks on Grayskull (elevated `setup-schedule.ps1`). |
| input | A real Group TOTO / iTOTO ticket photo to test reading (none exists). |
| decision | Testing phase renews/ends 24 Nov 13:57. |

### Next
1. Read the 20 Nov Friday catch-up lines in `logs\ingest.log`.
2. Owner steps above, accounts switch-on first.
3. Owner pass on unit-ticket share wording and the unrounded-share assumption.

### Merged
P6-15 on `main`; regression pass y (658); real test exercised n (specimen text only).

### Deployed
Nothing restarted: the live web checker still runs the old code until its process restarts.

### Discoveries
- `MISS` (process): the API check path bypassed `TicketDraft.check()` and so never applied the unit share; caught by the slice F test. Fixed.
- `SCOPE`: `TicketDraft.check()` and the API duplicate the check path.
- `SCOPE`: `ticket_entry.py` has a stale "not yet priced per unit" comment style elsewhere? none found; docstring updated.

2026-11-17 | delegable: 5 of 6 | reasons: too-large x1 | LOCAL: 6 · L1: 1 · L2: 0 (uncatalogued: 7) | lessons landed: 6

## Session 7 addendum (2026-11-17, after close)

### Done
- 4D Friday catch-up tasks registered on Grayskull (elevated `setup-schedule.ps1`, all eight tasks Ready). P6-15 verified live on typed Group TOTO and iTOTO tickets; BRAIN row 10 now 🟢.
- Welcome splash (LEAD DIRECT, `too-large`, no-runner: visual and audio): synthesised clack, thud and pop sounds; balls pop two or three at a time and shove their neighbours; paint splatter fades at once; "Tap for sound" hint with iOS-safe unlock. Commits `770e07f`, `f860493`, `1b3c0f5`, `9e82fe6`, `dbc3382`, `d23b33b`. Owner confirmed sound works.

### Tally
LEAD DIRECT +1 (splash). LOCAL 6 · L1 1 · L2 0 unchanged. Hand lessons landed: 0 (none from this work).

### Blocked
| Type | What |
| --- | --- |
| input | Read the 20 Nov Friday catch-up lines in `logs\ingest.log`; then row 4 goes green. |
| input | Accounts switch-on: Cloudflare Email Sending, token, two env vars on Grayskull. |
| decision | Testing phase renews or ends 24 Nov 13:57. |

### Next
1. 20 Nov log read. 2. Accounts switch-on. 3. 24 Nov testing-phase decision.

### Discoveries
- `MISS` (process): a page change shipped without bumping `web/sw.js` VERSION, so installed apps kept the old splash; fixed (v24).
- `MISS` (process): a Python patch that opened the target with `'w'` before encoding emptied `web/index.html` on an encode error; restored from git. Encode first, then write.
- `SCOPE`: no "tap for sound" memory between visits; browsers cannot autoplay sound.

2026-11-17 | delegable: 0 of 1 | reasons: needs-judgement x1 | LOCAL: 0 · L1: 0 · L2: 0 (uncatalogued: 0) | lessons landed: 0
