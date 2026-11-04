# P3-02-R2: parser fixes from six real photos

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_ocr.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Every function and constant not named in section 3 stays exactly as it is, including the module docstring, the imports and the last line `    return "\n".join(out)`.

## 1 - Scope
Edit only `lottery_checker/ticket_ocr.py`, and inside it only:
- add one module constant `_DRAW_SLASH` and use it in `clean_row`;
- the `if re.search(r"\bTOTO\b", joined):` test in `read_rows`;
- the 4D branch of `read_rows`;
- the token loop in `_toto_text`.
No new files, no new imports, no other functions touched.

## 2 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` must pass. The test file is the only success condition. Do not edit the tests. Six tests at the bottom of it (after `# P3-02-R2`) are red today; `test_toto_without_a_title_or_system_header_still_says_it_could_not_tell` is green today and must stay green, as must every other test.

## 3 - Behaviour

### 3a. A slash read as a digit in a draw number (`clean_row`)
Vision reads the `/` of `4217/26` as `7` or `1` (`4217726`, `4230126`). Add, after the imports' constants:
```python
# a draw number whose "/" was read as 7, 1, l, I or |: "14/09/26 4217726" -> "14/09/26 4217/26"
_DRAW_SLASH = re.compile(r"(\d{2}/\d{2}/(\d{2})\s+\d{4})[71lI|](?=\2\b)")
```
In `clean_row`, apply it once to the whole row, directly after the `_SPACED_DATE.sub(...)` line: `row = _DRAW_SLASH.sub(r"\1/", row)`. A row without a date before a 7-digit run is not changed.

### 3b. TOTO title lost (`read_rows`)
Today a photo is TOTO only if `\bTOTO\b` appears. Vision read the title as `STO` and `TOTOLS`. Change the test to also accept `\bSYSTEM\s*\d` (a bet-type header only TOTO prints): `re.search(r"\bTOTO\b|\bSYSTEM\s*\d", joined)`. The 4D branch and the "Couldn't tell" branch keep their tests and order.

### 3c. 4D header noise (4D branch of `read_rows`)
After the footer cut, and before `text = "4D\n" + ...`, make three changes to `rows`:
1. If some row matches `\b(?:ORDINARY|IBET|ROLL|SYSTEM)\b` (case-insensitive), the first such row is the bet-type row: drop every row before it. If none matches, drop nothing.
2. Drop every row that, after `.strip()`, is only 1 to 3 digits.
3. In a row that matches `PRICE\b` and contains `\$\s*(\d+\.\d{2})`, replace the whole row with `PRICE : $ <that amount>` (this puts back a price row the watermark glued letters onto, `SINPRICE POBE : $ 9.00`).
Then `text = "4D\n" + "\n".join(rows)` as today, and the note line stays.

### 3d. Orphan digit on a board row (`_toto_text`)
Vision sometimes reads a board's first number glued to junk: `3.04` for `04`. In the token loop, before the `_NUM.match(tok)` test, add: if `tok` matches `^\d\.(\d{2})$`, set `tok` to its two-digit group. The loop only covers rows before the PRICE and DRAW rows, so a price like `4.00` is never reached.
