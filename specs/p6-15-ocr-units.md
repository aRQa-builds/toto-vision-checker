# P6-15-E: keep the Group TOTO / iTOTO header and unit line when reading a photo

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_ocr.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk. The file ends with `_toto_text`; keep it last.

## 1 - Problem
`_toto_text` drops the `GROUP TOTO` / `ITOTO` header and the unit line, so a unit ticket reads as an ordinary one and would show the whole-entry prize. Fix it for TOTO photos only. 4D, `read_rows`, `read_ocr`, `clean_row` and every other function stay as they are.

## 2 - Scope (ticket_ocr.py only)
1. Four new module-level regexes next to `_LETTER_NUM` (all `re.I`, all with a leading word boundary, written as raw strings):
   - `_UNIT_HEAD`: `GROUP\s+TOTO` or `ITOTO`, captured in group 1.
   - `_UNIT_GROUP`: `UNIT\s+NUMBER\s*:?\s*(\d+)\s*/\s*(\d+)`.
   - `_UNIT_ITOTO`: `UNITS\s+PURCHASED\s*:?\s*(\d+)\s+OF\s+(\d+)`.
   - `_UNIT_OPEN`: `(?:UNIT\s+NUMBER|UNITS\s+PURCHASED)\s*:?\s*$` (a unit label whose value is on the next row).
2. At the very top of `_toto_text`, before anything else:
   - merge rows: a row matching `_UNIT_OPEN` is joined with the next row (single space) so `NUMBER OF UNITS PURCHASED:` + `1 of 28` becomes one row;
   - `unit_head` = the first `_UNIT_HEAD` match's group 1, upper-cased, or `None`;
   - `unit_line` = for the first row matching `_UNIT_GROUP`: `UNIT NUMBER: {k}/{n}`; else for the first matching `_UNIT_ITOTO`: `NUMBER OF UNITS PURCHASED: {u} of {N}`; else `None`;
   - then drop every row matching `_UNIT_GROUP` or `_UNIT_ITOTO` from `rows`, so the unit numbers are never read as board numbers.
3. Output: the bet-type line `kind` is prefixed `GROUP TOTO - ` when `unit_head` starts with `GROUP`, or `ITOTO - ` otherwise, when `unit_head` is set (e.g. `GROUP TOTO - ORDINARY`, `ITOTO - SYSTEM 12`); with no `unit_head` the line is exactly as today. If `unit_line` is set, append it just before the existing `if len(boards) > 10:` note check (after the PRICE line).
Tickets with no unit header and no unit line produce byte-identical text to today.

## 3 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` (6 red now: the `test_e_*` tests, synthetic rows shaped like the official specimens). Whole suite must stay green.

## 4 - Limits
No real or scraped ticket text anywhere. Do not change `ticket_entry.py`; it already parses these lines.
