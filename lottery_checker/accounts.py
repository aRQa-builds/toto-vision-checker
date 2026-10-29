"""Optional accounts and saved ticket history (P4-04, design 2026-10-29)."""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import secrets
import sqlite3
import time
from datetime import date, datetime, timezone
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


HISTORY_LIMIT = 500


def clean_entry(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")

    # Validate game
    game = payload.get("game")
    if game not in ("toto", "4d"):
        raise ValueError("Game must be 'toto' or '4d'")

    # Validate draw_no
    draw_no = payload.get("draw_no")
    if isinstance(draw_no, bool) or not isinstance(draw_no, int):
        raise ValueError("draw_no must be an integer")
    if draw_no < 1 or draw_no > 99999:
        raise ValueError("draw_no must be between 1 and 99999")

    # Validate draw_date
    draw_date = payload.get("draw_date")
    try:
        date.fromisoformat(draw_date)
    except (ValueError, TypeError):
        raise ValueError("draw_date must be a valid ISO date (YYYY-MM-DD)")

    # Validate claim_by
    claim_by = payload.get("claim_by")
    if claim_by is not None:
        try:
            date.fromisoformat(claim_by)
        except (ValueError, TypeError):
            raise ValueError("claim_by must be a valid ISO date (YYYY-MM-DD) or None")

    # Validate bets
    bets = payload.get("bets")
    if not isinstance(bets, list):
        raise ValueError("bets must be a list")
    if len(bets) < 1 or len(bets) > 30:
        raise ValueError("bets must contain between 1 and 30 entries")

    cleaned_bets = []
    for bet in bets:
        if not isinstance(bet, dict):
            raise ValueError("Each bet must be a dictionary")

        label = bet.get("label")
        if not isinstance(label, str) or not re.match(r"^[A-Za-z0-9 ]{1,40}$", label):
            raise ValueError("bet label must match ^[A-Za-z0-9 ]{1,40}$")

        numbers = bet.get("numbers")
        if not isinstance(numbers, list):
            raise ValueError("bet numbers must be a list")
        if len(numbers) < 1 or len(numbers) > 12:
            raise ValueError("bet numbers must contain between 1 and 12 items")
        for num in numbers:
            if not isinstance(num, str) or not re.match(r"^\d{1,4}$", num):
                raise ValueError("each number must be a string of digits with length 1-4")

        stake = bet.get("stake")
        if isinstance(stake, bool) or not isinstance(stake, (int, float)):
            raise ValueError("bet stake must be a number")
        if stake < 0 or stake > 10000:
            raise ValueError("bet stake must be between 0 and 10000")

        cleaned_bets.append({
            "label": label,
            "numbers": numbers,
            "stake": float(stake)
        })

    # Validate stake (whole ticket)
    stake = payload.get("stake")
    if isinstance(stake, bool) or not isinstance(stake, (int, float)):
        raise ValueError("stake must be a number")
    if stake < 0 or stake > 100000:
        raise ValueError("stake must be between 0 and 100000")

    # Validate won
    won = payload.get("won")
    if won is not None:
        if isinstance(won, bool) or not isinstance(won, (int, float)):
            raise ValueError("won must be a number or None")
        if won < 0 or won > 1e9:
            raise ValueError("won must be between 0 and 1e9")

    return {
        "game": game,
        "draw_no": draw_no,
        "draw_date": draw_date,
        "bets": cleaned_bets,
        "stake": stake,
        "won": won,
        "claim_by": claim_by
    }


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

    def save_history(self, user_id: int, payload: dict) -> int:
        cleaned = clean_entry(payload)

        with self._db() as db:
            # Check history limit
            count = db.execute(
                "SELECT COUNT(*) FROM history WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            if count >= HISTORY_LIMIT:
                raise ValueError("Your history is full. Delete some entries first.")

            now = self.clock()
            year = datetime.fromtimestamp(now, timezone.utc).year

            # Insert new record
            cur = db.execute(
                "INSERT INTO history (user_id, saved_at, game, draw_no, draw_date, bets, stake, won, claim_by, purge_after) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    now,
                    cleaned["game"],
                    cleaned["draw_no"],
                    cleaned["draw_date"],
                    json.dumps(cleaned["bets"]),
                    cleaned["stake"],
                    cleaned["won"],
                    cleaned["claim_by"],
                    f"{year+1}-12-31"
                )
            )

            return int(cur.lastrowid)

    def list_history(self, user_id: int) -> list:
        with self._db() as db:
            rows = db.execute(
                "SELECT id, saved_at, game, draw_no, draw_date, bets, stake, won, claim_by FROM history WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()

        result = []
        for row in rows:
            result.append({
                "id": int(row["id"]),
                "saved_at": row["saved_at"],
                "game": row["game"],
                "draw_no": row["draw_no"],
                "draw_date": row["draw_date"],
                "bets": json.loads(row["bets"]),
                "stake": row["stake"],
                "won": row["won"],
                "claim_by": row["claim_by"]
            })
        return result

    def delete_history(self, user_id: int, entry_id: int) -> bool:
        with self._db() as db:
            cur = db.execute(
                "DELETE FROM history WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            )
            return cur.rowcount == 1

    def delete_account(self, user_id: int) -> None:
        with self._db() as db:
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def purge(self) -> None:
        now = self.clock()
        today = datetime.fromtimestamp(now, timezone.utc).date().isoformat()

        with self._db() as db:
            # Delete history with purge_after < today
            db.execute(
                "DELETE FROM history WHERE purge_after < ?",
                (today,),
            )
            # Delete login_tokens with expires_at < now OR used_at IS NOT NULL
            db.execute(
                "DELETE FROM login_tokens WHERE expires_at < ? OR used_at IS NOT NULL",
                (now,),
            )
            # Delete sessions with expires_at < now
            db.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (now,),
            )


ACCOUNTS_MODULE_END = True
