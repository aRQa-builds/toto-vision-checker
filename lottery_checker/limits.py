"""How many images the site sends to Google Vision (owner's rules, 22 Oct 2026).

Ticket photos
- Normal: VISION_PER_HOUR per person (connection) an hour, VISION_PER_DAY for the
  whole site a day (api.py; env TOTO_VISION_PER_HOUR / TOTO_VISION_PER_DAY).
- Testing phase: much higher (TESTING_PER_HOUR / TESTING_PER_DAY) for a limited
  time, 7 days by default. Opened, renewed and closed with tools/testing-phase.ps1,
  which writes data/testing_phase.json. When it runs out, the normal limits come
  back by themselves; the site banner and setup-web.ps1 prompt the owner to renew
  or close it out for deployment. The server reads the file on every request, so
  no restart is needed.

Official-result screenshots
- No per-person limit: people screenshot a whole sitting of results at once, and
  every complete read helps others through the shared results (P3-07).
- One site-wide safety net, SCREENSHOTS_PER_DAY (env TOTO_SCREENSHOTS_PER_DAY,
  default 1000, 0 = none), far above what people do, so a runaway script can't
  run up the Vision bill. The Google Cloud quota is the last backstop.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

TESTING_PER_HOUR = int(os.environ.get("TOTO_TESTING_PER_HOUR", "200"))
TESTING_PER_DAY = int(os.environ.get("TOTO_TESTING_PER_DAY", "1000"))
SCREENSHOTS_PER_DAY = int(os.environ.get("TOTO_SCREENSHOTS_PER_DAY", "1000"))


@dataclass
class TestingPhase:
    active: bool
    ends: datetime
    started: Optional[datetime] = None

    def days_left(self, now: Optional[datetime] = None) -> float:
        now = now or datetime.now(timezone.utc)
        return (self.ends - now).total_seconds() / 86400

    def view(self, now: Optional[datetime] = None) -> dict:
        left = self.days_left(now)
        return {"active": self.active, "ends": self.ends.isoformat(),
                "days_left": max(0, round(left, 1)), "last_day": self.active and left <= 1}


def _parse(ts: str) -> datetime:
    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def testing_phase(data_dir: Path, now: Optional[datetime] = None) -> Optional[TestingPhase]:
    """The testing phase from data/testing_phase.json: active, ended (file still
    there, so the owner is prompted), or None (closed out / never opened)."""
    p = Path(data_dir) / "testing_phase.json"
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text(encoding="utf-8-sig"))
        ends = _parse(rec["ends"])
        started = _parse(rec["started"]) if rec.get("started") else None
    except (OSError, ValueError, KeyError, TypeError):
        return None                                   # a broken file never raises the limits
    now = now or datetime.now(timezone.utc)
    return TestingPhase(active=now < ends, ends=ends, started=started)


def photo_limits(data_dir: Path, per_hour: int, per_day: int) -> tuple[int, int]:
    """(per hour per person, per day site-wide) for ticket photos right now."""
    tp = testing_phase(data_dir)
    if tp and tp.active:
        return max(per_hour, TESTING_PER_HOUR), max(per_day, TESTING_PER_DAY)
    return per_hour, per_day
