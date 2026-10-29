# Web checker (P4-02): run it on Grayskull

Decision 21 Oct 2026: option 1. A small Python API on Grayskull runs the same
tested package and serves the Arcade Drum page from the same address. The page
only talks to the API, so the API can later move to a cloud host (or the logic
into the browser) without changing the page.

## Files
- `lottery_checker/api.py`: the API and the page server.
- `lottery_checker/store.py`: reads captured draws from `data\draws\`.
- `web/index.html`: the page (one file, no build step).
- `tools/run-web.cmd`: starts it on `http://127.0.0.1:8765`.
- `requirements.txt`: `fastapi`, `uvicorn` (plus `pytest`, `httpx` for tests).

## First run (local only)
```
cd D:\SakuraHydra\HavenPalms\Toto_Vision_Checker
py -3 -m pip install -r requirements.txt
py -3 -m pytest -q              # expect 453 passed (22 Oct 2026)
tools\run-web.cmd
```
Open http://127.0.0.1:8765 on Grayskull. Try the TOTO and 4D example buttons:
they use draws 4227 and 5551 from the capture, so they reveal straight away.

## What the page does
1. **Ticket**: type the ticket as printed (or short forms). Errors point at the line.
2. **Unlock**: if the draw was captured, "Reveal my result". If not, "Unlock on
   official page" opens the official draw in a new tab; coming back shows the
   "Welcome back" sheet.
3. **Confirm**: type the winning numbers (TOTO 6 + Additional, optional Group 1-4
   amounts; 4D all 23). "Use my screenshot" stays greyed out until a Vision key
   is set.
4. **Reveal**: headline, winning numbers, your boards lit up, per-line amounts,
   stake vs PRICE, claim-by date, credit line.

## Photos (P3-01, P3-02; live 22 Oct 2026)
- Google Cloud project `zenqi-toto` (org ralf-qa-org), Cloud Vision API, API key
  `toto-checker-grayskull` restricted to Cloud Vision API. The key lives only in
  Grayskull's user environment variable `GOOGLE_VISION_API_KEY`. After changing it,
  re-run `tools\setup-web.ps1` (the server reads it at start).
- **Scan ticket** opens the phone's back camera straight away (`capture="environment"`);
  **Upload photo** picks an existing one; pasting a picture (Ctrl+V, long-press Paste)
  on the ticket step works too. All go to `/api/ticket/photo` -> `ticket_ocr.py` -> the ticket
  as typed text -> the normal confirm screen, marked "Read from your photo". If it
  can't make a ready ticket, the text goes into the box to fix by hand.
- **Several tickets at once** (22 Oct): "Upload photos" takes up to 5 tickets; they are
  read one after another, then confirmed and revealed in turn ("Ticket 2 of 5"), with a
  total at the end. Extra photos beyond 5 are not read (the page says so). Every photo
  still counts against the per-person photo limit on the server, so the cap holds even
  for a changed page.
- **Draw dates are checked against draw numbers** (fix 22 Oct): the official page's
  "Next Draw" date was read as the draw's date when Vision split it onto its own line
  (draws 4216-4221 were saved as 22 Oct). Dates now skip any "Next Draw" date and must
  fit the draw number (TOTO ~3.5 days a draw from 4227 = 19 Oct 2026, 4D ~7/3 from 5551
  = 21 Oct 2026, within 12 days); otherwise the ticket's printed date is used, or the
  date counts as missing. Shared records with an impossible date are void.
- **Paste screenshot** (unlock sheet, and on each draw card): screenshot the official
  page, switch back, tap Paste; the clipboard image is read directly (the browser may
  ask once). Ctrl+V / long-press Paste anywhere on the unlock or results step does the
  same. **Upload screenshot** is the fallback. A later screenshot of just the prize
  table adds its amounts to what the first one read.
- **Several draws at once** (22 Oct): pick all screenshots in one go (up to 12).
  `/api/results/screenshots` reads each one and sorts it to the ticket's draws by
  draw number, else by draw date; a prize-table screenshot joins the one before it,
  and on a one-draw ticket goes to that draw. Notes say what didn't fit (a draw not
  on the ticket, a draw with no screenshot yet). Phones lead with "Choose screenshot"
  (screenshots go to Photos, not the clipboard); computers lead with Paste.
- Screenshots (single, older endpoint): `/api/results/screenshot` fills the typed-results
  form (numbers, Group 1-4 amounts); the user still taps Reveal. A screenshot of a
  different draw or game is refused with a message.
