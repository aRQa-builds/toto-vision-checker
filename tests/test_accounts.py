"""P4-04 accounts core: login tokens and sessions."""
import sqlite3

import pytest

from lottery_checker.accounts import LOGIN_TTL, SESSION_TTL, Accounts, normalise_email


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def acc(tmp_path, clock):
    return Accounts(tmp_path / "accounts.db", clock=clock)


def test_normalise_email():
    assert normalise_email("  Ann@Example.COM ") == "ann@example.com"
    assert normalise_email("nope") is None
    assert normalise_email("a b@example.com") is None
    assert normalise_email(None) is None
    assert normalise_email("a@" + "x" * 300 + ".com") is None


def test_bad_email_gets_no_token(acc):
    assert acc.request_login("nope") is None


def test_login_roundtrip_makes_user_and_session(acc):
    tok = acc.request_login("Ann@example.com")
    sess = acc.redeem_login(tok)
    assert sess
    user = acc.user_for_session(sess)
    assert user["email"] == "ann@example.com"


def test_login_token_is_single_use(acc):
    tok = acc.request_login("ann@example.com")
    assert acc.redeem_login(tok)
    assert acc.redeem_login(tok) is None


def test_login_token_expires(acc, clock):
    tok = acc.request_login("ann@example.com")
    clock.t += LOGIN_TTL + 1
    assert acc.redeem_login(tok) is None


def test_unknown_token_is_refused(acc):
    assert acc.redeem_login("not-a-token") is None
    assert acc.user_for_session("not-a-session") is None


def test_second_login_reuses_the_user(acc):
    a = acc.user_for_session(acc.redeem_login(acc.request_login("ann@example.com")))
    b = acc.user_for_session(acc.redeem_login(acc.request_login("ANN@example.com")))
    assert a["id"] == b["id"]


def test_session_expires(acc, clock):
    sess = acc.redeem_login(acc.request_login("ann@example.com"))
    clock.t += SESSION_TTL + 1
    assert acc.user_for_session(sess) is None


def test_end_session(acc):
    sess = acc.redeem_login(acc.request_login("ann@example.com"))
    acc.end_session(sess)
    assert acc.user_for_session(sess) is None


def test_tokens_are_stored_only_as_hashes(acc, tmp_path):
    tok = acc.request_login("ann@example.com")
    sess = acc.redeem_login(tok)
    raw = (tmp_path / "accounts.db").read_bytes()
    assert tok.encode() not in raw
    assert sess.encode() not in raw
    assert len(tok) >= 40 and tok != sess
