# P4-04 slice 1: accounts core

## 0 - Output format contract
Reply with the complete file `lottery_checker/accounts.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk. Keep the final line `ACCOUNTS_MODULE_END = True` unchanged.

## 1 - Scope
Edit only `lottery_checker/accounts.py`. Replace every `raise NotImplementedError`. Keep the existing signatures, `LOGIN_TTL`, `SESSION_TTL`. Stdlib only (sqlite3, hashlib, secrets, re, contextlib). No new files.

## 2 - Gate
`py -3 -m pytest tests/test_accounts.py -q` must pass (10 tests). The test file is the only success condition.

## 3 - Behaviour
- `SCHEMA` (run with `executescript` in `__init__`; create parent dir first):
  - `users(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, created_at REAL NOT NULL, last_login REAL)`
  - `login_tokens(token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, expires_at REAL NOT NULL, used_at REAL)`
  - `sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at REAL NOT NULL)`
  - `history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, saved_at REAL NOT NULL, game TEXT NOT NULL, draw_no INTEGER NOT NULL, draw_date TEXT NOT NULL, bets TEXT NOT NULL, stake REAL NOT NULL, won REAL, claim_by TEXT, purge_after TEXT NOT NULL)` (created now, used by a later slice)
- `_hash(token)`: SHA-256 hex of the UTF-8 string. Tokens are stored ONLY as this hash, never raw.
- `normalise_email(s)`: strip, lowercase; return None unless length <= 254 and it matches `^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$`; None input gives None.
- `Accounts._db()`: a `@contextmanager` yielding a `sqlite3` connection (`row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`); commit on success, always close.
- `request_login(email)`: None if the email does not normalise. Else token = `secrets.token_urlsafe(32)`, insert its hash with the normalised email and `expires_at = clock() + LOGIN_TTL`, return the raw token.
- `redeem_login(token)`: look up the hash; None if missing or `expires_at <= clock()`. Claim it atomically with `UPDATE login_tokens SET used_at=? WHERE token_hash=? AND used_at IS NULL` and return None unless `rowcount == 1` (single use). Then `INSERT OR IGNORE` the user (email, created_at), set `last_login`, create a session (`secrets.token_urlsafe(32)`, store hash, `expires_at = clock() + SESSION_TTL`), return the raw session token.
- `user_for_session(token)`: None for empty token; join sessions to users where hash matches and `expires_at > clock()`; return `{"id": int, "email": str}` or None.
- `end_session(token)`: delete the session row by hash; no-op for empty token.
