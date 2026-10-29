# P4-04 slice 6c: account UI in web/index.html

Executor: Fixer (reason-for-zero `too-large`: index.html is 85 KB, over the 80 KB payload cap). Edit by hunk; never reprint the whole file.

## Scope
Edit only `web/index.html` and add `tests/test_account_ui.py`. `web/account.js` (window.TotoAccount: `createAccountClient(fetch)` -> me/requestLink/verify/logout/history/save/remove/deleteAccount; `loginTokenFromHash(hash)`) and the server routes already exist. Read `lottery_checker/accounts.py` `clean_entry` for the exact entry shape `save` must send (game, draw number and date, bets with label/numbers/stake, stake, won, claim_by). Never send serials, barcodes, photos or ticket text.

## Behaviour
1. Add `<script src="/account.js"></script>` before the main inline script.
2. Anonymous use is unchanged. Nothing account-related appears as a requirement; no step is added.
3. Top bar: a small "Sign in" button. When signed in it shows the email, "My history" and "Sign out".
4. Sign-in uses the existing `#sheet` pattern: email field, "Email me a sign-in link", then the server's generic message. Show the server's `problems` text on error. One line says the checker works without signing in.
5. On load: if `loginTokenFromHash(location.hash)` returns a token, call `verify`, then `history.replaceState` to drop the hash (token never stays in the URL or history), then refresh `me()`. On failure show the problems text. Otherwise just call `me()` (a failure there means signed out, silently).
6. On the results view, when signed in, a "Save to my history" button builds the entry from the current result and calls `save`; confirm with a short message. Beside it: "Saved for the rest of this year and next. Serial numbers are never stored. You can delete it any time." Show it only when signed in. Disable the button after a successful save so a double tap cannot save twice.
7. "My history" sheet: list entries (game, draw, date, result won/not won/pending, stake), a delete button per entry, and "Delete my account and all saved data" with a confirm step. Empty state text if none.
8. Footer privacy line becomes: "Tickets are not stored unless you sign in and choose to save them." Replace the old "Ticket details are used for this check only and are not stored." wording only.
9. Escape all user/server text the way the file already does (use its `h()` helper / textContent, never innerHTML with data).
10. Do not bump `web/sw.js` (Lead does that).

## Gate
`py -3 -m pytest tests/test_account_ui.py -q` then `py -3 -m pytest -q` (full suite). `tests/test_account_ui.py` is a static check of web/index.html: contains `/account.js` script tag, the new footer wording, none of the old wording, no `innerHTML` use added with account data, and the page does not contain the word `serial` inside any `save(` entry-building code. Lead runs the browser smoke test.
