# SPRINT — Toto Vision Checker
_Current work state. Updated every session close._

## Status
- **Sprint**: 1, rules + matcher + results capture
- **Phase**: Active build, capture live on Grayskull
- **Last session**: 2026-10-17
- **Next session intent**: P2-05 results@zenqi.cc alias, then swap `TOTO_CONTACT` in `tools\run-ingest.cmd` back and send P2-06.

## Current Task
P2-03 live (verified 2026-10-25): 494 tests pass, six tasks registered, 4D 5551-5552 and Toto 4227-4228 stored. Remaining: P2-05 alias, then switch `TOTO_CONTACT` to results@zenqi.cc.

## Task Queue (next 3)
1. P2-05 set up results@zenqi.cc (M365 alias), then P2-06 send permission email (add schedule ask).
2. P0-02 ticket photos (System 7-11, Roll, 4D Roll/iBet, multi-draw): the photo parser was built on two real TOTO Ordinary tickets only; 4D photos untested.
3. P4-03 Cloudflare Tunnel (going public), then P4-04 accounts. P5-01 stats once framing is decided.

## Blockers
- None on the remote: public repo live (aRQa-builds/toto-vision-checker), 2026-10-25.
- Ticket photos: needed to harden P3-02 (4D, System 7-11, Roll layouts unseen), and for P4-09/P4-10.
- Permission from Singapore Pools: gates P2-04 backfill, paid tier, ads, Play.

## Open Decisions
- Currency S$ vs US$; paid cap 150 vs 300/week (on hold).
- Group TOTO/iTOTO support in v1?
- P5-01 descriptive-only stats framing.

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
