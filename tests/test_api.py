"""P4-02 web API, against the draws the capture really stored on Grayskull
(TOTO 4227, 4D 5550 and 5551), copied into a temp data folder."""
import base64
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web checker needs: py -3 -m pip install -r requirements.txt")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api, ingest  # noqa: E402
from lottery_checker.store import load_ref

FIX = Path(__file__).parent / "fixtures"
STORED = {
    "toto/4227.json": {"game": "toto", "draw_no": 4227, "draw_date": "2026-10-19",
                       "winning": [2, 15, 19, 20, 27, 30], "additional": 5,
                       "shares": {"1": {"amount": 2928913.0, "winners": 1}, "2": {"amount": 68513.0, "winners": 9},
                                  "3": {"amount": 1359.0, "winners": 183}, "4": {"amount": 200.0, "winners": 681},
                                  "5": {"amount": 50.0, "winners": 9069}, "6": {"amount": 25.0, "winners": 16199},
                                  "7": {"amount": 10.0, "winners": 159045}}},
    "4d/5551.json": {"game": "4d", "draw_no": 5551, "draw_date": "2026-10-21",
                     "first": "8455", "second": "1103", "third": "3344",
                     "starter": ["0273", "0436", "2089", "2837", "5006", "6491", "7394", "8072", "8468", "9574"],
                     "consolation": ["0030", "0854", "2005", "4062", "4623", "4890", "6736", "6804", "8934", "9363"]},
}


@pytest.fixture
def data(tmp_path):
    for rel, rec in STORED.items():
        p = tmp_path / "draws" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec))
    return tmp_path


@pytest.fixture
def client(data):
    return TestClient(api.create_app(data))


TOTO_TICKET = "TOTO\nORDINARY\nA. 02 15 19 20 27 05\nB. 02 15 19 40 41 05\nDRAW:\nMON 19/10/26 4227/26\nPRICE: $2.00"
FOURD_TICKET = "4D\nA 8455 BIG $1\nB 9363 BIG $1 SML $1\nDRAW: WED 21/10/26 5551/26\nPRICE: $3.00"


# ---------------- store ----------------

def test_store_loads_the_captured_record(data):
    ref = load_ref("toto", 4227, data)
    assert ref.draw.winning == (2, 15, 19, 20, 27, 30) and ref.draw.prize_for(2) == 68513.0
    assert ref.draw.rules.version == "toto-2026-03-02"
    assert load_ref("toto", 9999, data) is None


def test_store_treats_a_broken_file_as_not_on_file(data):
    (data / "draws" / "4d" / "5552.json").write_text("{not json")
    assert load_ref("4d", 5552, data) is None
    (data / "draws" / "4d" / "5553.json").write_text(json.dumps({**STORED["4d/5551.json"], "draw_no": 9}))
    assert load_ref("4d", 5553, data) is None                 # number inside must match the file


def test_store_reads_a_real_ingest_record(tmp_path):
    (rec,) = ingest.store("toto", (FIX / "toto_4068.html").read_text(encoding="utf-8"), tmp_path)
    ref = load_ref("toto", 4068, tmp_path)
    assert ref.draw.prize_for(1) is None                      # no Group 1 winner: stays unpriced
    assert ref.draw.prize_for(2) == 89066.0


# ---------------- endpoints ----------------

def test_health(client):
    r = client.get("/api/health").json()
    assert r["ok"] and r["photo_reading"] is False


def test_ticket_view_says_which_draws_are_on_file(client):
    r = client.post("/api/ticket", json={"text": TOTO_TICKET + "\nTHU 22/10/26 4228/26"}).json()
    assert r["game"] == "toto" and r["ready"]
    assert [(d["draw_no"], d["on_file"]) for d in r["draws"]] == [(4227, True), (4228, False)]
    assert r["draws"][1]["official_url"] == ingest.official_url("toto", 4228)
    assert r["entries"][0]["numbers"] == ["02", "05", "15", "19", "20", "27"]


def test_check_toto_against_captured_draw(client):
    r = client.post("/api/check", json={"text": TOTO_TICKET}).json()
    assert r["status"] == "ok"
    assert r["reveal"]["headline"] == "You won S$68,538"       # G2 68,513 + G6 25 (3 + Additional)
    assert r["reveal"]["stake"]["state"] == "match"
    assert "Singapore Pools" in r["reveal"]["attribution"]
    marks = [c["mark"] for c in r["boards"][0]["rows"][0]["cells"]]
    assert marks == ["hit", "add", "hit", "hit", "hit", "hit"]
    assert r["draws"][0]["source"] == "captured" and r["draws"][0]["claim_by"] == "2027-04-17"


