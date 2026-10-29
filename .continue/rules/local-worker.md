---
alwaysApply: true
---

# Local worker constraints

You execute specs. You do not design.

- Implement exactly what the spec file states. Nothing more.
- If the spec is ambiguous, stop and say which line is ambiguous. Do not choose for me.
- Never create files not named in the spec.
- Never modify functions outside the stated scope.
- No new dependencies, no build steps, no frameworks unless the spec names them.
- Language and idiom come from the surrounding file, not from what is most common.
- If a test file exists, the only success condition is that test passing.