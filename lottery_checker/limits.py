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
import time
from collections import defaultdict, deque
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


class LinkLimiter:
    def __init__(self, per_email: Optional[int] = None, per_ip: Optional[int] = None,
                 per_day: Optional[int] = None, clock=None):
        self.per_email = per_email if per_email is not None else int(os.environ.get("TOTO_LINK_PER_EMAIL", "3"))
        self.per_ip = per_ip if per_ip is not None else int(os.environ.get("TOTO_LINK_PER_IP", "10"))
        self.per_day = per_day if per_day is not None else int(os.environ.get("TOTO_LINK_PER_DAY", "200"))
        self.clock = clock or time.time
        self.emails: defaultdict[str, deque] = defaultdict(deque)
        self.ips: defaultdict[str, deque] = defaultdict(deque)
        self.site: deque = deque()

    def allow(self, email: str, ip: str) -> bool:
        now = self.clock()
        key_email = email.strip().lower()

        # Clean old timestamps from email and ip deques (3600s window)
        while self.emails[key_email] and now - self.emails[key_email][0] > 3600:
            self.emails[key_email].popleft()
        while self.ips[ip] and now - self.ips[ip][0] > 3600:
            self.ips[ip].popleft()

        # Clean old timestamps from site deque (86400s window)
        while self.site and now - self.site[0] > 86400:
            self.site.popleft()

        # Check limits
        if len(self.emails[key_email]) >= self.per_email or \
           len(self.ips[ip]) >= self.per_ip or \
           len(self.site) >= self.per_day:
            return False

        # Record success
        self.emails[key_email].append(now)
        self.ips[ip].append(now)
        self.site.append(now)
        return True


LIMITER_END = True
