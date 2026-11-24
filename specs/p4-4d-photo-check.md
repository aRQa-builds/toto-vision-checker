# P4-4D-PHOTO: real 4D photo rows through the check path (draw 5553)

## 0 - Status
Tests only. No target file changes. Not delegable to Hand: the test is green on arrival, so `rig-loop` would exit 2 (gate already green). Reason for zero: `no-runner` (nothing red to turn green). Done LEAD DIRECT at the owner's request (2026-11-24, session 9).

## 1 - Why
Item 4 evidence offered the live 4D ticket for draw 5553. The draw is stored and the ticket is fixture 10 (`tests/fixtures/ocr/10_page.rows.txt`, 10 printed lines, line C `BIG S'OUT`). Parser tests read these rows and `test_check_4d_against_tonights_draw` checks typed text, but no test ran real photo rows through `/api/check`.

## 2 - What
Append one test to `tests/test_api.py`: `test_real_4d_photo_rows_check_against_draw_5553_with_a_sold_out_line`. It writes a 5553 record into the temp data folder, reads `10_page.rows.txt` with `read_rows`, posts the text to `/api/check`, and asserts:
- nine entries (0310, 1310, then 3310 to 9310); line C (2310) is not an entry;
- the sold-out warnings for line 5 are present;
- printed price 9.0 equals the computed stake 9 (S'OUT is $0, so the $9.00 price is nine accepted $1 bets);
- reveal state `no_win`, headline "No win this time", stake state `match`.

## 3 - Gate
`py -3 -m pytest tests/test_api.py -q`

## 4 - Limits
Covers one real ticket (a non-winner). A winning real photo would add the payout path. The draw record is copied from `data/draws/4d/5553.json` (published results, attributed, same as the 5551 record already inline).
