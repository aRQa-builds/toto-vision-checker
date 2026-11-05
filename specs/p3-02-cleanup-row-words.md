# P3-02-C: remove the unused `row_words` variable in `ocr.py`

## 0 - Output format contract
Not delegated. LEAD DIRECT, `no-runner`: the gate is already green, so there is no red test to turn green.

## 1 - Scope
`lottery_checker/ocr.py`, `OcrResult.lines`: delete the single line `row_words = [i[3] for i in rows[-1]]`. Nothing else changes. The variable was left over from Hand's P3-02-R1 attempt and is never read.

## 2 - Gate
`py -3 -m pytest tests/test_ocr_skew.py tests/test_ocr.py tests/test_ticket_ocr.py -q` must stay green (behaviour unchanged).