def test_check_4d_against_tonights_draw(client):
    r = client.post("/api/check", json={"text": FOURD_TICKET}).json()
    assert r["reveal"]["headline"] == "You won S$2,060"         # 1st Big $2,000 + consolation Big $60
    rows = r["boards"][0]["rows"]
    assert rows[0]["categories"] == ["first"] and rows[1]["categories"] == ["consolation"]


def test_draw_not_on_file_asks_for_results(client):
    t = "TOTO\nA. 01 02 03 04 05 06\nDRAW:\nTHU 22/10/26 4228/26"
    r = client.post("/api/check", json={"text": t}).json()
    assert r["status"] == "need_results" and r["need"] == [4228]


def test_typed_results_fill_the_gap_and_change_attribution(client):
    t = "TOTO\nA. 01 02 03 04 05 06\nDRAW:\nTHU 22/10/26 4228/26"
    body = {"text": t, "results": [{"draw_no": 4228, "numbers": "1 2 3 40 41 42 + 4"}]}
    r = client.post("/api/check", json=body).json()
    assert r["reveal"]["headline"] == "You won S$25"            # 3 + Additional = Group 6
    assert r["draws"][0]["source"] == "user" and "entered by you" in r["reveal"]["attribution"]


def test_typed_results_need_a_date_when_the_ticket_has_none(client):
    body = {"text": "TOTO\nA. 01 02 03 04 05 06\ndraw 4228", "results": [{"draw_no": 4228, "numbers": "1 2 3 4 5 6 + 7"}]}
    r = client.post("/api/check", json=body)
    assert r.status_code == 422 and "add the draw date" in r.json()["detail"]["problems"][0]


def test_bad_typed_result_is_explained(client):
    t = "TOTO\nA. 01 02 03 04 05 06\nDRAW:\nTHU 22/10/26 4228/26"
    r = client.post("/api/check", json={"text": t, "results": [{"draw_no": 4228, "numbers": "1 2 3 4 5 50 + 6"}]})
    assert r.status_code == 422 and "1 to 49" in r.json()["detail"]["problems"][0]


def test_unready_ticket_returns_problems(client):
    r = client.post("/api/check", json={"text": "TOTO\nA. 01 02 03 04 05 06"})
    assert r.status_code == 422 and any("No draw found" in p for p in r.json()["detail"]["problems"])


def test_oversized_ticket_refused(client):
    assert client.post("/api/ticket", json={"text": "1 " * 3000}).status_code == 422


def test_screenshot_off_without_a_key(client):
    r = client.post("/api/results/screenshot", json={"images": [base64.b64encode(b"x").decode()]})
    assert r.status_code == 503 and "Type the numbers" in r.json()["detail"]["problems"][0]


def test_screenshot_reading_with_ocr(data):
    texts = iter([(FIX / "screens" / "fourd_5551_mobile_top.txt").read_text(encoding="utf-8"),
                  (FIX / "screens" / "fourd_5551_mobile_bottom.txt").read_text(encoding="utf-8")])

    class Fake:
        def __init__(self, t): self.text = t

    c = TestClient(api.create_app(data, recognize=lambda b: Fake(next(texts))))
    imgs = [base64.b64encode(b"img1").decode(), base64.b64encode(b"img2").decode()]
    r = c.post("/api/results/screenshot", json={"images": imgs}).json()
    assert r["complete"] and r["draw_no"] == 5551 and r["numbers"].startswith("8455 1103 3344 0273")


