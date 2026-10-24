"""First real Google Vision run (P3-01).

Sends each image to Vision once and reports what came back. Costs one billed
request per image (the first 1,000 a month are free).

1. The two real phone screenshots in tests/fixtures/screens/*.jpg: reads them
   with results_screen and compares draw number, game, numbers and share
   amounts against the hand-typed reference text next to each one (*.txt).
   PASS means Vision read everything the reference has.
2. Any extra images you name (for example your own ticket photos): prints the
   text and the row-grouped lines, which is what the ticket parser (P3-02)
   will be built on. With --save, the text is kept in tests/fixtures/ocr/
   for that work. Nothing is saved without --save.

The API key is read from GOOGLE_VISION_API_KEY and never printed.

Usage (project folder):
  py -3 tools\\vision_smoke.py                          # the two screenshots
  py -3 tools\\vision_smoke.py D:\\photos\\ticket1.jpg     # plus your photos
  py -3 tools\\vision_smoke.py --save D:\\photos\\*.jpg
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lottery_checker import ocr  # noqa: E402
from lottery_checker.results_screen import read_screen  # noqa: E402

SCREENS = ROOT / "tests" / "fixtures" / "screens"
SAVE_DIR = ROOT / "tests" / "fixtures" / "ocr"


def fields(r) -> dict:
    out = {"game": r.game, "draw_no": r.draw_no, "draw_date": r.draw_date}
    if r.game == "toto":
        out.update(winning=r.winning, additional=r.additional, shares=dict(r.shares))
    elif r.game == "4d":
        out.update(first=r.first, second=r.second, third=r.third,
                   starter=r.starter, consolation=r.consolation)
    return out


def compare(got: dict, want: dict) -> list[str]:
    bad = []
    for k, v in want.items():
        if v in (None, [], {}):
            continue
        g = got.get(k)
        if isinstance(v, dict):
            miss = {kk: vv for kk, vv in v.items() if (g or {}).get(kk) != vv}
            if miss:
                bad.append(f"{k}: expected {miss}, got {g}")
        elif isinstance(v, list):
            if [x for x in v if x not in (g or [])]:
                bad.append(f"{k}: expected {v}, got {g}")
        elif g != v:
            bad.append(f"{k}: expected {v}, got {g}")
    return bad


def run(path: Path) -> ocr.OcrResult:
    data = path.read_bytes()
    res = ocr.recognize(data)
    conf = res.mean_confidence
    print(f"  {len(data):,} bytes -> {len(res.words)} words, "
          f"mean confidence {conf:.3f}" if conf is not None else
          f"  {len(data):,} bytes -> {len(res.words)} words")
    return res


def main(argv: list[str]) -> int:
    if not os.environ.get(ocr.ENV_KEY, "").strip():
        print(f"{ocr.ENV_KEY} is not set in this window. Open a new PowerShell after setting it.")
        return 2
    save = "--save" in argv
    extra = [Path(p) for a in argv if a != "--save" for p in (glob.glob(a) or [a])]

    calls, failures = 0, 0
    print("Screenshots of the official results page")
    for img in sorted(SCREENS.glob("*.jpg")):
        ref = img.with_suffix(".txt")
        print(f"- {img.name}")
        try:
            res = run(img)
            calls += 1
        except ocr.OcrError as e:
            print(f"  FAIL: {e}")
            return 1                       # a key or API problem: stop before more billed calls
        got = fields(read_screen(res.text))
        if not ref.exists():
            print(f"  read: {got}")
            continue
        want = fields(read_screen(ref.read_text(encoding="utf-8")))
        bad = compare(got, want)
        if bad:
            failures += 1
            print("  DIFFERS from the typed reference:")
            for b in bad:
                print(f"    {b}")
            print("  Vision text:")
            print("    " + res.text.replace("\n", "\n    "))
        else:
            print(f"  PASS: draw {got['draw_no']} ({got['game']}), every reference field read")

    if extra:
        print("\nYour images")
    for img in extra:
        print(f"- {img}")
        if not img.is_file():
            print("  not found")
            continue
        try:
            res = run(img)
            calls += 1
        except ocr.OcrError as e:
            print(f"  FAIL: {e}")
            failures += 1
            continue
        if res.empty:
            print("  no text found (retake: flat, lit, whole ticket in frame)")
            continue
        print("  lines (grouped by row):")
        for line in res.lines():
            print(f"    {line}")
        if save:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            out = SAVE_DIR / (img.stem + ".vision.txt")
            out.write_text(res.text + "\n\n# lines\n" + "\n".join(res.lines()) + "\n", encoding="utf-8")
            print(f"  saved {out.relative_to(ROOT)}")

    print(f"\n{calls} Vision request(s) made. {'All good.' if not failures else f'{failures} problem(s).'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
