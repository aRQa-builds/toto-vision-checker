# P5-01 slice 1: descriptive draw statistics (lottery_checker/stats.py)

## 0 - Output format contract
Reply with the complete file `lottery_checker/stats.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the module docstring, `MIN_DRAWS`, `NOTE`, the three function names and the final line `STATS_MODULE_END = True`.

## 1 - Scope
Edit only `lottery_checker/stats.py`: fill in `toto_stats`, `fourd_stats`, `all_stats`. Standard library only (`json`, `pathlib` are already imported). Do not touch any other file.

## 2 - Gate
`py -3 -m pytest tests/test_stats.py -q` must pass. The test file is the only success condition.

## 3 - Behaviour
Input draws are dicts as stored in `data/draws/<game>/<n>.json`. Sort by `draw_no` ascending first; the input order does not matter. Counts only. Never sort or rank by count, and never use the words hot, cold, due or lucky.

`toto_stats(draws)` returns `{"game": "toto", "draws": n, "enough": n >= MIN_DRAWS, "note": NOTE, "numbers": [...]}` where `numbers` has exactly 49 dicts, always in order 1..49, each `{"number": k, "drawn": times k is in `winning` (the six), "additional": times k equals `additional`, "expected": n * 6 / 49, "since": ...}`. `since` is the number of draws after the latest draw whose `winning` six contains k (0 if k is in the latest draw), or `None` if k never appeared in a six.

`fourd_stats(draws)` returns `{"game": "4d", "draws": n, "enough": n >= MIN_DRAWS, "note": NOTE, "first_digits": [4 lists of 10 ints], "expected_per_digit": n / 10, "distinct_numbers": d}`. `first_digits[p][d]` counts draws whose `first` prize string has digit d at position p (0 = leftmost). `distinct_numbers` is the count of distinct 4-character strings across `first`, `second`, `third`, `starter` and `consolation` of all draws. With no draws, `first_digits` is four lists of ten zeros.

`all_stats(data_dir)` returns `{"toto": toto_stats(...), "4d": fourd_stats(...), "note": NOTE}`. It reads every `*.json` under `Path(data_dir) / "draws" / "toto"` and `"4d"` (only those folders, nothing else). A missing folder gives no draws; a file that is not valid JSON, or not a dict, is skipped.
