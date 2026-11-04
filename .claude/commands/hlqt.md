---
description: HLQT dashboard — the issued Hand-lane ticket, the next 3 (up to 10), the wait list, and the heartbeat verdict.
argument-hint: [--next N]
model: sonnet
effort: low
---

# /hlqt

Read-only. Shows the shared Hand lane on call. It never takes the lane, reaps, cancels, reorders or touches Ollama or LM Studio.

!bash node d:/SakuraHydra/Coffee_Crew_HQ/scripts/hlqt-board.mjs $ARGUMENTS

!bash node d:/SakuraHydra/Coffee_Crew_HQ/scripts/hlqt-check.mjs

## Instructions for Claude

Print the board above exactly as it is, then the one-line check verdict under it. Add nothing else unless the
verdict is WARN or FAULT, in which case name the finding in one line. Do not act on it: cancelling or reordering
tickets is the owner's call (`rig-loop --drop`, `--prioritize`).