def test_rate_limit(data, monkeypatch):
    monkeypatch.setattr(api, "RATE_PER_MIN", 3)
    c = TestClient(api.create_app(data))
    codes = [c.get("/api/health").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_security_headers_and_no_cache(client):
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["cache-control"] == "no-store"


def test_no_endpoint_lists_results(client):
    """No public list of draws. The only list is the owner view, and that is
    locked: off without data/owner.key (no key file in this data folder)."""
    paths = {r.path for r in client.app.routes if not r.path.startswith("/api/owner/")}
    assert not any("draws" in p or "results" == p.strip("/").split("/")[-1] for p in paths)
    assert client.get("/api/draws/toto/4227").status_code == 404
    assert client.get("/api/owner/results").status_code == 404


# ---------------- board pills and totals (prototype merge, 21 Oct) ----------------

def test_board_groups_and_totals_toto(client):
    r = client.post("/api/check", json={"text": TOTO_TICKET}).json()
    a, b = r["boards"][0]["rows"]
    assert a["groups"] == [{"group": 2, "count": 1, "amount": 68513.0}] and a["won"] == 68513.0
    assert b["groups"] == [{"group": 6, "count": 1, "amount": 25.0}] and not b["pending"]
    assert r["totals"] == {"won": 68538.0, "stake": 2.0, "net": 68536.0, "pending_groups": []}


def test_system_board_lists_every_group(client):
    t = "TOTO\nSYSTEM 7\nA. 02 15 19 20 27 30 41\nDRAW:\nMON 19/10/26 4227/26"
    row = client.post("/api/check", json={"text": t}).json()["boards"][0]["rows"][0]
    assert [g["group"] for g in row["groups"]] == [1, 3]       # 6 of 7 = one G1 set, six G3 sets
    assert row["groups"][1]["count"] == 6


def test_pending_totals_are_none_not_zero(client):
    t = "TOTO\nA. 01 02 03 04 05 06\nDRAW:\nTHU 22/10/26 4228/26"
    body = {"text": t, "results": [{"draw_no": 4228, "numbers": "1 2 3 4 5 40 + 6"}]}   # G2, no amount typed
    r = client.post("/api/check", json={**body}).json()
    row = r["boards"][0]["rows"][0]
    assert row["pending"] and row["won"] is None and row["groups"][0]["amount"] is None
    assert r["totals"]["won"] is None and r["totals"]["net"] is None and r["totals"]["pending_groups"] == [2]


def test_fourd_categories_in_prize_order(client):
    t = "4D\nA 8455 BIG $1\nB 9363 BIG $1 SML $1\nDRAW: WED 21/10/26 5551/26"
    rows = client.post("/api/check", json={"text": t}).json()["boards"][0]["rows"]
    assert rows[0]["categories"] == ["first"] and rows[0]["won"] == 2000.0
    assert rows[1]["won"] == 60.0


def test_page_is_always_revalidated(client, monkeypatch, tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<!doctype html><title>t</title>")
    monkeypatch.setattr(api, "WEB", tmp_path)
    r = client.get("/")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"


# ---------------- installable app (P4-06) ----------------

@pytest.mark.parametrize("path,ctype", [
    ("/manifest.webmanifest", "application/manifest+json"),
    ("/sw.js", "application/javascript"),
    ("/offline.html", "text/html"),
    ("/icons/icon-192.png", "image/png"),
    ("/icons/icon-512.png", "image/png"),
    ("/icons/maskable-512.png", "image/png"),
    ("/apple-touch-icon.png", "image/png"),
])
def test_app_files_are_served(client, path, ctype):
    r = client.get(path)
    assert r.status_code == 200 and r.headers["content-type"].startswith(ctype)


def test_manifest_is_installable(client):
    m = client.get("/manifest.webmanifest").json()
    assert m["display"] == "standalone" and m["start_url"] == "/"
    sizes = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
    assert ("192x192", "any") in sizes and ("512x512", "any") in sizes and ("512x512", "maskable") in sizes


def test_service_worker_never_caches_the_api_and_is_revalidated(client):
    r = client.get("/sw.js")
    assert 'url.pathname.startsWith("/api/")) return;' in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_icon_names_are_fixed_no_path_from_request(client):
    assert client.get("/icons/../api.py").status_code == 404
    assert client.get("/icons/other.png").status_code == 404


# ---------------------------------------------------------------- ticket photo (P3-02)

from lottery_checker import ocr  # noqa: E402
from tests.test_ticket_ocr import T01  # noqa: E402

IMG = base64.b64encode(b"jpeg bytes").decode()


def _rows_result(rows):
    words = [ocr.Word(tok, (10 * j, 30 * i, 10 * j + 8, 30 * i + 20), 0.95)
             for i, row in enumerate(rows) for j, tok in enumerate(row.split())]
    return ocr.OcrResult("\n".join(rows), words)


def test_ticket_photo_off_without_a_key(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_VISION_API_KEY", raising=False)
    r = client.post("/api/ticket/photo", json={"image": IMG})
    assert r.status_code == 503 and "Type the ticket" in r.json()["detail"]["problems"][0]


def test_ticket_photo_reads_a_real_ticket(data):
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    r = c.post("/api/ticket/photo", json={"image": IMG}).json()
    assert r["text"].startswith("TOTO\nORDINARY\nA. 12 13 14 16 26 39 QP")
    t = r["ticket"]
    assert t["ready"] and [d["draw_no"] for d in t["draws"]] == [4216, 4217] and t["stake"] == 4


def test_ticket_photo_blank_is_not_a_crash(data):
    c = TestClient(api.create_app(data, recognize=lambda b: ocr.OcrResult("")))
    r = c.post("/api/ticket/photo", json={"image": IMG}).json()
    assert not r["ticket"]["ready"] and "Retake" in r["notes"][0]


def test_ticket_photo_vision_failure_says_type_instead(data):
    def boom(b):
        raise ocr.OcrError("HTTP 403")
    c = TestClient(api.create_app(data, recognize=boom))
    r = c.post("/api/ticket/photo", json={"image": IMG})
    assert r.status_code == 502 and "Type the ticket" in r.json()["detail"]["problems"][0]
    assert "403" not in r.text                          # no Vision internals to the public


def test_ticket_photo_bad_base64(data):
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    assert c.post("/api/ticket/photo", json={"image": "not base64!!"}).status_code == 422


def test_vision_caps_per_client_and_per_day(data, monkeypatch):
    monkeypatch.setattr(api, "VISION_PER_HOUR", 2)
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    codes = [c.post("/api/ticket/photo", json={"image": IMG}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    other = {"cf-connecting-ip": "203.0.113.9"}       # another client still gets its own allowance
    assert c.post("/api/ticket/photo", json={"image": IMG}, headers=other).status_code == 200

    monkeypatch.setattr(api, "VISION_PER_HOUR", 100)
    monkeypatch.setattr(api, "VISION_PER_DAY", 1)
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    assert c.post("/api/ticket/photo", json={"image": IMG}).status_code == 200
    r = c.post("/api/ticket/photo", json={"image": IMG})
    assert r.status_code == 429 and "today's limit" in r.json()["detail"]["problems"][0]


# ---------------------------------------------------------------- batch screenshots (multi-draw tickets)

from tests.test_results_screen import _BOTTOM, _TOP, _TOP_4228  # noqa: E402


class _Txt:
    def __init__(self, t): self.text = t


def _batch_client(data, texts):
    it = iter(texts)
    return TestClient(api.create_app(data, recognize=lambda b: _Txt(next(it))))


def _imgs(n):
    return [base64.b64encode(f"img{i}".encode()).decode() for i in range(n)]


def test_batch_screenshots_fill_each_draw(data):
    c = _batch_client(data, [_TOP_4228, _TOP, _BOTTOM])
    r = c.post("/api/results/screenshots", json={"images": _imgs(3), "draws": [
        {"draw_no": 4227, "draw_date": "2026-10-19"}, {"draw_no": 4228, "draw_date": "2026-10-22"}]}).json()
    assert r["draws"]["4228"]["numbers"] == "3 8 11 25 33 47 + 12"
    assert r["draws"]["4227"]["numbers"] == "2 15 19 20 27 30 + 5"
    assert r["draws"]["4227"]["amounts"]["4"] == "200" and r["notes"] == []


def test_batch_screenshots_nothing_usable_is_422(data):
    c = _batch_client(data, ["just some text"])
    r = c.post("/api/results/screenshots", json={"images": _imgs(1), "draws": [{"draw_no": 4227}]})
    assert r.status_code == 422


def test_captured_result_wins_over_shared(data):
    t = TestClient(api.create_app(data)).post("/api/ticket", json={"text": TOTO_TICKET}).json()
    assert t["draws"][0]["source"] == "captured"



def test_a_conflicting_screenshot_voids_the_shared_draw(data, monkeypatch):
    from datetime import date as _d
    import lottery_checker.shared as sh
    real_submit = sh.submit
    monkeypatch.setattr(sh, "submit", lambda read, who, dd, today=None, device="Unknown":
                        real_submit(read, who, dd, _d(2026, 10, 23), device=device))
    wrong = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    c = _batch_client(data, [_TOP_4228, _TOP_4228, wrong])
    body = {"images": _imgs(1), "draws": [{"draw_no": 4228, "draw_date": "2026-10-22"}]}
    ua = {"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Mobile Safari/604.1"}
    for ip in ("198.51.100.1", "198.51.100.2", "198.51.100.3"):
        c.post("/api/results/screenshots", json=body, headers={"cf-connecting-ip": ip, **ua})
    t = c.post("/api/ticket", json={"text": "TOTO\nA. 01 02 03 04 05 06\nDRAW:\nTHU 22/10/26 4228/26"}).json()
    assert not t["draws"][0]["on_file"] and t["draws"][0]["shared"] == "void"   # back to own screenshot
    rec = json.loads((data / "shared" / "toto" / "4228.json").read_text())
    devices = {e["device"] for c_ in rec["candidates"].values() for e in c_["entries"]}
    assert devices == {"iPhone · Safari"} and "198.51.100" not in json.dumps(rec)


# ---------------------------------------------------------------- limits (owner's rules, 22 Oct 11:01)

def test_official_screenshots_have_no_per_person_limit(data, monkeypatch):
    monkeypatch.setattr(api, "VISION_PER_HOUR", 2)
    c = _batch_client(data, [_TOP] * 60)
    body = {"images": _imgs(40), "draws": [{"draw_no": 4227}]}     # a whole sitting at once
    assert c.post("/api/results/screenshots", json=body).status_code == 200
    assert c.post("/api/results/screenshots", json={"images": _imgs(5), "draws": [{"draw_no": 4227}]}).status_code == 200


def test_screenshot_safety_net_is_site_wide(data, monkeypatch):
    from lottery_checker import limits
    monkeypatch.setattr(limits, "SCREENSHOTS_PER_DAY", 3)
    c = _batch_client(data, [_TOP] * 10)
    body = {"images": _imgs(4), "draws": [{"draw_no": 4227}]}
    r = c.post("/api/results/screenshots", json=body)
    assert r.status_code == 429 and "very busy" in r.json()["detail"]["problems"][0]
    monkeypatch.setattr(limits, "SCREENSHOTS_PER_DAY", 0)                # 0 = no safety net
    assert c.post("/api/results/screenshots", json=body).status_code == 200


def test_screenshots_do_not_use_up_ticket_photos(data, monkeypatch):
    monkeypatch.setattr(api, "VISION_PER_HOUR", 2)
    text = (FIX / "screens" / "toto_4227_mobile_top.txt").read_text(encoding="utf-8")

    class Fake:
        def __init__(self, t): self.text = t
    seq = iter([Fake(text)] * 5 + [_rows_result(T01)] * 2)
    c = TestClient(api.create_app(data, recognize=lambda b: next(seq)))
    assert c.post("/api/results/screenshots", json={"images": _imgs(5), "draws": [{"draw_no": 4227}]}).status_code == 200
    assert [c.post("/api/ticket/photo", json={"image": IMG}).status_code for _ in range(2)] == [200, 200]


def _testing(data, ends):
    (data / "testing_phase.json").write_text(json.dumps({"started": "2026-10-22T03:00:00Z", "ends": ends}))


def test_testing_phase_raises_ticket_photo_limits_until_it_ends(data, monkeypatch):
    monkeypatch.setattr(api, "VISION_PER_HOUR", 1)
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    _testing(data, "2999-01-01T00:00:00Z")
    assert [c.post("/api/ticket/photo", json={"image": IMG}).status_code for _ in range(3)] == [200, 200, 200]
    h = c.get("/api/health").json()["testing"]
    assert h["active"] and h["days_left"] > 1 and not h["last_day"]
    _testing(data, "2020-01-01T00:00:00Z")                                # ended: normal limits by themselves
    assert c.post("/api/ticket/photo", json={"image": IMG}).status_code == 429
    h = c.get("/api/health").json()["testing"]
    assert h["active"] is False                                          # still reported, so the owner is prompted
    (data / "testing_phase.json").unlink()                                # closed out
    assert c.get("/api/health").json()["testing"] is None


def test_broken_testing_file_never_raises_limits(data, monkeypatch):
    monkeypatch.setattr(api, "VISION_PER_HOUR", 1)
    (data / "testing_phase.json").write_text("{nope")
    c = TestClient(api.create_app(data, recognize=lambda b: _rows_result(T01)))
    assert [c.post("/api/ticket/photo", json={"image": IMG}).status_code for _ in range(2)] == [200, 429]


def test_testing_last_day_flag():
    from datetime import datetime, timedelta, timezone
    from lottery_checker.limits import TestingPhase
    now = datetime(2026, 10, 29, tzinfo=timezone.utc)
    assert TestingPhase(True, now + timedelta(hours=10)).view(now)["last_day"]
    assert not TestingPhase(True, now + timedelta(days=3)).view(now)["last_day"]


def test_screenshots_of_other_draws_are_kept_for_others(data, monkeypatch):
    from datetime import date as _d
    import lottery_checker.shared as sh
    real_submit = sh.submit
    monkeypatch.setattr(sh, "submit", lambda read, who, dd, today=None, device="Unknown":
                        real_submit(read, who, dd, _d(2026, 10, 23), device=device))
    c = _batch_client(data, [_TOP_4228, _TOP_4228])
    body = {"images": _imgs(1), "draws": [{"draw_no": 4231}]}          # ticket is for another draw
    for ip in ("198.51.100.1", "198.51.100.2"):
        r = c.post("/api/results/screenshots", json=body, headers={"cf-connecting-ip": ip})
        assert r.status_code == 422                                      # nothing for this ticket...
    assert sh.status("toto", 4228, data) == "agreed"                     # ...but 4228 now helps others

