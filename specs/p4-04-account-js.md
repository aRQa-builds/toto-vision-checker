# P4-04 slice 6a: browser account client (web/account.js)

## 0 - Output format contract
Reply with the complete file `web/account.js`, line 1 to the last line, in one fenced javascript block. Never `/* ... existing code ... */`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the wrapper, the `const api = {...}` / export lines and the final comment line `/* ACCOUNT_JS_END */`.

## 1 - Scope
Edit only `web/account.js`: fill in the bodies of `createAccountClient` and `loginTokenFromHash`. Plain script (no import/export, no async generators, no libraries). Do not touch any other file.

## 2 - Gate
`node --test tests/web/account.test.cjs` must pass. The test file is the only success condition.

## 3 - Behaviour
`createAccountClient(fetchFn)` returns an object with async methods. Every request calls `fetchFn(url, opts)` with `opts = {method, headers, credentials: "same-origin"}` plus `body` when there is one. `headers` is `{}` for GET. For POST and DELETE it is `{"X-Toto": "1"}`, and also `"Content-Type": "application/json"` when a body is sent. Bodies are `JSON.stringify(...)`.
- `me()` GET `/api/me`, returns the parsed JSON.
- `requestLink(email)` POST `/api/auth/request` body `{email}`, returns parsed JSON.
- `verify(token)` POST `/api/auth/verify` body `{token}`, returns parsed JSON.
- `logout()` POST `/api/auth/logout` (no body, header X-Toto only), returns parsed JSON.
- `history()` GET `/api/history`, returns the `entries` array.
- `save(entry)` POST `/api/history` body is the entry itself, returns the `id` field.
- `remove(id)` DELETE `/api/history/<id>`, returns parsed JSON.
- `deleteAccount()` DELETE `/api/account`, returns parsed JSON.
Errors: if `fetchFn` throws, throw an Error whose message and single `problems` entry is `Can't reach the checker right now. Try again in a minute.` If the response is not ok, parse `await r.json()` (ignore a parse failure, treat as null); `problems` is `data.detail.problems` when it is an array, else `["Something went wrong. Try again."]`; throw an Error with `message = problems[0]`, `problems`, and `status = r.status`.

`loginTokenFromHash(hash)` returns the token when `hash` is a string matching exactly `^#login=([A-Za-z0-9_-]{20,200})$`, else `null`.