- The browser shrinks images to 2000 px JPEG before upload. Nothing is kept.
- Limits (owner's rules, 22 Oct 11:01; `lottery_checker/limits.py`):
  - Ticket photos: 20 per person (connection) an hour, 150 a day for the whole site
    (env `TOTO_VISION_PER_HOUR`, `TOTO_VISION_PER_DAY`).
  - Testing phase: 200 an hour, 1000 a day (env `TOTO_TESTING_PER_HOUR`,
    `TOTO_TESTING_PER_DAY`) for a limited time. `tools\testing-phase.ps1 -Start` (7 days,
    or `-Days n`), `-Renew` (7 more days from now), `-End` (close out for deployment),
    no switch = show. Writes `data\testing_phase.json`; read on every request, no
    restart. When it runs out, normal limits come back by themselves; the site banner
    says "renew or close out" on the last day and `setup-web.ps1` prints the state.
  - Official-result screenshots: no per-person limit (people upload a whole sitting at
    once; up to 40 per request, the page sends more in groups of 40, up to 200). Only a
    site-wide safety net of 1000 a day (env `TOTO_SCREENSHOTS_PER_DAY`, 0 = none).
    Screenshots of draws not on the ticket are still kept for the shared results.
  - All counters are in memory and reset when the server restarts. Keep the Google
    Cloud quota (Quotas, Cloud Vision) as the last backstop.
- Check Vision: `py -3 tools\vision_smoke.py` (2 billed requests).
- Test tickets: `tests\fixtures\tickets\*.jpg` (SPECIMEN, fake serials): Ordinary 4227,
  System 7 4227, 2 draws 4227-4228, 4 draws 4224-4227, 4D 5551.

## Shared results from users' screenshots (P3-07, owner's decisions 22 Oct 2026)
`lottery_checker/shared.py`, files in `data/shared/<game>/<draw>.json`.
- Every complete screenshot read is an entry for its draw: who (salted hash of the
  connection address, `data/shared/.salt`; the address is never stored), source device
  (short label, e.g. "Android · Chrome") and time (UTC).
- Served to other users only when two different people read exactly the same numbers
  and the same draw date, and nobody read anything else.
- **Any conflict voids the draw for good** (10:38): one different reading of the
  numbers or the date, even after two agreed, and the draw is never served; the file
  records when and why (`void`). Users then add their own screenshot, exactly as when
  there is no shared data, and the unlock screen tells them why.
- Group 1-4 amounts each need two people and no disagreement, else that group stays
  pending. Groups 5-7 are fixed by the rules.
- Captured official results always win; nothing is stored for a captured draw.
- Draws from 1 January of last year onwards are kept (changed 22 Oct 15:04 from the
  180-day claim period, so the whole year can be built from screenshots).
- Shown as "From other users' screenshots of the official page (two agreed)", never
  as official. On the unlock step the button reads **"Use crowd results · Reveal"**.
- Stored data is the default, never the only way (10:40): when a draw has a captured or
  shared result, the page offers Reveal straight away, plus "Choose / Paste screenshot"
  and "Type the numbers myself". The user's own numbers then take priority for that check
  (shown "As entered by you").
- Off switch: set `TOTO_SHARED_RESULTS=0` (user environment on Grayskull) and re-run
  `tools\setup-web.ps1`. To drop one draw, delete its file in `data\shared\`.

## Building the year's results from crowd screenshots (owner, 22 Oct 2026)
No pulling from singaporepools.com.sg for history (decision in
`results-source-decision.md`). Instead:
- **Help complete TOTO/4D 2026** card on the unlock and reveal steps (when photo reading
  is on): progress bar, and every draw of the year still missing or waiting for a second
  person, each a direct link to that draw's official page (`?sppl=` deep link). Gold
  chips (•) need just one more screenshot. **Add screenshots** (**Paste screenshot** on
  computers) take any number at once (sent 40 at a time) with no ticket needed.
- `GET /api/results/wanted?game=toto|4d`: draw numbers, state (`missing`/`waiting`) and
  official link only. Void draws are not asked for. Range: `YEAR_FIRST` in
  `results_db.py` (2026: TOTO 4144, 4D 5426) to the latest draw that should be out by
  now (draw-day calendar Mon/Thu, Wed/Sat/Sun; a draw counts from 22:00 SGT).
- `POST /api/results/contribute {images, game?}`: reads each screenshot, groups by draw,
  submits complete reads to shared results. Answers per draw: added, state now
  (`waiting`/`agreed`/`void`), or why not (incomplete, official result already held,
  too old). Same site-wide screenshot safety net as above.
- **Share from the phone (22 Oct 2026).** Phones save screenshots to Photos, never the
  clipboard, so the Paste button is now hidden on phones (computers keep Paste and Upload).
  With the app installed, **Share** on a screenshot offers *TOTO Check* (web manifest
  `share_target`, `POST /share-target`, files named `screenshots`). The service worker
  keeps the pictures in a cache called `toto-shared` on the phone, redirects to
  `/?shared=N`, and the page reads them back, deletes them and sends them to
  `/api/results/contribute`. If a share ever reaches the server, `POST /share-target` reads
  and stores nothing and redirects to `/?shared=0`. A share starts a fresh page, so it has
  no ticket in memory (none is stored): shared screenshots go to the crowd results, not
  to a ticket's unlock step. Needs a Chrome-installed app (WebAPK); Brave may not offer it.
  Bump `VERSION` in `sw.js` when the page changes; restart the server after any `.py`
  change (routes load at start).
- **One-tap unlock in the Android app (22 Oct 2026, `android\` folder, not yet built).** The app
  adds `window.TotoNative.capture(id, officialUrl)`; the page calls it for each draw on the
  ticket that we hold no result for (at most 4), sends the pictures to
  `/api/results/screenshots`, and goes straight to the reveal, with a 3-second sealed-box
  animation hiding the work (minimum 2.4 s so it never flashes). Any failure, or a read that
  is missing numbers, falls back to the manual steps. `/api/health` carries `auto_capture`;
  set `TOTO_AUTO_CAPTURE=0` and restart to switch it off for every app at once. App entries
  show as "Android · App" in shared results. Rules and build steps: `android\README.md`.
- **Failed reads leave a trace.** A screenshot that looks like the top of a result (game and
  draw number found) but whose numbers did not all read writes one line to `logs\web.log`
  (`screenshot read came up short: ...`) and one file `data\failed\screens\<time>_<game>_<draw>.json`
  holding the OCR text, the word boxes and what was missing (never the image; newest 60
  kept; `diag.py`). The user is told what was read ("only 5 of 6 read: ...") and to
  take a fresh shot of the top, not to scroll down.
- **Learning record (22 Oct 2026).** The same event is appended, never capped, to
  `data\learning\vision_reads.jsonl` (when, game, draw, what was missing, the numbers
  that did read, the OCR text; moved aside to `.1` past 5 MB). Results screenshots only:
  ticket photos are never recorded because their text carries serial numbers. Run
  `py -3 tools\vision_review.py` to line each logged read up against the true result
  (official capture first, else a crowd result two people agreed on) and name the
  mistake: a number dropped, an extra one, or a wrong one, with a summary and
  `data\learning\vision_review.csv`. Reads for draws with no true result yet show
  "no truth yet" until one exists. No Vision calls, no web requests.
- **One person's screenshot is in the database (22 Oct 2026).** A draw that only one person
  has sent is compiled with its numbers and the Group 1-4 amounts that screenshot showed
  (state `waiting`, `shares_confirmed` false, CSV note "one person's screenshot so far, not
  yet confirmed"). It is still never used to check a ticket until a second person agrees.
  The Help card now reads "N ready · N waiting · N to go" (bar: teal ready, gold waiting)
  instead of "1 of 84 draws ready"; `/api/results/wanted` adds `waiting`, `missing`, `on_file`.
- Results database (`results_db.py`): `data\results\<game>.json`, `<game>.csv`,
  `<game>-<year>.csv` (every draw number of the year, gaps `missing`), recompiled after
  every capture and screenshot. CLI: `py -3 -m lottery_checker.results_db [game]
  [--draw N] [--date YYYY-MM-DD]`.
- Owner view `/owner` (and `/api/owner/results`, `/api/owner/results.csv?year=`): locked
  by `data\owner.key`; `py -3 -m lottery_checker.owner` prints the Grayskull and phone
  links (key after `#`, never sent to the server). `--new` replaces the key.

## Guardrails built in
| Guardrail | Where |
|---|---|
| No public results feed: a check returns only the draws on that ticket; the wanted list has draw numbers and links only; the only list of results is the locked owner view | `api.py`, `test_no_endpoint_lists_results`, `test_wanted_endpoint_lists_numbers_never_results` |
| Server never fetches Singapore Pools | only `ingest.py` does, once after each draw |
| Singapore Pools credited on captured results; typed results say "as entered by you" | `reveal.py` |
| 60 API calls a minute per client (uses `CF-Connecting-IP` behind Cloudflare) | `api.py` middleware |
| Field size caps (ticket 4,000 chars, result 2,000, 3 screenshots of 7 MB) | request models |
| Binds to 127.0.0.1 only; nothing listens on the LAN | `run-web.cmd`, `main()` |
| Ticket text not stored or logged (access log off) | `main()` |
| No API docs page, `nosniff`, `no-referrer`, `X-Frame-Options: DENY`, `no-store` on API | `api.py` |

## Going public at toto.zenqi.cc
Uses Cloudflare Tunnel (`cloudflared`), so no router port is opened and the PC
stays unreachable except through the tunnel.

1. Quick test, no account needed: `cloudflared tunnel --url http://127.0.0.1:8765`
   prints a temporary `trycloudflare.com` address to try on your phone.
2. Permanent, live since 22 Oct 2026: `toto.zenqi.cc` is a published application
   (route) on the existing dashboard-managed tunnel **sakura-hud**, whose only replica
   is the `Cloudflared` Windows service on Grayskull (token file
   `C:\ProgramData\cloudflared\token`, also serves hud-origin.zenqi.cc). Route:
   Service URL `http://127.0.0.1:8765` (the `http://` matters), no path, defaults,
   no Access policy. The route lives in the dashboard (Networks > Tunnels > sakura-hud >
   Routes), not in a local config file.
   - Check: `powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1 -Status`
     (service state plus page, API and install files over https://toto.zenqi.cc).
   - Kill switch for toto only: disable or delete the toto.zenqi.cc route in the
     dashboard. Do NOT stop the Cloudflared service or run `-Stop`/`-Force`: that
     takes hud down too.
   - 502 "Host Error" on toto = nothing answering on 127.0.0.1:8765: run
     `tools\setup-web.ps1`.
   - `setup-tunnel.ps1` without `-Status` builds a separate named tunnel; it is only for
     a PC without the sakura-hud service, and refuses to replace it unless `-Force`.
3. Keep the web checker running: `powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1`
   registers `\ZenQi\TotoChecker\Web checker`, which starts at logon and runs
   `tools\web-service.cmd` hidden: that loop starts the server again 10 s after it stops
   for any reason and logs every start and stop to `logs\web.log`. Re-running the script
   is safe: it stops the old copy (and any `run-web.cmd` copy) first. Add `-AtStartup` (from an
   Administrator PowerShell) to start at boot before anyone logs on. `-Stop`, `-Disable`,
   `-Enable` and `-Remove` do what they say. After starting, it checks every install
   file too: a server started from older code answers /api/health but 404s routes added
   since (happened 22 Oct). After changing any .py file, run it again.

The privacy line reads "Tickets are not stored unless you sign in and choose
to save them." (P4-04, 29 Oct 2026). That stays true only while saving is an
explicit button and the saved entry carries no serial, barcode, photo or ticket
text.

## Accounts and saved history (P4-04, 29 Oct 2026)
Optional. Nothing about checking a ticket needs an account.

| Route | What |
|---|---|
| `POST /api/auth/request` `{email}` | Emails a sign-in link (`<TOTO_PUBLIC_URL or https://toto.zenqi.cc>/#login=<token>`). The same reply for every valid-looking address; 429 past the mail limits; 503 if the mail could not be sent. |
| `POST /api/auth/verify` `{token}` | Redeems the token once, sets the `toto_session` cookie (HttpOnly, SameSite=Lax, Secure over HTTPS, 30 days). |
| `POST /api/auth/logout`, `GET /api/me` | End the session; who am I. |
| `GET/POST /api/history`, `DELETE /api/history/{id}` | Saved entries for the signed-in user. |
| `DELETE /api/account` | Deletes the user, sessions and all history. |

Every POST and DELETE needs the header `X-Toto: 1` (CSRF guard). Audit lines on
logger `toto.accounts` carry the user id only, never the address. History is
purged at start and once a day.

To switch on at Grayskull: onboard `zenqi.cc` for Cloudflare Email Sending
(SPF/DKIM), create a token with "Email Sending: Edit", set
`CLOUDFLARE_EMAIL_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` for the service, then
re-run `tools\setup-web.ps1`. Without them sign-in mail fails with a 503.

## Known limits
- Grayskull off, asleep or rebooting = site down.
- One person on two networks (wifi and mobile) counts as two people for shared results.
- 4D ticket photo reading is untested on a real ticket (test ticket 05 only).
- Group TOTO / iTOTO unit tickets are refused with a message (payout per unit not
  worked out yet).
- Fonts load from Google Fonts; without them the page falls back to system fonts.
