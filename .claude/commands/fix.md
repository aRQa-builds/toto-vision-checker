---
description: L1 — Fixer fixes forward from one handoff file. Stops and calls a Lead check when it stalls.
argument-hint: <handoff-nn.md>
model: sonnet
effort: medium
---

# /fix

L1 escalation. Hand has already failed twice on this slice; this is the first cloud tier.
Model and effort are pinned in the frontmatter so the throttle is automatic.

Handoff: `$ARGUMENTS`

## Before starting

- Read the handoff file and nothing else: no repo tour, no @codebase. The brief, target and
  gate are named inside it.
- If the handoff carries the **🔁 REPEAT FAILURE** banner, do not fix. Write
  `Lead check requested — repeat failure` under **Outcome** and stop. That one belongs to Lead.
- If it is tagged `no-cloud-escalation`, stop. It goes to Lead locally.

## Fix forward

1. `git apply` the handoff's diff. Start from Hand's attempt, not from scratch.
2. Fix what Hand got wrong in the named target. Run the named gate after each change.
3. Green → fill **Outcome** and **Lesson for Hand** (one imperative line per distinct miss,
   no values). Lead lands the lesson at close. Do not commit.

## Stall rule — stop and call a Lead check

Stop as soon as any of these is true. Do not try "one more thing":

| Trigger | Why it means Lead |
|---|---|
| The gate fails **the same way twice in a row** after a change | Your change did nothing, so you are looping |
| **3 failed gate runs** in total | Not converging |
| The fix needs a file other than the target, or a change to the spec or the test | Out of the slice's scope; that is a re-plan |
| The spec is ambiguous on a line the fix depends on | Rule 2: name the line, do not choose |

On a stop, write under **Outcome** in the handoff file:

```
Lead check requested — <trigger> · gate runs: <n> · last failure: <one line, no values>
```

Leave the working tree as it is so Lead can see the attempt. Then report that one line in chat.
Lead decides: SPEC FAULT and re-plan, fix it as L2, or send it back with a narrower brief.

## Never

- Never assign the tally label. L1 vs L2 is `/close` work.
- Never edit `hand-lessons.md` directly. Propose the lesson in the handoff.
- Never send the handoff anywhere or decide `no-cloud-escalation`.
