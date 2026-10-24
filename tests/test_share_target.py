"""Android Share target, phone Paste button, and the failed-read diagnostics
(owner, 22 Oct 2026, after draw 4145 was refused with "Still missing:
winning numbers" and left nothing in the log to explain why)."""
import base64
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api, diag, ocr  # noqa: E402
from lottery_checker.results_screen import read_screen  # noqa: E402
from tests.test_api import data  # noqa: E402,F401  (fixture)
from tests.test_results_screen import _BOTTOM, _TOP  # noqa: E402

WEB = Path(__file__).resolve().parent.parent / "web"

# the 4145 page as Vision might return it with the lone "5" dropped from the row
_5_DROPPED = _TOP.replace("Mon, 19 Oct 2026 Draw No. 4227", "Mon, 05 Jan 2026 Draw No. 4145").replace(
    "2 15 19 20 27 30", "15 19 20 27 30").replace("Mon, 19 Oct 2026\nMon,", "Mon, 05 Jan 2026\nMon,")


# ---------------------------------------------------------------- the install files

def test_manifest_declares_a_share_target_for_pictures():
    m = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    st = m["share_target"]
    assert (st["action"], st["method"], st["enctype"]) == ("/share-target", "POST", "multipart/form-data")
    f = st["params"]["files"][0]
    assert f["name"] == "screenshots" and "image/png" in f["accept"] and "image/jpeg" in f["accept"]
    assert st["action"].startswith(m["scope"])                  # a share target must sit inside the app's scope


def test_service_worker_handles_the_share_and_keeps_the_pictures_cache():
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    assert '"/share-target"' in sw and 'formData()' in sw and "Response.redirect" in sw
    assert "k !== SHARED" in sw                                 # an update must not wipe a share in flight
    assert sw.index('"/share-target"') < sw.index('e.request.method !== "GET"')   # before the GET-only guard


