"""Web checker API (P4-02), served from Grayskull behind a tunnel.

Decision 21 Oct 2026: option 1, a small Python API on Grayskull running the
same tested package, with the Arcade Drum page served from the same origin.
The front end only ever calls these endpoints, so the API can later move to a
cloud host, or be replaced by in-browser Python, without touching the page.

Endpoints
- GET  /api/health                 liveness, and whether photo reading is on
- POST /api/ticket                 typed ticket -> what we read, per line, and
                                   whether each draw's result is on file
- POST /api/check                  ticket (+ typed results for draws not on
                                   file) -> reveal: headline, lines, stake
                                   check, claim date, ball marks
- POST /api/results/screenshot     screenshot(s) of the official page -> the
                                   numbers read, for the confirm screen
                                   (needs GOOGLE_VISION_API_KEY; 503 without)
- GET  /api/results/wanted         this year's draws still missing or waiting for a
                                   second screenshot, with each draw's official link
                                   (draw numbers only, never results)
- POST /api/results/contribute     screenshots of official results with no ticket,
                                   counted towards shared results (two must agree)
- GET  /owner, /api/owner/*        owner view of the results database (owner.key)
- POST /api/ticket/photo           photo of the ticket -> the ticket as text
                                   plus what we read (P3-02), for the confirm
                                   screen (needs the key; 503 without)

Guardrails
- No public results feed: /api/check only returns the draws on the ticket it
  was given, with Singapore Pools credited and linked. The only list of draws
  is the owner view (/owner, /api/owner/*), locked by data/owner.key (owner.py).
- The server never fetches Singapore Pools; only the scheduled capture does.
- Limits: request bodies capped by field, 60 API calls a minute per client,
  binds to 127.0.0.1 only (the tunnel connects locally).
- Ticket text is not stored or logged. Photos and screenshots are sent to
  Google Cloud Vision to read the text and are not kept.
- Vision costs money past 1,000 images a month (limits.py has the rules):
  ticket photos: VISION_PER_HOUR per person an hour (20) and VISION_PER_DAY for
  the site a day (150), much higher during a testing phase
  (tools/testing-phase.ps1); official-result screenshots: no per-person limit,
  only a site-wide daily safety net (1000). Over a limit the page says to type
  instead.

Run (from the project folder):  py -3 -m lottery_checker.api
"""
from __future__ import annotations

import base64
import os
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import fourd, toto
from .claim import claim_by
from .ingest import ATTRIBUTION, official_url
from .manual import EntryError, fourd_result, toto_result
from .reveal import SHARED_ATTRIBUTION, build_reveal
from . import diag, limits, owner, results_db, shared
from .store import load_ref
from .ticket import DrawRef, TicketError
from .ticket_entry import TicketDraft, parse_ticket

VERSION = "0.1.0"
MAX_TICKET = 4000
MAX_RESULT = 2000
MAX_IMAGES = 3
MAX_BATCH_IMAGES = 40          # a sitting's worth of results; the page sends more in groups of 40
MAX_IMAGE_BYTES = 7 * 1024 * 1024
RATE_PER_MIN = 60
VISION_PER_HOUR = int(os.environ.get("TOTO_VISION_PER_HOUR", "20"))
VISION_PER_DAY = int(os.environ.get("TOTO_VISION_PER_DAY", "150"))
ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


# ---------------------------------------------------------------- request models

class TicketIn(BaseModel):
    text: str = Field(..., max_length=MAX_TICKET)


class ResultIn(BaseModel):
    draw_no: int = Field(..., ge=1, le=99999)
    draw_date: Optional[date] = None
    numbers: str = Field(..., max_length=MAX_RESULT)
    amounts: dict[int, str] = Field(default_factory=dict)


class CheckIn(BaseModel):
    text: str = Field(..., max_length=MAX_TICKET)
    results: list[ResultIn] = Field(default_factory=list, max_length=12)


class ScreenshotIn(BaseModel):
    images: list[str] = Field(..., min_length=1, max_length=MAX_IMAGES)   # base64


class WantedDraw(BaseModel):
    draw_no: int = Field(..., ge=1, le=99999)
    draw_date: Optional[date] = None


