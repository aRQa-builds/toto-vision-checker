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
    raise NotImplementedError


def send_login_link(email: str, url: str, env=None, post=None) -> None:
    raise NotImplementedError


MAILER_END = True
