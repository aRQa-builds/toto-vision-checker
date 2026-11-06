# P3-02-R: TOTO System Roll coverage from synthetic rows

## 0 - Status
Tests only. No target file changes. Not delegable to Hand: every test is green today, so `rig-loop` would exit 2 (gate already green). Reason for zero: `no-runner`. Done LEAD DIRECT at the owner's request (2026-11-06).

## 1 - Why
P0-02 wanted a real TOTO System Roll photo. The owner chose to omit it and cover it synthetically, as with System 8-11 (`specs/p3-02-sys811.md`). No network access and no Singapore Pools fetch: PROJECT_BRAIN Rules still apply.

## 2 - What
Append a "P3-02-R" section to `tests/test_ticket_ocr.py`: a row builder `_roll_rows` in the real System 7 row shape (photo `09_toto_system7_4229_4230.jpg`): watermark glue, a `SYSTEM ROLL` header, 5 numbers per board, `$44` price (5 chosen x the other 44, rules reference), dummy numbers and serials.

Tests:
- `test_system_roll_board_reads_as_one_five_number_board`
- `test_system_roll_two_boards_do_not_merge`
- `test_system_roll_header_glued_or_spaced_reads_the_same`

## 3 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` (45 passed).

## 4 - Limits
Synthetic rows prove the parser handles the shape assumed here. The real System Roll layout is unseen, so the number of boards per ticket, the board letters and the position of the header are assumptions. A real photo replaces these if one ever turns up. P0-02 is closed as "omitted by owner".
