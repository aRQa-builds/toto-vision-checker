"""P0-01: diff the official 2026 Toto cl. 5.16 System table against the derived combinatorics.

Official table transcribed from TOTO Game Rules w.e.f. 2 Mar 2026 (Draw 4161/2026), page 15.
Columns: System Roll, Ordinary, System 7..12. None = "-" in the official table.
Scenario key (w, a): w = winning numbers among the chosen numbers, a = 1 if the Additional Number is chosen.
For System Roll, w and a count among the 5 chosen numbers.
"""
from math import comb

COLS = ["roll", 6, 7, 8, 9, 10, 11, 12]
_ = None

OFFICIAL = {
    (6, 1): {1: [_, _, 1, 1, 1, 1, 1, 1],
             2: [_, _, 6, 6, 6, 6, 6, 6],
             3: [_, _, _, 6, 12, 18, 24, 30],
             4: [_, _, _, 15, 30, 45, 60, 75],
             5: [_, _, _, _, 15, 45, 90, 150],
             6: [_, _, _, _, 20, 60, 120, 200],
             7: [_, _, _, _, _, 20, 80, 200]},
    (6, 0): {1: [_, 1, 1, 1, 1, 1, 1, 1],
             3: [_, _, 6, 12, 18, 24, 30, 36],
             5: [_, _, _, 15, 45, 90, 150, 225],
             7: [_, _, _, _, 20, 80, 200, 400]},
    (5, 1): {2: [_, 1, 1, 1, 1, 1, 1, 1],
             3: [_, _, 1, 2, 3, 4, 5, 6],
             4: [_, _, 5, 10, 15, 20, 25, 30],
             5: [_, _, _, 5, 15, 30, 50, 75],
             6: [_, _, _, 10, 30, 60, 100, 150],
             7: [_, _, _, _, 10, 40, 100, 200]},
    (5, 0): {1: [1, _, _, _, _, _, _, _],
             2: [1, _, _, _, _, _, _, _],
             3: [42, 1, 2, 3, 4, 5, 6, 7],
             5: [_, _, 5, 15, 30, 50, 75, 105],
             7: [_, _, _, 10, 40, 100, 200, 350]},
    (4, 1): {2: [2, _, _, _, _, _, _, _],
             4: [42, 1, 2, 3, 4, 5, 6, 7],
             5: [_, _, 1, 3, 6, 10, 15, 21],
             6: [_, _, 4, 12, 24, 40, 60, 84],
             7: [_, _, _, 4, 16, 40, 80, 140]},
    (4, 0): {3: [2, _, _, _, _, _, _, _],
             4: [1, _, _, _, _, _, _, _],
             5: [41, 1, 3, 6, 10, 15, 21, 28],
             7: [_, _, 4, 16, 40, 80, 140, 224]},
    (3, 1): {4: [3, _, _, _, _, _, _, _],
             6: [41, 1, 3, 6, 10, 15, 21, 28],
             7: [_, _, 1, 4, 10, 20, 35, 56]},
    (3, 0): {5: [3, _, _, _, _, _, _, _],
             6: [1, _, _, _, _, _, _, _],
             7: [40, 1, 4, 10, 20, 35, 56, 84]},
    (2, 1): {6: [4, _, _, _, _, _, _, _]},
    (2, 0): {7: [4, _, _, _, _, _, _, _]},
}


def group_of(win_hits, add_hit):
    if win_hits == 6:
        return 1
    if win_hits == 5:
        return 2 if add_hit else 3
    if win_hits == 4:
        return 4 if add_hit else 5
    if win_hits == 3:
        return 6 if add_hit else 7
    return 0


def system_shares(n, w, a):
    o = n - w - a
    if o < 0:
        return None
    out = {}
    for i in range(0, min(w, 6) + 1):
        for j in range(0, a + 1):
            l = 6 - i - j
            if l < 0 or l > o:
                continue
            g = group_of(i, j)
            if g:
                out[g] = out.get(g, 0) + comb(w, i) * comb(a, j) * comb(o, l)
    return out


def roll_shares(w, a):
    if w + a > 5:
        return None
    out = {}
    for g, c in ((group_of(w + 1, a), 6 - w),
                 (group_of(w, a + 1), 1 - a),
                 (group_of(w, a), 44 - (6 - w) - (1 - a))):
        if g and c:
            out[g] = out.get(g, 0) + c
    return out


def derived(col, w, a):
    r = roll_shares(w, a) if col == "roll" else system_shares(col, w, a)
    return r or {}


cells = mismatches = 0
for (w, a), groups in OFFICIAL.items():
    for ci, col in enumerate(COLS):
        official = {g: vals[ci] for g, vals in groups.items() if vals[ci] is not None}
        got = derived(col, w, a)
        cells += len(set(official) | set(got))
        if official != got:
            mismatches += 1
            print("MISMATCH", (w, a), col, "official", official, "derived", got)

# Also confirm the derived table has no non-empty scenario the official table omits.
extra = []
for col in COLS:
    for w in range(0, 7):
        for a in (0, 1):
            if (w, a) in OFFICIAL:
                continue
            got = derived(col, w, a)
            if got:
                extra.append((col, w, a, got))

print(f"scenarios: {len(OFFICIAL)}, columns: {len(COLS)}, group cells compared: {cells}")
print("column mismatches:", mismatches)
print("derived wins in scenarios absent from official table:", extra or "none")
