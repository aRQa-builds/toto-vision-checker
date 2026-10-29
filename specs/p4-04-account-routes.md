# P4-04 slice 5: account routes

## 0 - Output format contract
Reply with the complete file `lottery_checker/account_routes.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the final line `ROUTES_END = True`. The imports, `COOKIE`, `audit`, `EmailIn` and `TokenIn` stay as they are (do not add imports; `date` is imported on purpose, see the daily purge).

## 1 - Scope
Edit only `lottery_checker/account_routes.py`. Replace only the body of `add_account_routes`. `api.py` already calls it. Use only these existing APIs, with exactly these names:
- `Accounts(path)` with `purge()`, `request_login(email) -> token|None`, `redeem_login(token) -> session|None`, `user_for_session(token) -> {"id","email"}|None`, `end_session(token)`, `save_history(user_id, payload) -> id` (raises ValueError with a user-safe message), `list_history(user_id) -> list`, `delete_history(user_id, entry_id) -> bool`, `delete_account(user_id)`.
- `LinkLimiter()` with `allow(email, ip) -> bool`; `normalise_email(s)`; `SESSION_TTL`; `mailer.send_login_link(email, url)` and `mailer.MailError`.
Do not touch any other file.

## 2 - Gate
`py -3 -m pytest tests/test_account_routes.py tests/test_api.py -q` must pass. The test files are the only success condition.

## 3 - Behaviour
Inside `add_account_routes(app, data_dir, client_ip, send_link=None)`:
- `accounts = Accounts(Path(data_dir) / "accounts.db")`; call `accounts.purge()` once; `last_purge = {"day": date.today()}`; `limiter = LinkLimiter()`; `send = send_link or mailer.send_login_link`; `public = os.environ.get("TOTO_PUBLIC_URL", "https://toto.zenqi.cc").rstrip("/")`.
- `csrf(request)`: if header `x-toto` is not `"1"`, raise `HTTPException(403, {"problems": ["Missing request header."]})`. Every POST and DELETE route calls it first (including `/api/auth/request` and `/api/auth/verify`).
- `current(request)`: `accounts.user_for_session(request.cookies.get(COOKIE))`, else `HTTPException(401, {"problems": ["Sign in to use your history."]})`.
- `POST /api/auth/request` (body `EmailIn`): csrf; `normalise_email` else 422 `{"problems": ["That doesn't look like an email address."]}`; `limiter.allow(email, client_ip(request))` else 429 `{"problems": ["Too many sign-in emails. Try again later."]}`; if `date.today()` differs from `last_purge["day"]`, call `accounts.purge()` and update it; `token = accounts.request_login(email)`; `send(email, f"{public}/#login={token}")`; on `mailer.MailError` log `audit.warning("auth: sign-in mail failed")` (no email) and raise 503 `{"problems": ["We couldn't send the email. Try again later."]}`. Success returns `{"ok": True, "message": "If that address is valid, a sign-in link is on its way."}` (the same for every valid-looking address).
- `POST /api/auth/verify` (body `TokenIn`): csrf; `session = accounts.redeem_login(body.token)` else 400 `{"problems": ["That sign-in link has expired or was already used. Ask for a new one."]}`; `user = accounts.user_for_session(session)`; `audit.info("auth: signed in user=%s", user["id"])`; return `JSONResponse({"ok": True, "email": user["email"]})` with `set_cookie(COOKIE, session, max_age=SESSION_TTL, httponly=True, samesite="lax", path="/", secure=request.headers.get("x-forwarded-proto") == "https")`.
- `POST /api/auth/logout`: csrf; end the session for the cookie; if a user was found `audit.info("auth: signed out user=%s", id)`; return `JSONResponse({"ok": True})` with the cookie deleted (`delete_cookie(COOKIE, path="/")`).
- `GET /api/me`: `{"signed_in": True, "email": email}` or `{"signed_in": False}`. No csrf.
- `GET /api/history`: `{"entries": accounts.list_history(current(request)["id"])}`. No csrf.
- `POST /api/history` (body annotated `body: dict`): csrf; `current`; `save_history`; on ValueError 422 `{"problems": [str(e)]}`; `audit.info("history: saved user=%s entry=%s", ...)`; return `{"ok": True, "id": id}`.
- `DELETE /api/history/{entry_id}` (int): csrf; current; `delete_history` False gives 404 `{"problems": ["No such entry."]}`; `audit.info("history: deleted user=%s entry=%s", ...)`; return `{"ok": True}`.
- `DELETE /api/account`: csrf; current; `delete_account`; `audit.info("account: deleted user=%s", id)`; return `JSONResponse({"ok": True})` with the cookie deleted.
- Never log the email address anywhere.