class BatchShotsIn(BaseModel):
    images: list[str] = Field(..., min_length=1, max_length=MAX_BATCH_IMAGES)   # base64
    draws: list[WantedDraw] = Field(..., min_length=1, max_length=12)


class ContributeIn(BaseModel):
    images: list[str] = Field(..., min_length=1, max_length=MAX_BATCH_IMAGES)   # base64
    game: Optional[str] = Field(None, pattern="^(toto|4d)$")


class PhotoIn(BaseModel):
    image: str = Field(..., min_length=1, max_length=MAX_IMAGE_BYTES * 4 // 3 + 64)   # base64


# ---------------------------------------------------------------- app

def create_app(data_dir: Optional[Path] = None, recognize=None, send_link=None) -> FastAPI:
    data_dir = Path(data_dir or os.environ.get("TOTO_DATA", ROOT / "data"))
    app = FastAPI(title="ZenQi TOTO/4D checker", version=VERSION, docs_url=None, redoc_url=None)
    hits: dict[str, deque] = defaultdict(deque)
    vision_hits: dict[str, deque] = defaultdict(deque)
    vision_day = {"day": None, "count": 0, "screens": 0}

    def client_ip(request: Request) -> str:
        return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")

    def vision_allow(request: Request, n: int, kind: str = "photo") -> None:
        """Count n Vision images, or refuse. Ticket photos: per person an hour and
        per day (higher in a testing phase). Official-result screenshots: no
        per-person limit, only the site-wide daily safety net (limits.py)."""
        today = date.today()
        if vision_day["day"] != today:
            vision_day.update(day=today, count=0, screens=0)
        if kind == "screenshot":
            cap = limits.SCREENSHOTS_PER_DAY
            if cap and vision_day["screens"] + n > cap:
                raise HTTPException(429, {"problems": ["Screenshot reading is very busy today. "
                                                       "Type the numbers instead, or try again tomorrow."]})
            vision_day["screens"] += n
            return
        per_hour, per_day = limits.photo_limits(data_dir, VISION_PER_HOUR, VISION_PER_DAY)
        if vision_day["count"] + n > per_day:
            raise HTTPException(429, {"problems": ["Photo reading has reached today's limit. "
                                                   "Type the ticket instead, or try again tomorrow."]})
        now, q = time.monotonic(), vision_hits[client_ip(request)]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) + n > per_hour:
            raise HTTPException(429, {"problems": ["That's a lot of ticket photos in an hour. "
                                                   "Type the ticket instead, or try again later."]})
        q.extend([now] * n)
        vision_day["count"] += n

    def decode_image(b64: str, what: str) -> bytes:
        try:
            raw = base64.b64decode(b64.split(",")[-1], validate=True)
        except ValueError:
            raise HTTPException(422, {"problems": [f"That file isn't an image we can read."]}) from None
        if not raw:
            raise HTTPException(422, {"problems": [f"That {what} is empty."]})
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(413, {"problems": [f"{what.capitalize()} too large (7 MB max)."]})
        return raw

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            ip = client_ip(request)
            now, q = time.monotonic(), hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= RATE_PER_MIN:
                return JSONResponse({"detail": "Too many checks in a minute. Try again shortly."}, 429)
            q.append(now)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        elif request.url.path in ("/", "/sw.js", "/manifest.webmanifest", "/offline.html", "/account.js"):
            resp.headers["Cache-Control"] = "no-cache"      # always revalidate, so page updates show on refresh
        return resp

    def vision_on() -> bool:
        return recognize is not None or bool(os.environ.get("GOOGLE_VISION_API_KEY"))

    @app.get("/api/health")
    def health():
        tp = limits.testing_phase(data_dir)
        # auto_capture: the Android app's one-tap unlock. TOTO_AUTO_CAPTURE=0 switches it off
        # for every app at once (the page then shows the manual steps), e.g. if Singapore Pools objects.
        return {"ok": True, "version": VERSION, "photo_reading": vision_on(),
                "auto_capture": os.environ.get("TOTO_AUTO_CAPTURE", "1").strip() != "0",
                "testing": tp.view() if tp else None}

    from .account_routes import add_account_routes
    add_account_routes(app, data_dir, client_ip, send_link)

    @app.get("/api/samples/tickets")
    def sample_tickets(kind: str = "toto"):
        """Testing phase only: sample tickets on draws the results database lacks."""
        from . import samples
        if not limits.testing_phase(data_dir):
            raise HTTPException(404, "samples are only available in a testing phase")
        if kind not in samples.KINDS:
            raise HTTPException(422, "kind must be toto, 4d or five")
        out = []
        for s in samples.make(kind, data_dir):
            out.append({**s, "ticket": _ticket_view(parse_ticket(s["text"]), data_dir)})
        return {"tickets": out}

    @app.post("/api/ticket")
    def ticket(body: TicketIn):
        d = parse_ticket(body.text)
        return _ticket_view(d, data_dir)

    @app.post("/api/check")
    def check(body: CheckIn):
        d = parse_ticket(body.text)
        if not d.ready:
            raise HTTPException(422, {"problems": d.problems(), "ticket": _ticket_view(d, data_dir)})
        typed = {r.draw_no: r for r in body.results}
        refs, sources, need = [], {}, []
        for n, printed_date in d.draws:
            if n in typed:
                r = typed[n]
                when = r.draw_date or printed_date
                if when is None:
                    raise HTTPException(422, {"problems": [f"Draw {n}: add the draw date."]})
                try:
                    m = (toto_result(n, when, r.numbers, group_amounts=r.amounts) if d.game == "toto"
                         else fourd_result(n, when, r.numbers))
                except EntryError as e:
                    raise HTTPException(422, {"problems": [f"Draw {n}: {e}"]}) from None
                refs.append(m.ref)
                sources[n] = "user"
                continue
            ref, src = _lookup(d.game, n, data_dir)
            if ref is None:
                need.append(n)
            else:
                refs.append(ref)
                sources[n] = src
        if need:
            return {"status": "need_results", "need": need, "ticket": _ticket_view(d, data_dir)}
        try:
            from .ticket import check_ticket
            result = check_ticket(d.entries, refs)
        except TicketError as e:
            raise HTTPException(422, {"problems": [str(e)]}) from None
        vals = set(sources.values())
        source = "user" if "user" in vals else "shared" if "shared" in vals else "official"
        rv = build_reveal(result, printed_price=d.printed_price, results_source=source)
        return {
            "status": "ok",
            "ticket": _ticket_view(d, data_dir),
            "draws": [_draw_view(ref, sources[ref.draw.draw_no]) for ref in refs],
            "boards": [_boards(d, ref) for ref in refs],
            "reveal": {
                "state": rv.state, "headline": rv.headline, "subline": rv.subline,
                "claim": rv.claim_text, "needs_review": rv.needs_review,
                "stake": {"state": rv.stake.state, "message": rv.stake.message},
                "attribution": rv.attribution,
                "lines": [vars(lv) for lv in rv.lines],
            },
            # Won / Stake / Net tiles. won and net are None while any group is
            # pending, so the page can never show a pending prize as S$0.
            "totals": {"won": result.total_won, "stake": result.total_stake, "net": result.net,
                       "pending_groups": list(result.pending_groups)},
        }

    @app.post("/api/results/screenshot")
    def screenshot(body: ScreenshotIn, request: Request):
        if not vision_on():
            raise HTTPException(503, {"problems": ["Reading screenshots isn't switched on yet. "
                                                   "Type the numbers instead."]})
        from .ocr import OcrError
        from .results_screen import ScreenError, merge, read_screen
        from . import ocr as _ocr
        imgs = [decode_image(b, "screenshot") for b in body.images]
        vision_allow(request, len(imgs), "screenshot")
        rec = recognize or _ocr.recognize
        try:
            ocrs = [rec(img) for img in imgs]
            parts = [read_screen(o.text, getattr(o, "words", None)) for o in ocrs]
            diag.check_reads(data_dir, ocrs, parts)
            read = merge(parts)
        except ScreenError as e:
            raise HTTPException(422, {"problems": [str(e)]}) from None
        except OcrError:
            raise HTTPException(502, {"problems": ["Couldn't read the screenshot right now. "
                                                   "Type the numbers instead."]}) from None
        shared.submit(read, shared.client_id(client_ip(request), data_dir), data_dir,
                      device=shared.device_label(request.headers.get("user-agent")))
        return _screen_view(read)

    @app.post("/api/results/screenshots")
    def screenshots_batch(body: BatchShotsIn, request: Request):
        """Screenshots for several draws in one go (multi-draw tickets). Each is
        read on its own and sorted to the ticket's draws by draw number or date;
        a prize-table screenshot joins the one before it."""
        if not vision_on():
            raise HTTPException(503, {"problems": ["Reading screenshots isn't switched on yet. "
                                                   "Type the numbers instead."]})
        from . import ocr
        from .results_screen import read_screen, sort_by_draw
        imgs = [decode_image(b, "screenshot") for b in body.images]
        vision_allow(request, len(imgs), "screenshot")
        rec = recognize or ocr.recognize
        try:
            ocrs = [rec(img) for img in imgs]
            reads = [read_screen(o.text, getattr(o, "words", None)) for o in ocrs]
        except ocr.OcrError:
            raise HTTPException(502, {"problems": ["Couldn't read the screenshots right now. "
                                                   "Type the numbers instead."]}) from None
        diag.check_reads(data_dir, ocrs, reads)
        batch = sort_by_draw(reads, [(d.draw_no, d.draw_date) for d in body.draws])
        if batch.draws or batch.others:
            who = shared.client_id(client_ip(request), data_dir)
            device = shared.device_label(request.headers.get("user-agent"))
            for read in [*batch.draws.values(), *batch.others.values()]:   # other draws help other people
                shared.submit(read, who, data_dir, device=device)
        if not batch.draws:
            raise HTTPException(422, {"problems": batch.notes or
                                      ["No TOTO or 4D result found in these screenshots."]})
        return {"draws": {str(n): _screen_view(r) for n, r in batch.draws.items()}, "notes": batch.notes}

    # ------------------------------------------------ crowd-sourcing this year's results (owner, 22 Oct 2026)
    @app.get("/api/results/wanted")
    def results_wanted(game: str = "toto"):
        """This year's draws that still need screenshots, with a direct link to
        each draw's official page. Draw numbers only: no results are listed."""
        if game not in ("toto", "4d"):
            raise HTTPException(422, "game must be toto or 4d")
        return results_db.wanted(game, data_dir)

    @app.post("/api/results/contribute")
    def contribute(body: ContributeIn, request: Request):
        """Screenshots of official results pages, with no ticket: each draw read
        is counted towards the shared results (two people must agree). Returns
        what each screenshot added; never anyone else's results."""
        if not vision_on():
            raise HTTPException(503, {"problems": ["Reading screenshots isn't switched on yet."]})
        from . import ocr
        from .results_screen import read_screen, sort_by_draw
        imgs = [decode_image(b, "screenshot") for b in body.images]
        vision_allow(request, len(imgs), "screenshot")
        rec = recognize or ocr.recognize
        try:
            ocrs = [rec(img) for img in imgs]
            reads = [read_screen(o.text, getattr(o, "words", None)) for o in ocrs]
        except ocr.OcrError:
            raise HTTPException(502, {"problems": ["Couldn't read the screenshots right now. Try again."]}) from None
        diag.check_reads(data_dir, ocrs, reads)
        batch = sort_by_draw(reads, [])
        notes = [n for n in batch.notes if "isn't on this ticket" not in n]
        who = shared.client_id(client_ip(request), data_dir)
        device = shared.device_label(request.headers.get("user-agent"))
        added = []
        for n, read in sorted(batch.others.items(), reverse=True):
            game = read.game
            if body.game and game and game != body.game:
                notes.append(f"Draw {n} is a {'4D' if game == '4d' else 'TOTO'} result, not {body.game.upper()}; "
                             "it was still added.")
            if not read.complete:
                added.append({"game": game, "draw_no": n, "added": False, "why": read.prompt()})
                continue
            if load_ref(game, n, data_dir) is not None:
                added.append({"game": game, "draw_no": n, "added": False, "why": "We already have the official result."})
                continue
            ok = shared.submit(read, who, data_dir, device=device)
            st = shared.status(game, n, data_dir)
            why = None if ok else ("Draw date couldn't be read." if read.draw_date is None else
                                   "Too old: we keep this year's and last year's draws.")
            added.append({"game": game, "draw_no": n, "added": ok, "state": st,
                          "draw_date": read.draw_date.isoformat() if read.draw_date else None, "why": why})
        if not added:
            raise HTTPException(422, {"problems": notes or ["No TOTO or 4D result found in these screenshots."]})
        return {"draws": added, "notes": notes}

    @app.post("/api/ticket/photo")
    def ticket_photo(body: PhotoIn, request: Request):
        """Photo of the ticket -> the ticket as text, read like a typed one (P3-02).
        The page shows it on the confirm screen; nothing is checked until the
        user says it looks right. The photo is not kept."""
        if not vision_on():
            raise HTTPException(503, {"problems": ["Reading photos isn't switched on yet. "
                                                   "Type the ticket instead."]})
        from . import ocr
        from .ticket_ocr import read_ocr
        raw = decode_image(body.image, "photo")
        vision_allow(request, 1)
        try:
            result = (recognize or ocr.recognize)(raw)
        except ocr.OcrError:
            raise HTTPException(502, {"problems": ["Couldn't read the photo right now. "
                                                   "Type the ticket instead."]}) from None
        r = read_ocr(result)
        return {"text": r.text, "notes": r.notes, "ticket": _ticket_view(r.draft, data_dir)}

    # ------------------------------------------------ owner view (owner.py): locked by data/owner.key
    owner_fails: dict[str, deque] = defaultdict(deque)

    def owner_only(request: Request) -> None:
        ip = client_ip(request)
        now, q = time.monotonic(), owner_fails[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= owner.OWNER_FAILS_PER_HOUR:
            raise HTTPException(429, "Too many wrong keys. Try again later.")
        ok = owner.check(request.headers.get("x-owner-key"), data_dir)
        if ok is None:
            raise HTTPException(404, "Owner view is off.")
        if not ok:
            q.append(now)
            raise HTTPException(401, "Wrong or missing owner key.")

    @app.get("/api/owner/results")
    def owner_results(request: Request, game: str = "toto", q: str = ""):
        """The compiled results database, newest first. q: a draw number or a
        date (YYYY-MM-DD, or DD/MM/YY as printed on tickets)."""
        owner_only(request)
        if game not in ("toto", "4d"):
            raise HTTPException(422, "game must be toto or 4d")
        draw_no, day = _owner_query(q)
        rows = results_db.find(game, data_dir, draw_no, day)
        all_rows = rows if (draw_no is None and day is None) else results_db.collect(game, data_dir)
        counts = {s: sum(r["state"] == s for r in all_rows) for s in ("official", "agreed", "waiting", "void")}
        years = {str(y): results_db.coverage(yr) for y, yr in results_db.by_year(game, all_rows).items()}
        return {"game": game, "counts": counts, "query": {"draw_no": draw_no, "date": day}, "draws": rows,
                "years": dict(sorted(years.items(), reverse=True))}

    @app.get("/api/owner/results.csv")
    def owner_results_csv(request: Request, game: str = "toto", year: Optional[int] = None):
        """All draws, or one year (every draw number in the year, gaps marked missing)."""
        owner_only(request)
        if game not in ("toto", "4d"):
            raise HTTPException(422, "game must be toto or 4d")
        results_db.compile(data_dir)
        name = f"{game}-{int(year)}.csv" if year else f"{game}.csv"     # int(): nothing else reaches the path
        f = data_dir / "results" / name
        if not f.is_file():
            raise HTTPException(404, f"No {game.upper()} draws on file for {year}.")
        return FileResponse(f, media_type="text/csv", filename=name if year else f"{game}-results.csv")

    @app.get("/owner")
    def owner_page():
        page = WEB / "owner.html"
        if not page.is_file():
            raise HTTPException(404, "web/owner.html missing")
        resp = FileResponse(page, media_type="text/html")
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        return resp

    @app.get("/")
    def index():
        page = WEB / "index.html"
        if not page.is_file():
            raise HTTPException(404, "web/index.html missing")
        return FileResponse(page, media_type="text/html")

    # P4-06 installable app: manifest, service worker, offline page, icons.
    # Fixed names only; nothing in a request ever becomes a file path.
    STATIC = {
        "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
        "/sw.js": ("sw.js", "application/javascript"),
        "/offline.html": ("offline.html", "text/html"),
        "/account.js": ("account.js", "application/javascript"),
        "/icons/icon-192.png": ("icons/icon-192.png", "image/png"),
        "/icons/icon-512.png": ("icons/icon-512.png", "image/png"),
        "/icons/maskable-512.png": ("icons/maskable-512.png", "image/png"),
        "/apple-touch-icon.png": ("icons/apple-touch-icon.png", "image/png"),
    }

    # Sample specimen tickets for the "Try sample tickets" button: fixed names, and
    # only served while a testing phase is on (tools\\testing-phase.ps1).
    for n in range(1, 6):
        def _sample(n=n):
            if not limits.testing_phase(data_dir):
                raise HTTPException(404, "samples are only available in a testing phase")
            f = WEB / "samples" / f"ticket-{n}.jpg"
            if not f.is_file():
                raise HTTPException(404, f"web/samples/ticket-{n}.jpg missing")
            return FileResponse(f, media_type="image/jpeg")
        app.add_api_route(f"/samples/ticket-{n}.jpg", _sample, methods=["GET"], include_in_schema=False)

    def _static_route(rel: str, media: str):
        def serve():
            f = WEB / rel
            if not f.is_file():
                raise HTTPException(404, f"web/{rel} missing")
            return FileResponse(f, media_type=media)
        return serve

    for path, (rel, media) in STATIC.items():
        app.add_api_route(path, _static_route(rel, media), methods=["GET"], include_in_schema=False)

    @app.post("/share-target", include_in_schema=False)
    def share_target():
        """Android Share -> the installed app. The service worker normally answers this
        itself (it keeps the pictures on the phone and redirects). If a share ever
        reaches the server, the pictures are NOT read or stored: it only sends the
        person back to the page with shared=0 so the page can say what to do."""
        return RedirectResponse("/?shared=0", status_code=303)

    return app


# ---------------------------------------------------------------- views

def _owner_query(q: str):
    """'4227' -> (4227, None); '2026-10-19' or '19/10/26' -> (None, '2026-10-19')."""
    import re
    q = (q or "").strip()
    if not q:
        return None, None
    if re.fullmatch(r"\d{3,5}", q):
        return int(q), None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", q) or None
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})", q)
        if not m:
            raise HTTPException(422, "Search by draw number (4227) or date (19/10/26 or 2026-10-19).")
        d, mo, y = map(int, m.groups())
        y = y + 2000 if y < 100 else y
    try:
        return None, date(y, mo, d).isoformat()
    except ValueError:
        raise HTTPException(422, "That date doesn't exist.") from None


