# P3-02-H: harden the ticket photo parser on layouts not yet seen

## 0 - Output format contract
Reply with the complete file `lottery_checker/ticket_ocr.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Every function and constant not named in section 3 stays exactly as it is, including the module docstring, the imports and the last line `    return "\n".join(out)`.

## 1 - Scope
Edit only `lottery_checker/ticket_ocr.py`, and inside it only:
- add one module constant `_FOOTER` directly after the `_NUM = ...` line;
- the 4D branch of `read_rows`;
- `_toto_text`: the header-size handling, the `out = [...]` line, and the board-letter loop.
No new files, no new imports, no other functions touched.

## 2 - Gate
`py -3 -m pytest tests/test_ticket_ocr.py -q` must pass (all 28 tests). The test file is the only success condition. Do not edit the tests.

## 3 - Behaviour

### 3a. Footer constant
Add, directly after `_NUM = re.compile(r"^\d{1,2}$")`:
```python
# purchase time ("01:42") or a dashed serial ("000-0000000-0000000"): the ticket footer
_FOOTER = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{3,7}-\d{1,7}-\d{3,7}\b")
```

### 3b. 4D branch of `read_rows`
Today it is `text = "4D\n" + "\n".join(rows)`. Replace it so that the first row where `_FOOTER.search(row)` matches, and every row after it, is left out of `text`. If no row matches, all rows are kept (today's behaviour). The `notes.append("4D photo reading is new: ...")` line stays as it is. The TOTO branch and the "Couldn't tell" branch do not change.

### 3c. `_toto_text`: impossible SYSTEM size
Today, when `m.group(2)` is set, `kind, size = f"SYSTEM {int(m.group(2))}", int(m.group(2))`. Change it to: let `n = int(m.group(2))`.
- If `7 <= n <= 12`: `kind, size = f"SYSTEM {n}", n` (unchanged result).
- Otherwise: `kind, size = None, None`, and append exactly this note:
  `f"Bet type read as SYSTEM {n}, which doesn't exist; the bet type was taken from the count of numbers."`

With `size` None the existing check `if len(cur) == size:` is never true, so only a board letter starts a new board. Do not change that check.

### 3d. `_toto_text`: the `out` list
Today `out = ["TOTO", kind]`. Change it to `out = ["TOTO"] + ([kind] if kind else [])`, so no bet-type line is written when `kind` is None (`parse_ticket` then takes the type from the count of numbers).

### 3e. `_toto_text`: more than 10 boards
Today the loop writes `f"{letter or next(spare)}. ..."`, and `next(spare)` raises `StopIteration` once the ten letters A-J are used up. Change the loop body so that:
- the letter is `letter or next(spare, None)`;
- when the letter is not None the line is `f"{letter}. {' '.join(nums)}{' QP' if qp else ''}"` (unchanged);
- when it is None the line is `f"{' '.join(nums)}{' QP' if qp else ''}"` (no letter, no dot).

After that loop, if `len(boards) > 10`, append exactly this note: `"More than 10 boards were read; check the photo."`
The existing "A board letter was missing" note stays as it is.
