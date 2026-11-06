# hand-lessons.md: venture tier (Toto Vision Checker)
_Hand's knowledge base. Landed by Lead at close; Hand never writes its own lessons._

1. SQLite: use `cursor.lastrowid` and `cursor.rowcount`, not attributes of the connection. Never invent a column that is not in the schema.
2. Time: pass `timezone.utc` explicitly; never use naive local time for stored or compared timestamps.
3. When the spec states a numeric bound (for example `won` must be at most a limit), implement every bound, not just the lower one.
4. FastAPI JSON bodies: bind them as typed route parameters (`body: Model` or `body: dict`). Never call `request.body()` or `request.json()` without `await`, and never feed the result to a model constructor.
5. Take the user once per handler from the auth helper; do not look the session up again after a state change (it may be gone).
6. Browser client: await `r.json()` before reading fields; route every request through one helper that checks `r.ok` and throws an Error carrying `.problems` and `.status`; wrap the transport call in try/catch and map failure to the friendly message; send the same headers and `credentials` on every request of a kind.
7. Before calling a function that exists in the repo, read its argument order.
8. Before iterating or indexing a record field, check its type in the test fixtures (for example Toto `additional` is a single int, not a list; 4D prizes are strings and lists of strings).
9. Put each addition exactly where the spec places it (a note after the loop, not after the return) and keep every comment line the spec gives; the gate cannot see either.
10. When a spec lists lettered or numbered sub-sections of behaviour (3a, 3b, 3c, 3d), implement every one; two identical attempts stopped after the first sub-sections, and the gate then failed on exactly the omitted ones. Before replying, tick each sub-section against your diff. (Repeat of generic HL-175.)
11. Do not leave behind a variable or helper you no longer use after changing the logic that read it.
12. When loosening a regex (for example making a separator optional), add a negative test: a word or code that must still not match (DRAW, A0310). A loosened pattern that stays green proves nothing.
13. When a regex substitution must keep part of the matched text, wrap that part in a capture group and put exactly that group in the replacement; check the result against the expected string before replying.
