# P3-02-R1: row grouping keeps a board on one row

## 0 - Output format contract
Reply with the complete file `lottery_checker/ocr.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Everything outside the loop in section 3 stays exactly as it is, including the module docstring, the imports, the `lines` signature and docstring, and the last line of the file.

## 1 - Scope
Edit only `lottery_checker/ocr.py`, and inside it only the row-building loop in `OcrResult.lines` (the `for x, y, h, w in items:` loop). No new files, no new imports, no other functions touched.

## 2 - Gate
`py -3 -m pytest tests/test_ocr_skew.py -q` must pass. The test file is the only success condition. Do not edit the tests. Two tests were added at the bottom of it; `test_a_tall_watermark_word_does_not_split_a_board_row` is red today, `test_4d_bet_rows_keep_number_and_stake_together` is green today and must stay green, as must every other test in the file.

## 3 - Behaviour
Today a word joins the current row when its vertical centre is within `tolerance * max(h, rh)` of the centre of the row's FIRST word (`rows[-1][0]`). A tall watermark word that sorts first then anchors the row and a real number 22 px away is left out (real photo, 5 Nov 2026).

Change the comparison so the row centre is the mean `y` of every word already in the row, and `rh` is the mean height of every word already in the row. The test stays `abs(y - row_mean_y) <= tolerance * max(h, row_mean_h)`. Sorting, the `tolerance` default, the skew handling and the final join are unchanged.

Measured on the real photos before writing this spec: this one change put every 4D line of a 10-line ticket back on one row and rejoined a split TOTO board.
