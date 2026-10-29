# hand-lessons.md: venture tier (Toto Vision Checker)
_Hand's knowledge base. Landed by Lead at close; Hand never writes its own lessons._

1. SQLite: use `cursor.lastrowid` and `cursor.rowcount`, not attributes of the connection. Never invent a column that is not in the schema.
2. Time: pass `timezone.utc` explicitly; never use naive local time for stored or compared timestamps.
3. When the spec states a numeric bound (for example `won` must be at most a limit), implement every bound, not just the lower one.
4. FastAPI JSON bodies: bind them as typed route parameters (`body: Model` or `body: dict`). Never call `request.body()` or `request.json()` without `await`, and never feed the result to a model constructor.
5. Take the user once per handler from the auth helper; do not look the session up again after a state change (it may be gone).
6. Browser client: await `r.json()` before reading fields; route every request through one helper that checks `r.ok` and throws an Error carrying `.problems` and `.status`; wrap the transport call in try/catch and map failure to the friendly message; send the same headers and `credentials` on every request of a kind.
7. Before calling a function that exists in the repo, read its argument order.
