"""P4-04 saved history: whitelist, isolation, purge, deletion."""
import sqlite3
from datetime import datetime, timezone

import pytest

from lottery_checker.accounts import HISTORY_LIMIT, Accounts, clean_entry

PAYLOAD = {"game": "toto", "draw_no": 4227, "draw_date": "2026-10-19",
           "bets": [{"label": "Ordinary", "numbers": ["02", "15", "19", "20", "27", "30"], "stake": 1.0}],
           "stake": 1.0, "won": 0.0, "claim_by": "2027-01-17"}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def ts(y, m, d):
    return datetime(y, m, d, 12, tzinfo=timezone.utc).timestamp()


@pytest.fixture
def clock():
    return Clock(ts(2026, 10, 29))


@pytest.fixture
def acc(tmp_path, clock):
    return Accounts(tmp_path / "accounts.db", clock=clock)


def user(acc, email):
    return acc.user_for_session(acc.redeem_login(acc.request_login(email)))["id"]


def test_save_and_list(acc):
    uid = user(acc, "ann@example.com")
    eid = acc.save_history(uid, PAYLOAD)
    rows = acc.list_history(uid)
    assert [r["id"] for r in rows] == [eid]
    assert rows[0]["draw_no"] == 4227
    assert rows[0]["bets"][0]["numbers"][0] == "02"
    assert rows[0]["won"] == 0.0


def test_unknown_fields_and_serials_never_reach_the_row(acc, tmp_path):
    uid = user(acc, "ann@example.com")
    dirty = dict(PAYLOAD, serial="A1234567890", line="TOTO 7777 SERIAL 99887766",
                 bets=[{"label": "Ordinary", "numbers": ["02", "15"], "stake": 1.0,
                        "line": "serial 55443322", "serial": "55443322"}])
    acc.save_history(uid, dirty)
    raw = (tmp_path / "accounts.db").read_bytes()
    for needle in (b"A1234567890", b"99887766", b"55443322", b"SERIAL"):
        assert needle not in raw


@pytest.mark.parametrize("bad", [
    dict(PAYLOAD, game="lotto"),
    dict(PAYLOAD, draw_no=0),
    dict(PAYLOAD, draw_date="19/10/2026"),
    dict(PAYLOAD, bets=[]),
    dict(PAYLOAD, bets=[{"label": "Ordinary", "numbers": ["A1234567890"], "stake": 1.0}]),
    dict(PAYLOAD, bets=[{"label": "<script>", "numbers": ["02"], "stake": 1.0}]),
    dict(PAYLOAD, stake=-1),
    dict(PAYLOAD, claim_by="soon"),
])
def test_bad_entries_are_refused(bad):
    with pytest.raises(ValueError):
        clean_entry(bad)


def test_pending_prize_is_kept_as_none_not_zero(acc):
    uid = user(acc, "ann@example.com")
    acc.save_history(uid, dict(PAYLOAD, won=None))
    assert acc.list_history(uid)[0]["won"] is None


def test_users_cannot_see_or_delete_each_others_entries(acc):
    ann, bob = user(acc, "ann@example.com"), user(acc, "bob@example.com")
    eid = acc.save_history(ann, PAYLOAD)
    assert acc.list_history(bob) == []
    assert acc.delete_history(bob, eid) is False
    assert len(acc.list_history(ann)) == 1
    assert acc.delete_history(ann, eid) is True
    assert acc.list_history(ann) == []


def test_history_is_capped(acc):
    uid = user(acc, "ann@example.com")
    for _ in range(HISTORY_LIMIT):
        acc.save_history(uid, PAYLOAD)
    with pytest.raises(ValueError):
        acc.save_history(uid, PAYLOAD)


def test_purge_after_is_end_of_next_year(acc, tmp_path):
    uid = user(acc, "ann@example.com")
    acc.save_history(uid, PAYLOAD)
    db = sqlite3.connect(tmp_path / "accounts.db")
    assert db.execute("SELECT purge_after FROM history").fetchone()[0] == "2027-12-31"


def test_purge_removes_expired_history(acc, clock):
    uid = user(acc, "ann@example.com")
    acc.save_history(uid, PAYLOAD)
    clock.t = ts(2028, 1, 2)
    acc.purge()
    assert acc.list_history(uid) == []


def test_purge_removes_used_and_expired_tokens(acc, clock, tmp_path):
    acc.request_login("old@example.com")
    clock.t += 10_000
    acc.purge()
    db = sqlite3.connect(tmp_path / "accounts.db")
    assert db.execute("SELECT COUNT(*) FROM login_tokens").fetchone()[0] == 0


def test_delete_account_removes_everything(acc):
    uid = user(acc, "ann@example.com")
    sess = acc.redeem_login(acc.request_login("ann@example.com"))
    acc.save_history(uid, PAYLOAD)
    acc.delete_account(uid)
    assert acc.list_history(uid) == []
    assert acc.user_for_session(sess) is None
