"""Optional accounts and saved ticket history (P4-04, design 2026-10-29)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

LOGIN_TTL = 15 * 60
SESSION_TTL = 30 * 86400


def normalise_email(s: Optional[str]) -> Optional[str]:
    raise NotImplementedError


class Accounts:
    def __init__(self, path, clock: Callable[[], float] = time.time):
        raise NotImplementedError

    def request_login(self, email: str) -> Optional[str]:
        raise NotImplementedError

    def redeem_login(self, token: str) -> Optional[str]:
        raise NotImplementedError

    def user_for_session(self, token: Optional[str]) -> Optional[dict]:
        raise NotImplementedError

    def end_session(self, token: Optional[str]) -> None:
        raise NotImplementedError


ACCOUNTS_MODULE_END = True
