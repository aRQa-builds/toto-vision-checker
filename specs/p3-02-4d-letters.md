# P3-02-L: 4D board letter glued to the number, and a stray digit before it

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_entry.py`, line 1 to the last line, in one fenced block. Never `# ... existing code ...`, a placeholder or a partial hunk: every omitted line is deleted from disk.

## 1 - Scope
Target: `lottery_checker/ticket_entry.py` only. Two bounded changes, nothing else:
1. `_BOARD_LETTER` (line 49): today `^\s*([A-J])[.)]?\s+(?=[\dR])`. A letter followed by `.` or `)` must accept zero spaces after it (`G.6310`, `B.5413`). A letter with NO `.`/`)` must still need at least one space, so `DRAW`, `D` + `R...`, never reads as board D. Keep case-insensitive.
2. `_add_fourd` (line 309): after the board letter is removed, if the body starts with one stray digit and a dot or comma and then a 4-digit number (`1.7310`), drop that `1.` so the number is `7310`. Only that exact shape: one digit, one `.` or `,`, optional spaces, then `[0-9R]{4}` ending at a word boundary. Nothing else is stripped.

Do not change `_FOURD_NUM`, `_toto_numbers`, or any other function. `_BOARD_LETTER` is also used by `_toto_numbers`: TOTO behaviour must not change.

## 2 - Why
Live photo run 2026-11-06: photo 10 fails on `G.6310` and `H. 1.7310`, photo 11 on `B.5413`. The parser rejects them loudly (correct), but the text is a valid ticket.

## 3 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` must pass in full (currently 2 red: `test_l10_...`, `test_l11_...`; `test_l_draw_word_...` is a guard that must stay green).

## 4 - Limits
Pattern-based on two Vision variants. A different misread is a new spec. Numbers are never guessed: an unreadable line still errors.
