"""P4-04 account routes: optional magic-link sign-in and saved history."""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import mailer
from .accounts import SESSION_TTL, Accounts, normalise_email
from .limits import LinkLimiter

COOKIE = "toto_session"
audit = logging.getLogger("toto.accounts")


class EmailIn(BaseModel):
    email: str


class TokenIn(BaseModel):
    token: str


def add_account_routes(app: FastAPI, data_dir: Path, client_ip, send_link=None) -> None:
    return None


ROUTES_END = True