def _lookup(game: str, n: int, data_dir: Path):
    """A draw's result and where it came from: the official capture first, then
    results two users' screenshots agreed on (P3-07), else (None, None)."""
    ref = load_ref(game, n, data_dir)
    if ref is not None:
        return ref, "captured"
    ref = shared.load_shared_ref(game, n, data_dir)
    if ref is not None:
        return ref, "shared"
    return None, None


def _ticket_view(d: TicketDraft, data_dir: Path) -> dict:
    entries = []
    for e, line in zip(d.entries, d.entry_lines):
        if isinstance(e, toto.TotoEntry):
            entries.append({"line": line, "label": e.label, "numbers": [f"{n:02d}" for n in e.numbers],
                            "stake": e.stake})
        else:
            label = {"ordinary": "Ordinary", "roll": "Roll", "system": "System", "ibet": "iBet"}[e.kind]
            entries.append({"line": line, "label": label, "numbers": [e.number], "big": e.big,
                            "small": e.small, "perms": e.perms, "stake": e.cost_per_draw})
    draws = []
    for n, when in d.draws:
        src = _lookup(d.game, n, data_dir)[1] if d.game else None
        draws.append({"draw_no": n, "date": when.isoformat() if when else None, "on_file": src is not None,
                      "source": src,
                      # "void": other users' screenshots disagree, so this draw needs the user's own
                      "shared": shared.status(d.game, n, data_dir) if d.game and src != "captured" else None,
                      "official_url": official_url(d.game, n) if d.game else None})
    return {
        "game": d.game, "ready": d.ready, "entries": entries, "draws": draws,
        "printed_price": d.printed_price, "stake": d.stake() if d.entries else 0,
        "quick_pick": d.quick_pick, "problems": d.problems() if not d.ready else [],
        "errors": [{"line": e.line_no, "message": e.message} for e in d.errors],
        "warnings": d.warnings,
    }


