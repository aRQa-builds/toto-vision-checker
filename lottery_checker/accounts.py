"""Optional accounts and saved ticket history (P4-04, design 2026-10-29)."""
from __future__ import annotations

import contextlib
import hashlib
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional

LOGIN_TTL = 15 * 60
SESSION_TTL = 30 * 86400

_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    last_login REAL
);
CREATE TABLE IF NOT EXISTS login_tokens (
    token_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    expires_at REAL NOT NULL,
    used_at REAL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    saved_at REAL NOT NULL,
    game TEXT NOT NULL,
    draw_no INTEGER NOT NULL,
    draw_date TEXT NOT NULL,
    bets TEXT NOT NULL,
    stake REAL NOT NULL,
    won REAL,
    claim_by TEXT,
    purge_after TEXT NOT NULL
);
"""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalise_email(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = s.strip().lower()
    if len(s) > 254 or not _EMAIL_RE.match(s):
        return None
    return s


class Accounts:
    def __init__(self, path, clock: Callable[[], float] = time.time):
        self.path = Path(path)
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextlib.contextmanager
    def _db(self):
        db = sqlite3.connect(str(self.path))
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            yield db
            db.commit()
        finally:
            db.close()

    def request_login(self, email: str) -> Optional[str]:
        norm = normalise_email(email)
        if norm is None:
            return None
        token = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO login_tokens (token_hash, email, expires_at) VALUES (?, ?, ?)",
                (_hash(token), norm, self.clock() + LOGIN_TTL),
            )
        return token

    def redeem_login(self, token: str) -> Optional[str]:
        if not token:
            return None
        th = _hash(token)
        now = self.clock()
        with self._db() as db:
            row = db.execute(
                "SELECT email, expires_at FROM login_tokens WHERE token_hash = ?",
                (th,),
            ).fetchone()
            if row is None or row["expires_at"] <= now:
                return None
            cur = db.execute(
                "UPDATE login_tokens SET used_at = ? WHERE token_hash = ? AND used_at IS NULL",
                (now, th),
            )
            if cur.rowcount != 1:
                return None
            db.execute(
                "INSERT OR IGNORE INTO users (email, created_at) VALUES (?, ?)",
                (row["email"], now),
            )
            db.execute("UPDATE users SET last_login = ? WHERE email = ?", (now, row["email"]))
            user_id = db.execute(
                "SELECT id FROM users WHERE email = ?", (row["email"],)
            ).fetchone()["id"]
            session = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_hash(session), user_id, now + SESSION_TTL),
            )
        return session

    def user_for_session(self, token: Optional[str]) -> Optional[dict]:
        if not token:
            return None
        with self._db() as db:
            row = db.execute(
                "SELECT u.id AS id, u.email AS email FROM sessions s "
                "JOIN users u ON u.id = s.user_id "
                "WHERE s.token_hash = ? AND s.expires_at > ?",
                (_hash(token), self.clock()),
            ).fetchone()
        if row is None:
            return None
        return {"id": int(row["id"]), "email": row["email"]}

    def end_session(self, token: Optional[str]) -> None:
        if not token:
            return
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash(token),))


ACCOUNTS_MODULE_END = True
