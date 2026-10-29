---
description: Session close — write PROJECT_BRAIN.md and SPRINT.md, sweep discoveries, route learnings. Run at ~60% context or when the queue empties.
---

# /close

Write files directly. Do not summarise back to chat — the files are the output.
**Step 10 is the one deliberate exception** — it is chat-only, by design, and runs last.

Work through in order. Skip nothing; an empty section is a valid result and should look obviously empty.

---

## 1. SPRINT.md — this session

Append, do not rewrite history.

- **Done** — tasks passed, with tally: solved LOCAL / L1 / L2 / SPEC FAULT. Mark each Hand
  attempt that had no Doris entry as `uncatalogued`. Fixer fixing forward from Hand's diff
  is **L1**.
- **Blocked** — a `| Type | What |` table under `### Blocked`, one row per blocker. Type is
  `input` (needs the human) or `decision`. Never a bullet list: `roadmap-report.mjs` reads only
  the table, so bullets read as zero blockers (s52–s55 did, 2026-09-27). None blocked →
  write `None.` and no table (every row counts as a blocker)
- **Next** — the top of the queue when work resumes
- **Merged** — feature name, regression pass y/n, real test exercised y/n
- **Deployed** — what and when, if anything went out

## 2. Discoveries — sweep and tag

Every finding from the preview exercise or manual test gets exactly one tag:

| Tag | Meaning | Destination |
|-----|---------|-------------|
| `MISS` | in criteria, didn't work | front of queue + Doris signal |
| `SCOPE` | not in criteria | backlog, untouched — does not reopen the feature |
| `FRAME` | criteria were wrong | frame questions + Doris review |

Do not re-litigate a `SCOPE` item. It competes next sprint like anything else.

## 3. PROJECT_BRAIN.md — durable decisions only

A line earns a place here if a future session would make the wrong call without it.

- Decisions and the reason behind them, not the discussion
- Constraints discovered (infra, tier limits, dependency behaviour)
- What was tried and rejected, with why

Not here: task status, sprint progress, anything already in SPRINT.md.

## 4. Route learnings

Check the tally for recurrence, then promote. **The routing table lives in Clara
(`skills/clara`, "Promotion — routing"), not here** — this list drifted to three destinations
while the catalog layer grew to seven, which is the same one-fact-one-home failure the catalogs
exist to prevent. Read Clara; do not maintain a second copy.

Summary only, as a pointer: frontend → Freya · core backend/storage → Baker · secrets, tokens,
credentials → Iris · audit rows and log lines → Edith · test shape → Doris · close/attribution →
Clara · compliance → ⛔ **never Grace** (prescriptive-from-authority; a recurrence never admits a
rule there). Framing miss recurred **2x** — or **1x if it cost a whole feature** → frame questions.

On every promotion:
- Tag `DURABLE` (how the codebase works) or `SCAFFOLD` (how to make the current tier behave)
- **State what it replaced.** Nothing enters without an eviction or a merge.
- Date the entry.

Below threshold: leave it in SPRINT.md and let it recur. One bad build is not doctrine.

## 4a. Land Hand lessons — the learning loop

The one learning written on **first occurrence**. The 3x threshold above is for catalogs; a
Hand lesson exists to stop occurrence two. **The procedure lives in Clara ("Hand lessons —
land them at close")**, not here. Read it there. In summary:

- **Sources:** the "Lesson for Hand" line in every handoff resolved this session, every
  Lead fix-up after a LOCAL pass, and every `MISS` Hand caused.
- **Destination:** a code-shape rule any repo would want goes to
  `Coffee_Crew_HQ/hand-lessons.md`. A lesson that only makes sense in this repo goes to the
  repo's own `hand-lessons.md`.
- ⛔ **Scrub before landing:** no values, names or figures.
- **Doris request:** three lessons on one shape with no Doris entry → log a Doris catalog
  request.
- **Warm the retrieval index:** `node d:/SakuraHydra/Coffee_Crew_HQ/scripts/rig-index.mjs --repo .`
  (Clara). Skipped on a RESOURCE FAULT, never a blocker.
- **Delegable log:** append the standing line with `LOCAL · L1 · L2 (uncatalogued)` and
  `lessons landed: k`. Zero is a valid entry. Log a skipped count as zero with the reason,
  never omit it.

## 10. Session Progress Tracker Summary — chat, not a file

Runs **last**, after steps 1–4a are written. This is the one deliberate exception to "do not summarise back to chat" at the top of this file. It exists because no single file answers *"what's open, what's done, across the whole build, right now"* — SPRINT.md's queue table is per-module state and PROJECT_BRAIN.md is decisions; neither, read alone, gives a build-wide readout, and the two can silently disagree.

**Two different questions — do not collapse them:**

- **This session's Done** (step 1's list) — what happened in the last few hours.
- **Build-wide status** (this step) — where every module in SPRINT.md's `SPRINT-queue-modules`
  table stands *right now*, regardless of whether this session touched it.

**Build it by cross-checking, not restating:**

1. Read the current `SPRINT-queue-modules` table (just-written, this close pass).
2. For each module row, check PROJECT_BRAIN.md's AD/PATTERN frontier (`--status live`) for any
   decision that bears on that module's status.
3. **Flag a contradiction, don't silently resolve it** — e.g. an AD records something as
   overridden or decided but the queue row hasn't been updated to match, or a queue row claims
   `done` with no corresponding AD/commit backing it.
4. If a contradiction is found, fix it now, in this same close pass.

**Output format — three headed sections, in this order, header text fixed:**

```text
## Session <N> close — done:

- <one bullet per Done row from step 1, plain language, cite the commit/AD/gate>
- ...

Tally: <LOCAL DIRECT FAULT GRACE L1 L2 LEAD RESOURCE SPEC TRANSFER n ·>. `Delegable: n of m`.
Escalation: LOCAL a · L1 b · L2 c (uncatalogued u). Hand lessons landed: k.

## Open

[Render the SPRINT-queue-modules table condensed to one line per row using the exact glyphs: ✅ done · 🔶 done (partial split) · ⏳ stub/pending/blocked-on-work · ⛔ blocked on a decision or FRAME · 📋 roadmap]

## Todos next

1. <top of queue item, why it's next>
2. ...
n. Standing/carried-forward blockers, grouped in one line, not repeated per-item.

---
## LOCAL HANDOFF (Steps 5-9 & Boundary Sweep)

Once the Step 10 summary is printed to the chat, you must immediately use your terminal or bash execution tool to run the following command to execute the local staging push, config sync, vault mirroring, and boundary sweep via the local state machine:

node d:/SakuraHydra/Coffee_Crew_HQ/scripts/scout-close.mjs