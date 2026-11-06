# P3-02-P: page-processed photo fixtures

Gate: `py -3 -m pytest tests/test_ticket_ocr.py -q`

Tests-only, green on arrival, LEAD DIRECT (`no-runner`). `tests/fixtures/ocr/NN_page.rows.txt` hold the Vision rows
for the image the live page sends (`shrink` + `cleanTicket`), serial rows dropped. Raw-file Vision text missed
the `DRAW :` and `G.6310` bugs; these fixtures pin the live path for photos 01-11.
