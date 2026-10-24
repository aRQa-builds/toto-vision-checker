"""Derive Toto System-entry winning-share tables by combinatorics.

A System N entry covers every 6-number combination out of the N chosen numbers.
Each combination is graded against the draw (6 winning numbers + 1 additional).
System Roll covers the 5 chosen numbers plus each of the other 44 numbers.

Superseded as a check by verify_cl516.py (full 2026 official table); kept for reference.
"""
from math import comb


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
    """System n, with w of the chosen numbers among the 6 winning and a (0/1) = additional number chosen."""
    o = n - w - a
    if o < 0:
        return None
    out = {}
    for i in range(0, min(w, 6) + 1):
        for j in range(0, a + 1):
            l = 6 - i - j
            if l < 0 or l > o:
                continue
            cnt = comb(w, i) * comb(a, j) * comb(o, l)
            g = group_of(i, j)
            if g:
                out[g] = out.get(g, 0) + cnt
    return out


def roll_shares(w, a):
    """System Roll: 5 chosen numbers (w winning, a additional among them), 6th is each of the other 44."""
    if w + a > 5:
        return None
    rest_win = 6 - w
    rest_add = 1 - a
    rest_other = 44 - rest_win - rest_add
    out = {}

    def add(g, c):
        if g and c:
            out[g] = out.get(g, 0) + c

    add(group_of(w + 1, a), rest_win)
    add(group_of(w, a + 1), rest_add)
    add(group_of(w, a), rest_other)
    return out


if __name__ == "__main__":
    print("System Roll (5 chosen numbers; w winning among them, a = additional among them):")
    for w in range(0, 6):
        for a in (0, 1):
            r = roll_shares(w, a)
            if r:
                print(f"  w={w} a={a}: {r}")
    print("\nSystem 7-12 full table (w winning among chosen, a additional chosen):")
    for n in range(7, 13):
        for w in range(6, 1, -1):
            for a in (1, 0):
                r = system_shares(n, w, a)
                if r:
                    print(f"  System {n}  w={w} a={a}: {dict(sorted(r.items()))}")
