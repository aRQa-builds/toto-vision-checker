"""Owner view of the results database (owner's request, 22 Oct 2026), on
Grayskull and on the owner's phone.

The site is public, so the view is locked with an owner key:
- data/owner.key, made on Grayskull with  py -3 -m lottery_checker.owner
  (prints the key and the two links). --new replaces it; old links stop working.
- No key file: the owner view is off (404).
- The page reads the key from the link's #fragment, which browsers never send
  to a server or a log, keeps it on that device, and sends it in the
  X-Owner-Key header. It never goes in a URL query.
- 256-bit random key, compared in constant time; wrong keys are also slowed
  down per client (OWNER_FAILS_PER_HOUR).
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
OWNER_FAILS_PER_HOUR = 10
SITE = "https://toto.zenqi.cc"
LOCAL = "http://127.0.0.1:8765"


def key_path(data_dir: Path) -> Path:
    return Path(data_dir) / "owner.key"


def owner_key(data_dir: Path) -> Optional[str]:
    try:
        k = key_path(data_dir).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return k if len(k) >= 32 else None


def check(given: Optional[str], data_dir: Path) -> Optional[bool]:
    """None: owner view off (no key file). Else whether the key is right."""
    k = owner_key(data_dir)
    if k is None:
        return None
    return bool(given) and secrets.compare_digest(given.strip().encode(), k.encode())


def make_key(data_dir: Path) -> str:
    k = secrets.token_hex(32)
    p = key_path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(k, encoding="utf-8")
    return k


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Owner key for the results view.")
    p.add_argument("--new", action="store_true", help="replace the key (old links stop working)")
    p.add_argument("--data", default=str(ROOT / "data"))
    a = p.parse_args(argv)
    data_dir = Path(a.data)
    k = owner_key(data_dir)
    if a.new or k is None:
        k = make_key(data_dir)
        print("New owner key made: data\\owner.key")
    print("\nOwner view links (the key is after #, so it is never sent to the server or logged):")
    print(f"  Grayskull : {LOCAL}/owner#key={k}")
    print(f"  Phone     : {SITE}/owner#key={k}")
    print("\nOpen each link once; the device remembers the key. Don't share these links.")
    print("Lost phone or leaked link: py -3 -m lottery_checker.owner --new")
    return 0


if __name__ == "__main__":
    sys.exit(main())
