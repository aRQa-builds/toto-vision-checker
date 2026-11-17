# P2-07-I: `store` never re-saves a draw that is already on file

## 0 - Output format contract
Reply with the complete file `lottery_checker/ingest.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target `lottery_checker/ingest.py` only, function `store`. Inside the `for res in results:` loop, after `json_p` is built, if `json_p` already exists, `continue` before anything is written: no raw write, no JSON write, and the record is not appended to `out`. A draw not yet on file is stored exactly as before.

Do not change any other line or function (`run` included).

## 2 - Why
A gap request answered with the latest page (draw not yet published, or a redirect that still parses) makes `store` rewrite that latest draw's raw page and JSON, so its `captured_at` moves and the original capture time is lost. Follow-up to P2-07-G/H.

## 3 - Gate
`py -3 -m pytest tests/test_ingest.py -q` (red now: `test_gap_fill_does_not_rewrite_a_draw_already_stored`). Every other test in the file must stay green.

## 4 - Limits
Known and accepted: when the page's only draw is already stored, `run` prints "NOTE draw N not published yet; page returned nothing", because `store` returns no record for it. The wording is imprecise but harmless; not in scope.
