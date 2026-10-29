import json
import logging

import pytest

from lottery_checker.mailer import MailError, send_login_link

URL = "https://toto.zenqi.cc/#login=abc123"
ENV = {"CLOUDFLARE_EMAIL_TOKEN": "tok-secret", "CLOUDFLARE_ACCOUNT_ID": "acct1"}


def test_sends_one_request_with_the_link_and_bearer_token():
    seen = []

    def post(url, headers, body):
        seen.append((url, headers, json.loads(body)))
        return 200, "{}"

    send_login_link("ann@example.com", URL, env=ENV, post=post)
    (url, headers, body), = seen
    assert "acct1" in url and url.startswith("https://api.cloudflare.com/")
    assert headers["Authorization"] == "Bearer tok-secret"
    assert body["to"] == "ann@example.com" and body["from"] == "login@zenqi.cc"
    assert URL in body["text"]


def test_sender_can_be_overridden():
    seen = []
    send_login_link("a@x.com", URL, env={**ENV, "TOTO_MAIL_FROM": "hi@zenqi.cc"},
                    post=lambda u, h, b: seen.append(json.loads(b)) or (200, "{}"))
    assert seen[0]["from"] == "hi@zenqi.cc"


def test_http_error_raises_mailerror_without_leaking_secrets():
    with pytest.raises(MailError) as e:
        send_login_link("a@x.com", URL, env=ENV, post=lambda u, h, b: (403, "denied tok-secret"))
    assert "tok-secret" not in str(e.value)


def test_transport_failure_raises_mailerror():
    def boom(u, h, b):
        raise OSError("down")

    with pytest.raises(MailError):
        send_login_link("a@x.com", URL, env=ENV, post=boom)


def test_unconfigured_raises_mailerror():
    with pytest.raises(MailError):
        send_login_link("a@x.com", URL, env={}, post=lambda *a: (200, "{}"))


def test_dev_links_logs_the_link_but_never_the_email(caplog):
    caplog.set_level(logging.WARNING)
    send_login_link("ann@example.com", URL, env={"TOTO_DEV_LINKS": "1"}, post=lambda *a: 1 / 0)
    assert URL in caplog.text and "ann@example.com" not in caplog.text