def test_a_share_that_reaches_the_server_reads_and_stores_nothing(data):  # noqa: F811
    c = TestClient(api.create_app(data))
    r = c.post("/share-target", files={"screenshots": ("a.png", b"not read", "image/png")}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/?shared=0"
    assert not (data / "failed").exists()
    assert not list((data / "shared").rglob("*.json"))


# ---------------------------------------------------------------- phones have no Paste button

def test_paste_button_is_for_computers_only():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    assert "const CAN_PASTE = !PHONE && " in page
    assert page.index("const PHONE =") < page.index("const CAN_PASTE =")


# ---------------------------------------------------------------- what the user is told

def test_partial_numbers_row_says_what_was_read_and_asks_for_a_new_shot_not_a_scroll():
    r = read_screen(_5_DROPPED)
    assert r.draw_no == 4145 and r.winning == [15, 19, 20, 27, 30]
    p = r.prompt()
    assert "only 5 of 6 read: 15 19 20 27 30" in p
    assert "fresh screenshot of the top" in p and "Scroll down" not in p


def test_missing_prize_table_still_says_scroll_down():
    r = read_screen("Mon, 05 Jan 2026 Draw No. 4145\nWinning Numbers\n5 20 35 39 40 49\nAdditional Number\n27")
    assert r.top_missing == [] and not r.top_incomplete
    assert read_screen(_TOP).prompt().startswith("Read the draw")          # complete: unchanged wording


def test_partial_read_survives_a_merge():
    from lottery_checker.results_screen import merge
    m = merge([read_screen(_5_DROPPED)])
    assert m.winning_partial == [15, 19, 20, 27, 30] and "only 5 of 6" in m.prompt()


# ---------------------------------------------------------------- failed reads leave a trace

class _Txt:
    def __init__(self, t): self.text, self.words = t, [ocr.Word("15", (1, 2, 3, 4), 0.9)]


def _imgs(n):
    return [base64.b64encode(f"img{i}".encode()).decode() for i in range(n)]


def test_a_short_top_of_page_read_saves_its_raw_ocr(data):  # noqa: F811
    c = TestClient(api.create_app(data, recognize=lambda b: _Txt(_5_DROPPED)))
    c.post("/api/results/contribute", json={"images": _imgs(1), "game": "toto"})
    files = list((data / "failed" / "screens").glob("*.json"))
    assert len(files) == 1
    j = json.loads(files[0].read_text(encoding="utf-8"))
    assert (j["game"], j["draw_no"], j["missing"], j["winning_read"]) == ("toto", 4145, ["winning numbers"], [15, 19, 20, 27, 30])
    assert "Winning Numbers" in j["text"] and j["words"] == [["15", 1, 2, 3, 4]]


def test_a_bottom_of_page_shot_is_not_a_failure(data):  # noqa: F811
    c = TestClient(api.create_app(data, recognize=lambda b: _Txt(_BOTTOM)))
    c.post("/api/results/contribute", json={"images": _imgs(1)})
    assert not (data / "failed").exists()


def test_failure_files_are_capped_and_diagnostics_never_raise(data, monkeypatch):  # noqa: F811
    monkeypatch.setattr(diag, "KEEP", 3)
    r = read_screen(_5_DROPPED)
    for _ in range(6):
        diag.save_failed(data, _Txt(_5_DROPPED), r)
    assert len(list((data / "failed" / "screens").glob("*.json"))) == 3
    diag.save_failed(data / "no" / "\0bad", _Txt("x"), r)                  # unwritable path: swallowed


# ---------------------------------------------------------------- the learning record (22 Oct 2026)

def test_each_short_read_is_appended_to_the_learning_ledger(data):  # noqa: F811
    c = TestClient(api.create_app(data, recognize=lambda b: _Txt(_5_DROPPED)))
    c.post("/api/results/contribute", json={"images": _imgs(2), "game": "toto"})
    lines = diag.ledger_path(data).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2                                      # appended, never overwritten
    e = json.loads(lines[0])
    assert (e["game"], e["draw_no"], e["missing"], e["source"]) == ("toto", 4145, ["winning numbers"], "screenshot")
    assert e["read"] == {"winning": [15, 19, 20, 27, 30], "additional": 5} and "Winning Numbers" in e["text"]


def test_ledger_survives_the_failure_files_being_pruned(data, monkeypatch):  # noqa: F811
    monkeypatch.setattr(diag, "KEEP", 1)
    r = read_screen(_5_DROPPED)
    for _ in range(4):
        diag.save_failed(data, _Txt(_5_DROPPED), r)
    assert len(list((data / "failed" / "screens").glob("*.json"))) == 1
    assert len(diag.ledger_path(data).read_text(encoding="utf-8").splitlines()) == 4


def test_compare_names_the_kind_of_mistake():
    t = [5, 20, 35, 39, 40, 49]
    assert diag.compare_numbers([20, 35, 39, 40, 49], t) == {"kind": "dropped", "missing": [5]}
    assert diag.compare_numbers(t, t) == {"kind": "ok"}
    assert diag.compare_numbers(t + [7], t) == {"kind": "extra", "extra": [7]}
    assert diag.compare_numbers([6, 20, 35, 39, 40, 49], t) == {"kind": "wrong", "missing": [5], "extra": [6]}


def test_review_lines_a_logged_read_up_with_the_official_result(data):  # noqa: F811
    r = read_screen(_5_DROPPED)                                  # logged as a short read of draw 4145
    diag.save_failed(data, _Txt(_5_DROPPED), r)
    row = diag.review(data)[0]
    assert row["kind"] == "no truth yet" and row["truth"] is None
    (data / "draws" / "toto").mkdir(parents=True, exist_ok=True)
    (data / "draws" / "toto" / "4145.json").write_text(json.dumps({
        "game": "toto", "draw_no": 4145, "draw_date": "2026-01-05", "winning": [5, 15, 19, 20, 27, 30],
        "additional": 12, "shares": {}}), encoding="utf-8")
    row = diag.review(data)[0]
    assert (row["kind"], row["detail"], row["truth_source"]) == ("dropped", "missing [5] additional read 5 true 12", "official")
    csv_path = diag.write_review_csv(data)
    assert "dropped" in csv_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- one person's screenshot is in the database (22 Oct 2026)

def test_a_waiting_draw_is_compiled_with_its_numbers_and_amounts(data):  # noqa: F811
    from datetime import date
    from lottery_checker import results_db, shared
    from tests.test_results_screen import _TOP_4228
    from tests.test_shared import _read
    shared.submit(_read(_TOP_4228), "a", data, date(2026, 10, 23))
    row = results_db.find("toto", data, 4228)[0]
    assert row["state"] == "waiting" and row["winning"] and row["additional"] == 12
    assert row["shares"]["1"] and row["shares_confirmed"] is False            # the one screenshot's amounts, marked unconfirmed
    comp = results_db.compile(data)["toto"]
    assert comp["by_draw"]["4228"]["state"] == "waiting" and comp["counts"]["waiting"] == 1
    csv_text = (data / "results" / "toto-2026.csv").read_text(encoding="utf-8-sig")
    assert "one person's screenshot so far, not yet confirmed" in csv_text
    # still never used to check a ticket until a second person agrees
    assert shared.load_shared_ref("toto", 4228, data) is None


def test_wanted_counts_ready_waiting_and_missing_apart(data):  # noqa: F811
    from datetime import date, datetime, timedelta, timezone
    from lottery_checker import results_db, shared
    from tests.test_results_screen import _TOP_4228
    from tests.test_shared import _read
    shared.submit(_read(_TOP_4228), "a", data, date(2026, 10, 23))
    w = results_db.wanted("toto", data, datetime(2026, 10, 23, 12, 0, tzinfo=timezone(timedelta(hours=8))))
    assert (w["usable"], w["waiting"], w["on_file"]) == (1, 1, 2)
    assert w["usable"] + w["waiting"] + w["missing"] == w["draws"]


def test_help_card_shows_ready_waiting_and_to_go():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    assert "${w.usable} ready · ${waiting} waiting · ${none} to go" in page
    assert "draws ready`" not in page                                           # the old "1 of 84 draws ready"
