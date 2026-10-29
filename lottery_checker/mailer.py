"""Sign-in mail through Cloudflare Email Service (P4-04)."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("toto.mailer")
ENDPOINT = "https://api.cloudflare.com/client/v4/accounts/{account}/email/sending/send"
SUBJECT = "Your TOTO Check sign-in link"
BODY = ("Open this link to sign in to TOTO Check. It works once and expires in 15 minutes.\n\n{url}\n\n"
        "If you did not ask for this, ignore this email.")


class MailError(RuntimeError):
    pass


def _post(url: str, headers: dict, body: bytes):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return (resp.status, resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return (e.code, e.read().decode("utf-8", "replace"))


def send_login_link(email: str, url: str, env=None, post=None) -> None:
    if env is None:
        env = os.environ

    token = env.get("CLOUDFLARE_EMAIL_TOKEN")
    account = env.get("CLOUDFLARE_ACCOUNT_ID")

    if not token or not account:
        if env.get("TOTO_DEV_LINKS") == "1":
            log.warning("DEV sign-in link: %s", url)
            return
        raise MailError("sign-in mail is not configured")

    from_addr = env.get("TOTO_MAIL_FROM", "login@zenqi.cc")
    body_dict = {
        "from": from_addr,
        "to": email,
        "subject": SUBJECT,
        "text": BODY.format(url=url)
    }
    body_bytes = json.dumps(body_dict).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    endpoint_url = ENDPOINT.format(account=account)

    if post is None:
        post = _post

    try:
        status, text = post(endpoint_url, headers, body_bytes)
    except OSError as e:
        raise MailError(f"sign-in mail could not be sent ({type(e).__name__})") from None

    if not (200 <= status < 300):
        raise MailError(f"sign-in mail was refused (HTTP {status})")


MAILER_END = True
