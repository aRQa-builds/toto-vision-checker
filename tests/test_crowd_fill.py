"""Building the year's results from crowd screenshots (owner, 22 Oct 2026): no
pulling from the official site. Missing draws get a direct link to their official
page; screenshots added without a ticket count once two people agree."""
import base64
from datetime import date, datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api, results_db, shared  # noqa: E402
from tests.test_api import STORED, data  # noqa: E402,F401  (fixture)
from tests.test_results_screen import _BOTTOM, _TOP, _TOP_4228  # noqa: E402
from tests.test_shared import _read  # noqa: E402

SGT = timezone(timedelta(hours=8))


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=SGT)


# ---------------------------------------------------------------- which draws should be out by now

def test_latest_drawn_follows_the_draw_days():
    assert results_db.latest_drawn("toto", at("2026-10-22 15:00")) == 4227     # tonight's 4228 not up yet
    assert results_db.latest_drawn("toto", at("2026-10-22 22:30")) == 4228
    assert results_db.latest_drawn("toto", at("2026-10-26 23:00")) == 4229     # Mon
    assert results_db.latest_drawn("4d", at("2026-10-24 22:00")) == 5552       # Sat
    assert results_db.latest_drawn("4d", at("2026-10-25 22:00")) == 5553       # Sun


def test_first_draws_of_2026_match_the_owners_numbers():
    assert results_db.latest_drawn("toto", at("2026-01-01 23:00")) == 4144     # Thu 1 Jan
    assert results_db.latest_drawn("4d", at("2026-01-03 23:00")) == 5426       # Sat 3 Jan


# ---------------------------------------------------------------- wanted list

def test_wanted_lists_missing_and_waiting_draws_with_links(data):  # noqa: F811
    shared.submit(_read(_TOP_4228), "a", data, date(2026, 10, 23))
    w = results_db.wanted("toto", data, at("2026-10-23 12:00"))
    assert (w["from"], w["to"], w["draws"], w["usable"]) == (4144, 4228, 85, 1)
    states = {x["draw_no"]: x["state"] for x in w["wanted"]}
    assert states[4228] == "waiting" and states[4144] == "missing" and 4227 not in states
    assert "toto_results.aspx?sppl=" in w["wanted"][0]["official_url"]
    assert w["wanted"][0]["draw_no"] == 4228                                    # newest first


def test_void_draws_are_not_asked_for(data):  # noqa: F811
    other = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    shared.submit(_read(_TOP_4228), "a", data, date(2026, 10, 23))
    shared.submit(_read(other), "b", data, date(2026, 10, 23))
    assert 4228 not in {x["draw_no"] for x in results_db.wanted("toto", data, at("2026-10-23 12:00"))["wanted"]}


def test_wanted_endpoint_lists_numbers_never_results(data):  # noqa: F811
    j = TestClient(api.create_app(data)).get("/api/results/wanted?game=4d").json()
    assert j["from"] == 5426 and all(set(x) == {"draw_no", "state", "official_url"} for x in j["wanted"])


# ---------------------------------------------------------------- the whole year is kept

def test_crowd_reads_kept_for_this_and_last_year():
    early = _TOP_4228.replace("Draw No. 4228", "Draw No. 4150").replace("Thu, 22 Oct 2026", "Thu, 22 Jan 2026")
    r = _read(early)
    assert r.draw_no == 4150 and r.draw_date == date(2026, 1, 22)
    assert shared.submit(r, "a", _tmp(), date(2026, 10, 22))                    # was refused at 180 days
    old = _TOP_4228.replace("Thu, 22 Oct 2026", "Thu, 24 Oct 2024")
    assert not shared.submit(_read(old), "a", _tmp(), date(2026, 10, 22))


def _tmp():
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp())


# ---------------------------------------------------------------- contribute without a ticket

class _Txt:
    def __init__(self, t): self.text = t


def _client(data_dir, texts, ip="1.1.1.1"):  # noqa: F811
    it = iter(texts)
    c = TestClient(api.create_app(data_dir, recognize=lambda b: _Txt(next(it))))
    c.headers["cf-connecting-ip"] = ip
    return c


def _imgs(n):
    return [base64.b64encode(f"img{i}".encode()).decode() for i in range(n)]


def test_contribute_two_people_make_a_draw_ready(data):  # noqa: F811
    r = _client(data, [_TOP_4228]).post("/api/results/contribute", json={"images": _imgs(1), "game": "toto"}).json()
    assert r["draws"] == [{"game": "toto", "draw_no": 4228, "added": True, "state": "waiting",
                           "draw_date": "2026-10-22", "why": None}]
    r = _client(data, [_TOP_4228], ip="2.2.2.2").post("/api/results/contribute", json={"images": _imgs(1)}).json()
    assert r["draws"][0]["state"] == "agreed"
    assert shared.load_shared_ref("toto", 4228, data).draw.additional == 12


def test_contribute_skips_draws_we_have_officially(data):  # noqa: F811
    r = _client(data, [_TOP, _BOTTOM]).post("/api/results/contribute", json={"images": _imgs(2)}).json()
    assert r["draws"] == [{"game": "toto", "draw_no": 4227, "added": False, "why": "We already have the official result."}]


def test_contribute_nothing_readable_is_422(data):  # noqa: F811
    r = _client(data, ["hello"]).post("/api/results/contribute", json={"images": _imgs(1)})
    assert r.status_code == 422


def test_contribute_needs_photo_reading(data):  # noqa: F811
    assert TestClient(api.create_app(data)).post("/api/results/contribute",
                                                 json={"images": _imgs(1)}).status_code == 503