def _draw_view(ref: DrawRef, source: str) -> dict:
    d = ref.draw
    out = {"draw_no": d.draw_no, "date": ref.draw_date.isoformat(), "source": source,
           "official_url": official_url("toto" if isinstance(d, toto.TotoDraw) else "4d", d.draw_no),
           "attribution": ATTRIBUTION if source == "captured" else SHARED_ATTRIBUTION if source == "shared" else None,
           "claim_by": claim_by(ref.draw_date).isoformat()}
    if isinstance(d, toto.TotoDraw):
        out.update(game="toto", winning=[f"{n:02d}" for n in d.winning], additional=f"{d.additional:02d}")
    else:
        out.update(game="4d", first=d.first, second=d.second, third=d.third,
                   starter=list(d.starter), consolation=list(d.consolation))
    return out


def _screen_view(read) -> dict:
    """What the page needs from one draw's screenshots: numbers to put in the
    typed-results form, Group 1-4 amounts, and what (if anything) is missing."""
    out = {"complete": read.complete, "prompt": read.prompt(), "missing": read.missing,
           "game": read.game, "draw_no": read.draw_no,
           "draw_date": read.draw_date.isoformat() if read.draw_date else None, "notes": read.notes}
    if read.game == "toto":
        out["numbers"] = " ".join(map(str, read.winning)) + (f" + {read.additional}" if read.additional else "")
        out["amounts"] = {str(g): f"{a:,.0f}" for g, a in read.shares.items() if g <= 4}
    elif read.game == "4d":
        out["numbers"] = " ".join(x for x in [read.first, read.second, read.third,
                                               *read.starter, *read.consolation] if x)
    return out


