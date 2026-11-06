# P3-02-W: "DRAW :" printed between the day name and the date

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_ocr.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target `lottery_checker/ticket_ocr.py` only. In `clean_row` (line 130) add one step, and one module-level compiled regex beside `_GLUED_DAY` (line 47): when a day name (MON TUE WED THU FRI SAT SUN, case-insensitive) is followed by the word `DRAW`, optional spaces, an optional `:`, optional spaces, and then a date `dd/mm/yy`, remove the `DRAW :` part and keep the day and date: `THU DRAW : 10/09/26 4216/26` -> `THU 10/09/26 4216/26`. Apply it where the other row regexes run (before the token loop). A row that begins with `DRAW :` before the day (`DRAW : THU 10/09/26 4216/26`) must stay unchanged.

Do not change `_DRAW`, `_toto_text`, `read_rows` or any other function.

## 2 - Why
Live photo run 2026-11-06: photo 07 (draws 4216 and 4217) read only 4217 on the page. The page shrinks the photo and filters out the watermark before sending (`web/index.html` `shrink`), and for that image Vision returns `THU DRAW : 10/09/26 4216126 ...`. `_DRAW` needs `DAY date number`, so draw 4216 was dropped silently; only the price check flagged it. Reproduced 2/2 from the page-processed image; the raw file reads fine 5/5, which is why the old tests never saw it.

## 3 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` (red now: `test_w07_draw_word_between_day_and_date_is_dropped`, `test_w07_page_image_rows_keep_both_draws`).

## 4 - Limits
Fixes one Vision variant. Tests on raw files do not exercise the page's own image processing; a fixture of page-processed Vision rows per photo is the follow-up (not in this slice).
