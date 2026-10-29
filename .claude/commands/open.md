---
description: Session open — read project state, run environmental preflight, render roadmap, sort the queue.
model: sonnet
effort: medium
---

# /open

!bash node d:/SakuraHydra/Coffee_Crew_HQ/scripts/scout-config-sync.mjs

!bash node d:/SakuraHydra/Coffee_Crew_HQ/scripts/scout-open.mjs

!bash cd d:/SakuraHydra/aRQa_Solutions/aRQa_Engineer_Handbook && node scripts/refresh-due.mjs --all | grep -Ev '\sok$'

---

## Step 0 — config sync (runs first, above)

`scout-config-sync.mjs` runs **before** `scout-open.mjs`, not after: a stale `num_ctx` or a
stale delegation rule corrupts every judgement made afterwards. ⭐ **`Coffee_Crew_HQ` is master
for shared config**, not the bare umbrella root (D-9, 2026-08-10).

Three tiers. The tier decides the action; nothing here is a blanket clone.

| Tier | Files | Action |
|---|---|---|
| **1 · MIRROR** | `.continue/config.yaml`, `.continue/rules/`, `.claude/commands/*.md` | Pull on hash mismatch, after confirmation |
| **2 · NEVER SYNC** | `.claude/scheduled_tasks.json`, `.claude/scheduled_tasks.lock`, `.claude/settings.local.json`, `.claude/launch.json` | Excluded. Never copied, in either direction |
| **3 · PROMOTE, NOT CLONE** | `.claude/skills/**` | Counted, never copied. A skill moves only as an owner-landed promotion |

Checked by **content hash, never mtime** — `git checkout`, `git clone` and a plain copy all
reset mtime, so "destination is newer" fires on byte-identical files and stays silent on real
divergence.

- **COPIED** → the file was absent locally; there was no local edit to destroy. No action.
- **DIFF** → **do not overwrite.** Show `diff -u <local> <source>` and ask, in both directions,
  regardless of which side is newer. Only after the human confirms, re-run with `--apply`.
  A local edit made mid-session for a reason is exactly what a silent pull destroys.
- **ABSENT-UPSTREAM** → the project has a file the source lacks. Never auto-push at open;
  note it for `/close` step 6.
- Run from inside `Coffee_Crew_HQ` itself, this reports "nothing to pull" — it is the source.

The sync is **advisory and never halts `/open`**; a DIFF is a question for the human, not a
failed preflight.

---

## Instructions for Claude

Using the local context emitted by `scout-open.mjs` above:

1. **Check Preflight Blockers:**
   - If any environmental failure or missing file is reported, halt immediately.
   - If step 0 reported a **DIFF**, raise it before planning — but do not overwrite unasked.
   - **Refresh backlog** (the `refresh-due` line above, run in the Handbook, which holds the
     chunked corpus and `.refresh-proposals/`). Each `PROPOSAL PENDING since <date>` row is a
     scrape waiting on the owner, and the weekly fallback skips it until it is landed. Put
     each one in the Blocked table as **AWAITING OWNER**, with its age in days and the
     proposal file `.refresh-proposals/<date>-<id>.md`. Any OVERDUE row is a missed cycle,
     so raise it as a blocker as well. Never land a proposal at `/open`: Grace rules are
     owner-landed.

2. **Skill-pull check (catalog drift, Tier 3 "promote, not clone"):**
   Run `node d:/SakuraHydra/Coffee_Crew_HQ/scripts/skill-pull.mjs --project .` from the current
   project root. This diffs the project's local `.claude/skills/*` against the canonical vault
   copy (falling back to the umbrella copy) and, on a real divergence, stages a proposal under
   `.skill-pull-proposals/<date>-<skill-id>.md` — it never edits a `SKILL.md` directly, same
   promote-not-clone doctrine as step 0's Tier 3.
   - If it staged nothing, say so in one line and move on.
   - A `DIRTY` line means the vault's canonical `SKILL.md` has uncommitted changes, so it is
     not a reference and nothing was compared or staged for that skill (SP-01, 2026-09-29).
     Put it in the Blocked table as **AWAITING OWNER**: commit or revert the vault edit.
     Never commit the vault at `/open`.
   - If it staged anything, call `learning_capture` (only an agent session can — the script's
     transport has no MCP path) with `problem_signature` describing the drift found and
     `applies_to` naming this project, then surface the staged proposal file path(s) to the
     user. No auto-landing.

3. **Render Scoped Roadmap (Macro View):**
   Display the high-level status matrix parsed from `PROJECT_BRAIN.md`:

   | Module / AD | Initial Scope Objective | Current Status | Key Blocker / Milestone |
   | :--- | :--- | :--- | :--- |

   **Traffic-light variant (owner, 2026-10-16).** When the arguments ask for roadmap traffic
   lights (e.g. `/open roadmap traffic with item No`), render this shape instead:

   | # | Module / AD | Initial Scope Objective | Status | Key Blocker / Milestone |
   | :-- | :--- | :--- | :---: | :--- |

   - `#` numbers every row from 1, so the owner can refer to items by number. Re-use those
     numbers in the Daily Queue and Orientation (e.g. "device passes (items 9, 10, 12)").
   - `Status` is exactly one light: 🟢 shipped/done · 🟡 built but waiting on verification
     or an owner pass · 🔴 blocked on a decision, funding or plan tier · ⚪ not yet framed.
   - Cover every module, open AD and parked epic in `PROJECT_BRAIN.md`, not only active work.
     Order by build sequence, with parked or blocked epics at the end.

4. **Sort Daily Queue (Micro View):**
   Present immediate tasks parsed from `SPRINT.md` in strict priority order:
   1. **Input blockers**
   2. **`MISS` discoveries**
   3. **Open tasks**
   4. **Open features**
   5. **Backlog `SCOPE` items**

5. **Read Tally Before Planning:**
   - **`SPEC FAULT`** → Freya/Doris is thin.
   - **`L1`** → Spec is shallow, or Hand lacks a lesson. Check the handoff's "Lesson for Hand".
   - **`L2`** → Hard problem; do not over-promote.
   - **Escalation rate** → read `LOCAL : L1 : L2` across the delegable log in SPRINT.md. It
     should drift toward LOCAL as `hand-lessons.md` grows. Flat across six lines means the
     lessons are not transferring. Say so in orientation.

6. **Route Hand first (root CLAUDE.md, owner 2026-09-24):**
   - Every queued build task goes to **Hand first** unless it carries a live reason-for-zero:
     `no-runner`, `too-large`, `unreliable-at-size` or `needs-judgement`.
   - A missing Doris entry does not block. Tag the attempt `uncatalogued`.
   - New files do not block either. Lead commits a stub plus a red test.
   - ⛔ Never route to LEAD DIRECT because the shape is new. That is the circular gate the
     order retired.
   - Check that the lessons are in place: `Coffee_Crew_HQ/hand-lessons.md` plus this repo's
     `hand-lessons.md` if one exists.
   - Flag any resolved `handoff-<nn>.md` whose "Lesson for Hand" was never landed. That is
     a close-step miss, and Hand repeats the error until it is landed.

7. **Orientation Output:**
   Print **exactly four lines** to chat:
   - Where the last session stopped
   - What is blocking, if anything
   - What is next and why, with its route (Hand first · or the reason-for-zero that stops it)
   - Any preflight failure

Stop and wait for user confirmation before starting work.
