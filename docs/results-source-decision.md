# P2-02 Results source and terms (17 Oct 2026)

Decision note for where draw results come from. Not legal advice.

## Finding: Singapore Pools' website terms block scraping

Singapore Pools "Website & Mobile App Terms and Conditions"
(https://www.singaporepools.com.sg/en/rules/pages/website-tnc.html), read 17 Oct 2026:

| Clause | What it says |
|---|---|
| 2.1 | Limited licence to view, cache and print pages. |
| 2.2.1 | Commercial exploitation prohibited; permitted use is "limited to your personal use only". |
| 2.2.3 | No use "as part of any systematic or automated data collection activities", naming data mining, data harvesting and scraping. |
| 4.1 | Singapore Pools claims IP in the site and its content. Results data is not named specifically. |
| 4.2 | No reproducing or distributing content, except with "written express permission of the Company" or where the law permits. |

robots.txt only blocks SharePoint service paths and tender files, but robots.txt does not override the terms above.

So a public product (free or paid) that scrapes singaporepools.com.sg results pages, on a cron or as a backfill, conflicts with cl. 2.2.1 and 2.2.3. Whether the bare draw numbers are protectable facts is a separate legal question; the terms bind anyone using the site regardless.

## Third-party sources checked

| Source | What it is | Problem |
|---|---|---|
| GitHub Singapore-Pools-Dataset | 4D since 1986, Toto draws, CSV | Collected from the Singapore Pools site; no licence stated; known NaN gaps |
| GitHub TOTO-SG-Data | JSON fed by a scraper repo | Scraper-based; no licence; no field schema |
| GitHub scrapers (sg-lottery-scraper, fourd, etc.) | Code that scrapes Singapore Pools | Same terms issue when run |
| Kaggle "Singapore Lottery Numbers" | Dataset, 2022 | Source and licence not stated |
| Zyla "Live 4D Draw Results API" | Paid API marketplace listing | Origin and licensing of data not confirmed |

None of these is a clean licence: they inherit the same origin, and an unlicensed dataset adds no rights.

## How other public repos handle it (code read 17 Oct 2026)

Seven public GitHub projects that collect Singapore Pools results were cloned and their fetch code read.

| Repo | Last commit | Licence | Fetches | Politeness | Terms or permission mentioned |
|---|---|---|---|---|---|
| alphatrl/sg-lottery-scraper | 2025-05-26 | MIT | 4D, Toto, Sweep results pages via Puppeteer | GitHub Actions cron, about 4 runs a day plus Toto cascade runs | No |
| Q-gabe/huat-did-i-win (archived Jan 2026) | 2021-01-11 | MIT | Proxies users' checks to Singapore Pools' own `CalculatePrizeForTOTO` endpoint | None | No (only "not encouraging gambling") |
| nwfxyz/4D_analytics | 2018-05-27 | None | Posts every 4D combination to `Get4DNumberCheckResultsJSON` | 1 s sleep; spoofs a Firefox user agent | No ("We do not advocate gambling") |
| jinjie/fourd | 2019-01-13 | MIT | Scrapy spider on `fourd_result_draw_list_en.html`, up to one year back | Honest user agent "Fourd"; no delay set | No |
| ccie48715/Toto_Singapore | 2021-10-16 | Apache-2.0 | Toto results and outlet pages, into SQLite | None | No |
| yongyct/singapore-pools-analysis | 2019-11-16 | None | 4D and Toto results pages, BeautifulSoup | None | No |
| Singapore-Pools-Dataset | 2026-07-14 | None | Published CSV, 4D since 1986 plus Toto | n/a | No |

Takeaways:
- None of them states that permission was obtained, and none mentions the website terms.
- Their MIT or Apache licences cover their own code only; they cannot grant rights to Singapore Pools' data.
- They are hobby or analysis projects. None is a public, branded product with a paid tier like toto.zenqi.cc.
- No takedowns were visible, but that is not permission; it only shows enforcement against small repos has not been public.
- Patterns not to copy: spoofed browser user agents, brute-forcing Singapore Pools' number-check endpoint (10,000 requests), and proxying our users' checks through Singapore Pools' own checker.
- If permission is granted, good practice from these repos and general norms: fetch once after each draw (Toto Mon/Thu after 21:30, 4D Wed/Sat/Sun after 18:30), one request per page, an honest user agent with a contact address, cache and store the raw page, and never call their internal JSON endpoints unless the permission covers them.

Endpoints these repos use (for the permission request, so it can name them): `en/product/Pages/4d_results.aspx`, `en/product/Pages/toto_results.aspx`, `DataFileArchive/Lottery/Output/fourd_result_draw_list_en.html`, `_layouts/15/FourD/FourDCommon.aspx/Get4DNumberCheckResultsJSON`, `_layouts/15/TotoApplication/TotoCommonPage.aspx/CalculatePrizeForTOTO`.

## Bring-your-own-result: what the browser allows (checked 17 Oct 2026)

Response headers on the official Toto results page (one request from the user's own browser):
- `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors none` → the page will not load inside an iframe on toto.zenqi.cc (blank frame).
- No `Access-Control-Allow-Origin` → JavaScript on toto.zenqi.cc cannot read the page either.
- Even if framing were allowed, a page cannot read or screenshot a cross-origin iframe; the only browser capture route is the screen-share prompt (`getDisplayMedia`), which asks the user every time.

So in the web app and PWA, the official page opens in its own tab, and the user hands the result back by screenshot, share-to-app (Android PWA share target), or typing. A native Android shell with an in-app view could read the page the user is viewing, but that is our code extracting content (cl. 2.2.3 risk) and needs the legal check.

Deep links (verified): Toto `en/product/sr/Pages/toto_results.aspx?sppl=<base64 "DrawNumber=N">`, 4D `en/product/Pages/4d_results.aspx?sppl=<same>`.

## What the official pages offer (for reference only)

- `fourd_result_top_draws_en.html` (DataFileArchive) holds the latest 6 4D draws: draw no., date, 1st/2nd/3rd, 10 starter, 10 consolation.
- Toto results pages are keyed by an encoded draw number and include group prize amounts and winner counts, which the matcher needs for Groups 1-4.

## Decision (proposed)

1. **Ask Singapore Pools for written permission** (cl. 4.2.2) to use 4D and Toto results, current and historical, in a free public checker at toto.zenqi.cc, with source attribution and links back. This is the only clean route for both nightly ingest (P2-03) and backfill (P2-04).
2. **Build the ingest with a pluggable source adapter**, so the source can be swapped (permitted feed, licensed provider, or manual import) without touching the schema or matcher.
3. **Until permission:** development uses a small hand-entered fixture set of real draws, not a scraper, and nothing is published.
4. **Fallbacks if refused:**
   - User-entered results: the user types or confirms the winning numbers for their draw; the app only does the matching (results never redistributed by us).
   - A licensed commercial data provider, if one can show rights to the data.
   - Link-out: send users to the official results page and only check the numbers they enter.
5. Third-party scraped datasets are not used in the product. P5 analytics/backfill waits on the same permission.

## Open
- Who at Singapore Pools handles data or content permission requests (no process is described in the terms).
- Whether permission would cover historical archives (P2-04) as well as new draws.
