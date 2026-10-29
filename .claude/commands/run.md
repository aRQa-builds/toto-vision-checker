---
description: Run one delegable slice through Hand — preflight, then rig-loop (attempt, one retry, handoff on second failure).
argument-hint: --brief <spec.md> --target <file> --gate "<command>" [--shape <DORIS-ID>] [--repo DIR]
model: sonnet
effort: low
---

# /run

Mechanical execution of a slice the Lead has already planned. This command does not plan,
judge or attribute. Model and effort are pinned in the frontmatter so the throttle is
automatic: this turn runs on Sonnet at low effort, and the session model resumes on the
next prompt.

**Hand first, always.** Every slice goes to Hand (and Scout for read-and-report) before any
cloud tier. Fixer or Lead is reached only when Hand or Scout has failed, or when the Lead
explicitly calls for an escalation, a consult or a fix. A cheaper Claude pin here does not
replace Hand; it only makes the wrapper around Hand cheap.

Arguments: `$ARGUMENTS`

## Preconditions — stop if any is missing

- `--brief` names a spec file that exists on disk (a spec that exists only in chat does not exist).
- `--target` names a file that exists. For creation work the Lead has committed a stub.
- `--gate` is a behavioural command, not a compile gate alone.

If a precondition fails, say which one in one line and stop. Do not write the spec, the stub
or the test yourself.

## Steps

1. **Preflight.** `node d:/SakuraHydra/Coffee_Crew_HQ/scripts/rig-preflight.mjs`
   - Exit 1 → **RESOURCE FAULT**. Report it and stop. No attempt is made. Never touch LM Studio.
2. **Loop.** `node d:/SakuraHydra/Coffee_Crew_HQ/scripts/rig-loop.mjs $ARGUMENTS`
   Add `--repo <cwd>` when running from a venture repo and it was not passed. Run it in the
   foreground with a 600 s Bash timeout; if it needs longer, run it in the background and wait
   for the exit notification. Do not poll.
3. **Report the exit code, verbatim meaning:**

| Exit | Meaning | Report |
|---|---|---|
| 0 | Gate green (attempt 1 or 2). Change applied, not committed | Show `git diff --stat` on the target. Candidate **LOCAL** |
| 1 | Escalated — both attempts failed. Target reverted; `handoff-<nn>.md` written | Path of the handoff file. Next tier is `/fix <handoff>`. If the script printed **REPEAT FAILURE**, say "Lead check" instead: identical failures point at the spec or test (also Lead if `no-cloud-escalation`) |
| 2 | Usage error, dirty target, or gate already green | The script's message. Nothing to delegate |
| 3 | RESOURCE FAULT or VOID. Not a counted attempt | The script's message. Re-run once the station is clear |
| 4 | Held by VIS (session paused or aborted) | The script's message |
| 5 | Hand lane busy past `--wait-max` (3600 s). Not an attempt, no handoff | "Lane busy", plus the last position line. Re-run later. Not a Hand failure |
| 6 | QUEUE CANCELLED: Lead dropped or cleared this ticket. No attempt, no handoff | The reason the script printed. Not a Hand failure |
| 7 | HARNESS FAULT: delegate missing or died before any model call. No attempt, no handoff | The script's message. Check that HQ's `rig-loop.mjs` was called with `--repo` |

A busy lane is a wait, not a failure: the script prints "You are N of M, est. start ~X min".
`node d:/SakuraHydra/Coffee_Crew_HQ/scripts/rig-loop.mjs --queue-status` shows the queue.
`--lane-report` rolls up Hand calls and seconds per week, month and repo.

## Never

- Never assign a tally label. "Candidate LOCAL" is the most this command says; attribution is
  `/close` work (Clara).
- Never decide `no-cloud-escalation`, never scrub, never send the handoff anywhere.
- Never commit, never retry beyond what `rig-loop.mjs` already does, never edit the target
  after a green gate.
- Never fix a failure yourself. Escalation is a separate, Lead-initiated step.
