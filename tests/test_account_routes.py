"""P4-04 routes: sign-in, history, CSRF guard, isolation, anonymous API unchanged."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api  # noqa: E402

H = {"X-Toto": "1"}
ENTRY = {"game": "toto", "draw_no": 4227, "draw_date": "2026-10-19",
         "bets": [{"label": "Ordinary", "numbers": ["02", "15", "19", "20", "27", "30"], "stake": 1.0}],
         "stake": 1.0, "won": 0.0, "claim_by": None}


@pytest.fixture
def sent():
    return []


@pytest.fixture
def client(tmp_path, sent):
    app = api.create_app(data_dir=tmp_path, send_link=lambda email, url: sent.append((email, url)))
    return TestClient(app)


def sign_in(client, sent, email="ann@example.com"):
    assert client.post("/api/auth/request", json={"email": email}, headers=H).status_code == 200
    token = sent[-1][1].split("#login=")[1]
    r = client.post("/api/auth/verify", json={"token": token}, headers=H)
    assert r.status_code == 200
    return r


def test_request_sends_one_link_and_replies_generically(client, sent):
    r = client.post("/api/auth/request", json={"email": "ann@example.com"}, headers=H)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert len(sent) == 1 and sent[0][1].startswith("https://toto.zenqi.cc/#login=")
    r2 = client.post("/api/auth/request", json={"email": "never-seen@example.com"}, headers=H)
    assert r2.json() == r.json()


def test_bad_email_is_422_and_sends_nothing(client, sent):
    assert client.post("/api/auth/request", json={"email": "nope"}, headers=H).status_code == 422
    assert sent == []


def test_post_without_csrf_header_is_refused(client, sent):
    assert client.post("/api/auth/request", json={"email": "ann@example.com"}).status_code == 403
    assert sent == []


def test_verify_sets_a_locked_down_cookie(client, sent):
    client.post("/api/auth/request", json={"email": "ann@example.com"}, headers=H)
    token = sent[-1][1].split("#login=")[1]
    r = client.post("/api/auth/verify", json={"token": token}, headers={**H, "X-Forwarded-Proto": "https"})
    cookie = r.headers["set-cookie"].lower()
    assert "toto_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "secure" in cookie


def test_verify_token_cannot_be_reused(client, sent):
    client.post("/api/auth/request", json={"email": "ann@example.com"}, headers=H)
    token = sent[-1][1].split("#login=")[1]
    assert client.post("/api/auth/verify", json={"token": token}, headers=H).status_code == 200
    assert client.post("/api/auth/verify", json={"token": token}, headers=H).status_code == 400


def test_me_signed_out_and_in(client, sent):
    assert client.get("/api/me").json() == {"signed_in": False}
    sign_in(client, sent)
    assert client.get("/api/me").json() == {"signed_in": True, "email": "ann@example.com"}


def test_history_requires_sign_in(client):
    assert client.get("/api/history").status_code == 401
    assert client.post("/api/history", json=ENTRY, headers=H).status_code == 401
    assert client.delete("/api/account", headers=H).status_code == 401


def test_save_list_delete_roundtrip(client, sent):
    sign_in(client, sent)
    saved = client.post("/api/history", json=ENTRY, headers=H)
    assert saved.status_code == 200
    eid = saved.json()["id"]
    assert [r["id"] for r in client.get("/api/history").json()["entries"]] == [eid]
    assert client.delete(f"/api/history/{eid}", headers=H).status_code == 200
    assert client.get("/api/history").json()["entries"] == []
    assert client.delete(f"/api/history/{eid}", headers=H).status_code == 404


def test_bad_entry_is_422(client, sent):
    sign_in(client, sent)
    r = client.post("/api/history", json=dict(ENTRY, game="lotto"), headers=H)
    assert r.status_code == 422


def test_two_users_are_isolated(tmp_path, sent):
    app = api.create_app(data_dir=tmp_path, send_link=lambda e, u: sent.append((e, u)))
    ann, bob = TestClient(app), TestClient(app)
    sign_in(ann, sent, "ann@example.com")
    eid = ann.post("/api/history", json=ENTRY, headers=H).json()["id"]
    sign_in(bob, sent, "bob@example.com")
    assert bob.get("/api/history").json()["entries"] == []
    assert bob.delete(f"/api/history/{eid}", headers=H).status_code == 404


def test_logout_ends_the_session(client, sent):
    sign_in(client, sent)
    assert client.post("/api/auth/logout", headers=H).status_code == 200
    assert client.get("/api/me").json() == {"signed_in": False}


def test_delete_account_removes_data_and_session(client, sent):
    sign_in(client, sent)
    client.post("/api/history", json=ENTRY, headers=H)
    assert client.delete("/api/account", headers=H).status_code == 200
    assert client.get("/api/me").json() == {"signed_in": False}
    sign_in(client, sent)
    assert client.get("/api/history").json()["entries"] == []


def test_link_requests_are_rate_limited(client, sent):
    codes = [client.post("/api/auth/request", json={"email": "ann@example.com"}, headers=H).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    assert len(sent) == 3


def test_mail_failure_is_503_not_a_crash(tmp_path):
    from lottery_checker.mailer import MailError

    def boom(email, url):
        raise MailError("down")

    c = TestClient(api.create_app(data_dir=tmp_path, send_link=boom))
    assert c.post("/api/auth/request", json={"email": "ann@example.com"}, headers=H).status_code == 503


def test_signed_in_user_is_never_in_logs_by_email(client, sent, caplog):
    import logging
    caplog.set_level(logging.INFO)
    sign_in(client, sent)
    assert "ann@example.com" not in caplog.text
    assert "signed in user=" in caplog.text


def test_purge_runs_again_when_the_day_changes(tmp_path, sent, monkeypatch):
    from datetime import date, timedelta
    from lottery_checker import account_routes, accounts as acc_mod

    calls = []
    real = acc_mod.Accounts.purge
    monkeypatch.setattr(acc_mod.Accounts, "purge", lambda self: (calls.append(1), real(self))[1])
    c = TestClient(api.create_app(data_dir=tmp_path, send_link=lambda e, u: sent.append((e, u))))
    start = len(calls)                      # one purge at start-up
    c.post("/api/auth/request", json={"email": "a@example.com"}, headers=H)
    assert len(calls) == start              # same day: no extra purge

    class Tomorrow(date):
        @classmethod
        def today(cls):
            return date.today() + timedelta(days=1)

    monkeypatch.setattr(account_routes, "date", Tomorrow)
    c.post("/api/auth/request", json={"email": "b@example.com"}, headers=H)
    assert len(calls) == start + 1


def test_anonymous_api_still_works_without_a_session(client):
    assert client.get("/api/health").json()["ok"] is True
