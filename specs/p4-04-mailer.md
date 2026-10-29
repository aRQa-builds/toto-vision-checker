# P4-04 slice 4: sign-in mailer

## 0 - Output format contract
Reply with the complete file `lottery_checker/mailer.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the final line `MAILER_END = True`. The imports, `log`, `ENDPOINT`, `SUBJECT`, `BODY` and `MailError` stay exactly as they are.

## 1 - Scope
Edit only `lottery_checker/mailer.py`. Replace only the two `raise NotImplementedError` bodies (`_post`, `send_login_link`). Stdlib only (urllib already imported). No new files, no new imports.

## 2 - Gate
`py -3 -m pytest tests/test_mailer.py -q` must pass (6 tests). The test file is the only success condition.

## 3 - Behaviour
- `_post(url, headers, body)`: `urllib.request.Request(url, data=body, headers=headers, method="POST")`, `urlopen(..., timeout=30)`; return `(status, text)`. On `urllib.error.HTTPError` return `(e.code, e.read().decode("utf-8", "replace"))` instead of raising.
- `send_login_link(email, url, env=None, post=None)`:
  - `env` defaults to `os.environ`. token = `env.get("CLOUDFLARE_EMAIL_TOKEN")`, account = `env.get("CLOUDFLARE_ACCOUNT_ID")`.
  - If either is missing: when `env.get("TOTO_DEV_LINKS") == "1"` do `log.warning("DEV sign-in link: %s", url)` and return (the email address must NOT appear in the log); otherwise raise `MailError("sign-in mail is not configured")`.
  - Body: JSON-encoded to bytes with keys `from` (`env.get("TOTO_MAIL_FROM", "login@zenqi.cc")`), `to` (email), `subject` (SUBJECT), `text` (`BODY.format(url=url)`). Headers: `Authorization: Bearer <token>` and `Content-Type: application/json`.
  - Call `(post or _post)(ENDPOINT.format(account=account), headers, body)`. If it raises `OSError`, raise `MailError(f"sign-in mail could not be sent ({type(e).__name__})") from None`. If the status is not 200..299, raise `MailError(f"sign-in mail was refused (HTTP {status})")`. Error messages must never contain the token or the response text.
