# P4-04 slice 2: saved history

## 0 - Output format contract
Reply with the complete file `lottery_checker/accounts.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the final line `ACCOUNTS_MODULE_END = True`. Everything already implemented (schema, normalise_email, request_login, redeem_login, user_for_session, end_session, `_db`) stays exactly as it is.

## 1 - Scope
Edit only `lottery_checker/accounts.py`. Replace only the `raise NotImplementedError` bodies of `clean_entry`, `save_history`, `list_history`, `delete_history`, `delete_account`, `purge`. The imports `json` and `datetime` are already there. The `history` table already exists; use only its columns exactly as named in SCHEMA (id, user_id, saved_at, game, draw_no, draw_date, bets, stake, won, claim_by, purge_after). Stdlib only, no new files.

## 2 - Gate
`py -3 -m pytest tests/test_history.py tests/test_accounts.py -q` must pass. The tests are the only success condition.

## 3 - Behaviour
- `clean_entry(payload)` returns a NEW dict with ONLY the keys game, draw_no, draw_date, bets, stake, won, claim_by; any other key (serial, line, ...) is dropped. Raises `ValueError` (user-safe message) when:
  - payload not a dict; game not in ("toto", "4d")
  - draw_no not an int (bool excluded) in 1..99999
  - draw_date not a real ISO date `YYYY-MM-DD` (check with `date.fromisoformat`); claim_by likewise, but None is allowed
  - bets not a list of 1..30 dicts; each bet needs `label` matching `^[A-Za-z0-9 ]{1,40}$`, `numbers` a list of 1..12 strings each matching `^\d{1,4}$` (so a serial can never ride in as a number), and `stake` a number 0..10000 (bool excluded)
  - stake (whole ticket) a number 0..100000; won a number >= 0 (up to 1e9) or None (None means pending and is kept as None, never 0)
  - Output bets keep only label, numbers (list), stake (float).
- `HISTORY_LIMIT = 500` is a per-user cap.
- `save_history(user_id, payload)`: `clean_entry`, then if the user already has HISTORY_LIMIT rows raise `ValueError("Your history is full. Delete some entries first.")`. Insert with `saved_at = self.clock()`, `bets` stored as `json.dumps`, `purge_after = f"{year+1}-12-31"` where year is the UTC year of `self.clock()`. Return the new row id.
- `list_history(user_id)`: that user's rows newest first (`ORDER BY id DESC`) as dicts with keys id, saved_at, game, draw_no, draw_date, bets (json-decoded list), stake, won, claim_by.
- `delete_history(user_id, entry_id)`: delete WHERE id AND user_id match; True only if exactly one row went.
- `delete_account(user_id)`: delete the users row (foreign keys cascade sessions and history).
- `purge()`: with now = `self.clock()` and today = UTC ISO date of now, delete history with `purge_after < today`, login_tokens with `expires_at < now` OR `used_at IS NOT NULL`, sessions with `expires_at < now`.
