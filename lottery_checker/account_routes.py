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
    accounts = Accounts(Path(data_dir) / "accounts.db")
    accounts.purge()
    last_purge = {"day": date.today()}
    limiter = LinkLimiter()
    send = send_link or mailer.send_login_link
    public = os.environ.get("TOTO_PUBLIC_URL", "https://toto.zenqi.cc").rstrip("/")

    def csrf(request: Request):
        if request.headers.get("x-toto") != "1":
            raise HTTPException(status_code=403, detail={"problems": ["Missing request header."]})

    def current(request: Request):
        session = accounts.user_for_session(request.cookies.get(COOKIE))
        if not session:
            raise HTTPException(status_code=401, detail={"problems": ["Sign in to use your history."]})
        return session

    @app.post("/api/auth/request")
    async def request_login(request: Request, body: EmailIn):
        csrf(request)
        email = normalise_email(body.email)
        if not email:
            raise HTTPException(status_code=422, detail={"problems": ["That doesn't look like an email address."]})

        if not limiter.allow(email, client_ip(request)):
            raise HTTPException(status_code=429, detail={"problems": ["Too many sign-in emails. Try again later."]})

        today = date.today()
        if last_purge["day"] != today:
            accounts.purge()
            last_purge["day"] = today

        token = accounts.request_login(email)
        try:
            send(email, f"{public}/#login={token}")
        except mailer.MailError:
            audit.warning("auth: sign-in mail failed")
            raise HTTPException(status_code=503, detail={"problems": ["We couldn't send the email. Try again later."]})

        return {"ok": True, "message": "If that address is valid, a sign-in link is on its way."}

    @app.post("/api/auth/verify")
    async def verify_login(request: Request, body: TokenIn):
        csrf(request)
        session = accounts.redeem_login(body.token)
        if not session:
            raise HTTPException(status_code=400, detail={"problems": ["That sign-in link has expired or was already used. Ask for a new one."]})

        user = accounts.user_for_session(session)
        audit.info("auth: signed in user=%s", user["id"])

        response = JSONResponse({"ok": True, "email": user["email"]})
        response.set_cookie(
            key=COOKIE,
            value=session,
            max_age=SESSION_TTL,
            httponly=True,
            samesite="lax",
            path="/",
            secure=request.headers.get("x-forwarded-proto") == "https",
        )
        return response

    @app.post("/api/auth/logout")
    async def logout(request: Request):
        csrf(request)
        token = request.cookies.get(COOKIE)
        user = accounts.user_for_session(token)
        accounts.end_session(token)
        if user:
            audit.info("auth: signed out user=%s", user["id"])
        response = JSONResponse({"ok": True})
        response.delete_cookie(key=COOKIE, path="/")
        return response

    @app.get("/api/me")
    async def me(request: Request):
        user = accounts.user_for_session(request.cookies.get(COOKIE))
        if user:
            return {"signed_in": True, "email": user["email"]}
        return {"signed_in": False}

    @app.get("/api/history")
    async def history(request: Request):
        user = current(request)
        return {"entries": accounts.list_history(user["id"])}

    @app.post("/api/history")
    async def save_history(request: Request, body: dict):
        csrf(request)
        user = current(request)
        try:
            entry_id = accounts.save_history(user["id"], body)
        except ValueError as e:
            raise HTTPException(status_code=422, detail={"problems": [str(e)]})
        audit.info("history: saved user=%s entry=%s", user["id"], entry_id)
        return {"ok": True, "id": entry_id}

    @app.delete("/api/history/{entry_id}")
    async def delete_history_entry(request: Request, entry_id: int):
        csrf(request)
        user = current(request)
        if not accounts.delete_history(user["id"], entry_id):
            raise HTTPException(status_code=404, detail={"problems": ["No such entry."]})
        audit.info("history: deleted user=%s entry=%s", user["id"], entry_id)
        return {"ok": True}

    @app.delete("/api/account")
    async def delete_account_endpoint(request: Request):
        csrf(request)
        user = current(request)
        accounts.delete_account(user["id"])
        audit.info("account: deleted user=%s", user["id"])
        response = JSONResponse({"ok": True})
        response.delete_cookie(key=COOKIE, path="/")
        return response


ROUTES_END = True