def _boards(d: TicketDraft, ref: DrawRef) -> dict:
    """Per board: number marks for the ball animation (hit, add(itional) or none)
    and what the board won, for the "GROUP n · S$x" pill. won is None when a
    winning group has no published amount yet (pending, never S$0)."""
    rows = []
    for e in d.entries:
        if isinstance(e, toto.TotoEntry):
            w, a = set(ref.draw.winning), ref.draw.additional
            cells = [{"t": f"{n:02d}", "mark": "hit" if n in w else "add" if n == a else ""}
                     for n in e.numbers]
            r = toto.check_entry(e, ref.draw)
            groups = [{"group": g, "count": n, "amount": ref.draw.prize_for(g)}
                      for g, n in sorted(r.shares.items())]
            rows.append({"label": e.label, "cells": cells, "groups": groups,
                         "won": r.amount, "pending": bool(r.unpriced_groups)})
        else:
            r = fourd.check_entry(e, ref.draw)
            cats = sorted({h.category for h in r.hits},
                          key=["first", "second", "third", "starter", "consolation"].index)
            rows.append({"label": e.kind, "cells": [{"t": e.number, "mark": "hit" if r.hits else ""}],
                         "categories": cats, "won": float(r.amount), "pending": False})
    return {"draw_no": ref.draw.draw_no, "rows": rows}


app = create_app()


def main() -> None:
    import uvicorn
    host = os.environ.get("TOTO_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("TOTO_WEB_PORT", "8765"))
    uvicorn.run("lottery_checker.api:app", host=host, port=port, proxy_headers=True,
                forwarded_allow_ips="127.0.0.1", log_level="info", access_log=False)


if __name__ == "__main__":
    main()
