r"""What Vision got wrong on results screenshots, lined up against the true results.

Reads data\learning\vision_reads.jsonl (written whenever a results screenshot
comes up short, see lottery_checker/diag.py), looks up the true result for each
draw (official capture first, else a crowd result two people agreed on), and says
what kind of mistake it was: a number dropped, an extra one, or a wrong one.
Writes data\learning\vision_review.csv. Makes no Vision calls and no web requests.

Usage (project folder):
  py -3 tools\vision_review.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lottery_checker import diag  # noqa: E402


def main() -> int:
    data = Path(os.environ.get("TOTO_DATA", ROOT / "data"))
    rows = diag.review(data)
    if not rows:
        print("Nothing logged yet: no results screenshot has come up short.")
        return 0
    for r in rows:
        print(f"{r['at'][:16]}  {r['game']} {r['draw_no']}  missing: {r['missing']}  read: {r['read']}")
        print(f"      -> {r['kind']}" + (f" ({r['detail']})" if r["detail"] else "")
              + (f"  [truth: {r['truth_source']}]" if r["truth_source"] else ""))
    kinds = Counter(r["kind"] for r in rows)
    print("\nSummary:", ", ".join(f"{k} {n}" for k, n in kinds.most_common()))
    dropped = [n for r in rows if r["kind"] == "dropped" for n in (r["truth"] or {}).get("winning", [])
               if n not in r["read"].get("winning", [])]
    if dropped:
        one = sum(1 for n in dropped if n < 10)
        print(f"Numbers Vision dropped: {len(dropped)}, of which single-digit: {one}")
    print("CSV:", diag.write_review_csv(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
