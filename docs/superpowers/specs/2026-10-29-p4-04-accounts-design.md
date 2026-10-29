# P4-04 Accounts and saved ticket history: design

Status: approved by owner in chat, 2026-10-29. Not yet planned or built.

## Goal
Optional email sign-in so a user can save checked tickets and see them later. Anonymous
use is unchanged: nothing is required, nothing is auto-saved, and every existing flow
behaves exactly as today.

## Decisions (owner)
- Purpose: saved ticket history.
- Storage: local SQLite on Grayskull, `data/accounts.db` (git-ignored under `data/`).
- Sign-in: email magic link, sent through Cloudflare Email Service from `login@zenqi.cc`.
- Saved data: bets and outcome, no serials, kept to the end of the year after saving.

## Sessions and magic link
- Server-side sessions in SQLite. Cookie holds a random token; the database stores only its
  hash. `Secure; HttpOnly; SameSite=Lax`, 30 days. State-changing calls also need a custom
  header (CSRF guard).
- `POST /api/auth/request {email}`: emails a one-time link. Token is 32 random bytes, stored
  hashed, valid 15 minutes, single use. The reply is always "if that address is valid, a link
  is on its way" (no account enumeration).
- The link opens `/auth/verify#token`; the page POSTs the token, so it never reaches server
  logs or referrers and mail-scanner prefetch cannot consume it.
- Limits on link sending: per email and per connection per hour, plus a site-wide daily cap
  (defaults 3 / 10 / set at build time, env-tunable like `limits.py`).
- Sign-out ends the session. Expired tokens and sessions are purged.

## Data (`lottery_checker/accounts.py` owns the schema)
- `users`: id, email (lowercased), created_at, last_login.
- `login_tokens`: token_hash, email, expires_at, used_at.
- `sessions`: token_hash, user_id, expires_at.
- `history`: id, user_id, saved_at, game, draw_no, draw_date, bets (JSON), stake, result
  (JSON), payout, claim_by, purge_after.
- Never saved: printed serial, barcode, the photo. One function strips serial fields from the
  parsed `TicketDraft`; a test asserts no serial-like value survives into a row.
- Retention: `purge_after` is the end of the year after saving; purge at server start and
  daily.
- The email is the only identifier stored and is never logged.

## Endpoints
- `GET /api/history`, `POST /api/history`, `DELETE /api/history/{id}`, `DELETE /api/account`.
- All return 401 when signed out. Queries are scoped to the session's user in the query itself.
- No endpoint lists other users' data or any results (existing guardrail tests stay).

## Mailer (`lottery_checker/mailer.py`)
- `send_login_link(email, url)` calls the Cloudflare Email Service API. Token and account id
  come from the environment on Grayskull, never the repo.
- No token configured: the link is written to `logs\web.log` only when `TOTO_DEV_LINKS=1`.
- First implementation step: confirm the API shape and domain onboarding (SPF/DKIM) against
  current Cloudflare docs. Not assumed here.

## UI (`web/index.html`)
- Header "Sign in (optional)" link, email box, "check your inbox" state.
- Signed in: "My history" panel, "Save to my history" on the reveal step, sign out, delete one
  entry, delete my account and data.
- Privacy line becomes: "Tickets are not stored unless you sign in and choose to save them."
- Bump `VERSION` in `web/sw.js`.

## Testing
pytest only; no real email, no network. A fake mailer captures the link. Covers: single-use
and expiry, hashed storage, enumeration-safe replies, both rate limits, cookie flags,
cross-user isolation, serial stripping, purge, account deletion. The existing 494 tests must
stay green; anonymous behaviour must not change.

## Delivery (rig rules)
Per slice: Lead writes `specs/p4-04-<slice>.md` naming its gate command, a stub with a
sentinel, and a red test. Hand first via `rig-loop --repo` after `rig-preflight`.
1. `accounts.py`: schema, tokens, sessions.
2. History CRUD, serial stripping, purge.
3. `mailer.py`.
4. API routes and rate limits.
5. UI (likely Fixer: `index.html` is one large file).
Catalogs: Iris (tokens, credentials), Edith (audit of sign-in and deletes), Grace at FRAME
(personal data). Auth data touch: no market data involved, so cloud escalation is allowed
after scrubbing.

## Out of scope for v1
Passwords, social login, history export, editing saved entries, the Android app.

## Open items
- Rate-limit defaults and exact cookie lifetime to confirm at slice 4.
- Cloudflare Email Service domain onboarding for `zenqi.cc` (owner action if not done).
- Whether the Grace FRAME pass changes retention or consent wording.
