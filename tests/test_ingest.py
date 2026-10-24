import base64
import json
from pathlib import Path

import pytest

from lottery_checker import ingest
from lottery_checker.fourd import FourDEntry, check_entry as check_4d
from lottery_checker.parse import ParseError, parse_fourd, parse_toto
from lottery_checker.toto import TotoEntry, check_entry as check_toto

FIX = Path(__file__).parent / "fixtures"
TOTO_HTML = (FIX / "toto_4068.html").read_text(encoding="utf-8")
FOURD_HTML = (FIX / "fourd_5500.html").read_text(encoding="utf-8")


# ---------- Parsing the official layout ----------

def test_parse_toto_4068():
    (r,) = parse_toto(TOTO_HTML)
    d = r.draw
    assert d.draw_no == 4068 and r.draw_date.isoformat() == "2025-04-10"
    assert d.winning == (14, 26, 27, 30, 46, 48) and d.additional == 10
    assert r.group1_prize_pool == 1269186
    assert r.shares[1] == (None, None)                # no Group 1 winner
    assert r.shares[2] == (89066, 3) and r.shares[7] == (10, 82339)
    assert dict(d.group_prizes) == {2: 89066, 3: 2137, 4: 406, 5: 50, 6: 25, 7: 10}
    # P2-01: draw 4068 predates the 2026 rules, so it carries the 2022 version.
    assert d.rules.version == "toto-2022" and d.rules.verified is True


def test_parsed_toto_prices_pool_groups_in_matcher():
    (r,) = parse_toto(TOTO_HTML)
    # 4 winning + Additional -> Group 4, priced from the published $406
    res = check_toto(TotoEntry("ordinary", (14, 26, 27, 30, 10, 1)), r.draw)
    assert dict(res.shares) == {4: 1} and res.amount == 406


def test_parse_fourd_5500():
    (r,) = parse_fourd(FOURD_HTML)
    d = r.draw
    assert d.draw_no == 5500 and r.draw_date.isoformat() == "2026-06-24"
    assert (d.first, d.second, d.third) == ("5950", "2916", "1793")
    assert d.starter[0] == "0398" and len(d.starter) == 10   # leading zero kept
    assert d.consolation[-1] == "8838" and len(d.consolation) == 10
    assert d.rules.version == "4d-2024-12-30"                # P2-01


def test_parsed_fourd_in_matcher():
    (r,) = parse_fourd(FOURD_HTML)
    assert check_4d(FourDEntry("roll", "59R0", big=1), r.draw).amount == 2000   # 5950 first
    assert check_4d(FourDEntry("ordinary", "0398", big=1, small=1), r.draw).amount == 250


@pytest.mark.parametrize("html", ["<html><body>Maintenance</body></html>", TOTO_HTML.replace("win3", "winX")])
def test_layout_change_fails_loudly(html):
    with pytest.raises(ParseError):
        parse_toto(html)


def test_fourd_missing_number_fails_loudly():
    with pytest.raises(Exception):
        parse_fourd(FOURD_HTML.replace("<td>0733</td>", ""))


# ---------- Guardrails ----------

def test_kill_switch_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv("TOTO_INGEST_ENABLED", raising=False)
    calls = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", lambda *a, **k: calls.append(1))
    assert ingest.run("toto", tmp_path) == 0
    assert calls == []                                  # no request made


def test_requires_contact_for_user_agent(monkeypatch):
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.delenv("TOTO_CONTACT", raising=False)
    with pytest.raises(ingest.IngestDisabled):
        ingest.fetch("toto")


def test_user_agent_is_honest(monkeypatch):
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    ua = ingest.user_agent()
    assert ua.startswith("ZenQiTotoChecker/") and "ops@example.test" in ua and "Mozilla" not in ua


def test_deep_link_matches_official_pattern():
    url = ingest.official_url("toto", 4068)
    assert url.endswith("toto_results.aspx?sppl=RHJhd051bWJlcj00MDY4")
    assert base64.b64decode(url.split("sppl=")[1]).decode() == "DrawNumber=4068"


def test_store_writes_raw_and_attributed_json(tmp_path):
    (rec,) = ingest.store("toto", TOTO_HTML, tmp_path)
    saved = json.loads((tmp_path / "draws/toto/4068.json").read_text())
    assert saved == rec
    assert saved["source"] == "Singapore Pools" and "do not own" in saved["attribution"]
    assert saved["official_url"].endswith("RHJhd051bWJlcj00MDY4")
    assert (tmp_path / "raw/toto/4068.html").exists()
    # P2-01: every record says which rule set priced it, and whether that version is checked.
    assert saved["rules_version"] == "toto-2022" and saved["rules_verified"] is True


def test_retry_run_skips_request_when_draw_stored(monkeypatch, tmp_path):
    ingest.store("4d", FOURD_HTML, tmp_path)
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-06-24")
    calls = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", lambda *a, **k: calls.append(1))
    assert ingest.run("4d", tmp_path) == 0
    assert ingest.run("4d", tmp_path, draw_no=5500) == 0
    assert calls == []


def test_one_request_then_store(monkeypatch, tmp_path):
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-06-24")
    seen = []

    class Resp:
        """Mimics http.client.HTTPResponse closely enough for fetch()."""
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def __init__(self, url): self._url = url
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return FOURD_HTML.encode()
        def geturl(self): return self._url

    def fake_urlopen(req, timeout):
        seen.append((req.full_url, req.get_header("User-agent"), timeout))
        return Resp(req.full_url)

    monkeypatch.setattr(ingest.urllib.request, "urlopen", fake_urlopen)
    assert ingest.run("4d", tmp_path) == 0
    # 4D always asks for a draw by number (the plain page is script-filled, see ingest.py).
    assert len(seen) == 1 and seen[0][2] == 20
    assert seen[0][0] == ingest.official_url("4d", ingest.FOURD_SEED_DRAW)
    assert (tmp_path / "draws/4d/5500.json").exists()


def _fake_resp(body, seen):
    class Resp:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        def __init__(self, url): self._url = url
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return body.encode()
        def geturl(self): return self._url
    def fake_urlopen(req, timeout):
        seen.append(req.full_url)
        return Resp(req.full_url)
    return fake_urlopen


def test_fourd_requests_next_draw_after_latest_stored(monkeypatch, tmp_path):
    """Regression for 18 Oct 2026: the plain 4D page has no server-rendered results."""
    ingest.store("4d", FOURD_HTML, tmp_path)               # draw 5500 on file
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-06-27")
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(FOURD_HTML, seen))
    assert ingest.run("4d", tmp_path) == 0
    assert seen == [ingest.official_url("4d", 5501)]
    assert "?sppl=" in seen[0]


def test_fourd_unpublished_draw_is_noted_not_failed(monkeypatch, tmp_path, capsys):
    """Asking for a draw not yet out returns the previous draw; log it, exit 0, retry later."""
    ingest.store("4d", FOURD_HTML, tmp_path)
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-06-27")
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(FOURD_HTML, []))
    assert ingest.run("4d", tmp_path) == 0
    assert "draw 5501 not published yet; page returned 5500" in capsys.readouterr().out
    assert ingest.latest_stored("4d", tmp_path) == 5500


def test_toto_still_uses_plain_page(monkeypatch, tmp_path):
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-10-19")
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(TOTO_HTML, seen))
    ingest.run("toto", tmp_path)
    assert seen == [ingest.official_url("toto")]


def test_unparseable_page_is_kept_for_diagnosis(monkeypatch, tmp_path):
    """Regression for 18 Oct 2026: both live runs failed to parse and the
    responses were discarded, leaving nothing to diagnose."""
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2026-10-18")
    body = "<html><body>Please accept cookies to continue</body></html>"

    class Resp:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return body.encode()
        def geturl(self): return "https://www.singaporepools.com.sg/consent"

    monkeypatch.setattr(ingest.urllib.request, "urlopen", lambda req, timeout: Resp())
    assert ingest.run("4d", tmp_path) == 2                 # still fails loudly

    pages = list((tmp_path / "failed" / "4d").glob("*.html"))
    metas = list((tmp_path / "failed" / "4d").glob("*.json"))
    assert len(pages) == 1 and len(metas) == 1
    assert pages[0].read_text(encoding="utf-8") == body    # exactly what we received
    meta = json.loads(metas[0].read_text(encoding="utf-8"))
    assert meta["status"] == 200
    assert meta["final_url"] == "https://www.singaporepools.com.sg/consent"
    assert meta["final_url"] != meta["requested_url"]      # redirect is recorded
    assert "tables-wrap" in meta["error"]
    assert (tmp_path / "draws" / "4d").exists() is False   # nothing stored as a draw


# ---------- P2-07: Friday special draws (P0-04) ----------

def _stored_toto(tmp_path, draw_no, day):
    folder = tmp_path / "draws" / "toto"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{draw_no}.json").write_text(json.dumps({"draw_no": draw_no, "draw_date": day}))


def _on(monkeypatch, today):
    monkeypatch.setenv("TOTO_INGEST_ENABLED", "1")
    monkeypatch.setenv("TOTO_CONTACT", "ops@example.test")
    monkeypatch.setattr(ingest, "today_sgt", lambda: today)


def test_catch_up_makes_no_request_on_a_normal_week(monkeypatch, tmp_path, capsys):
    """Thursday's draw is on file, so Friday's catch-up run must not touch the site."""
    _stored_toto(tmp_path, 4228, "2026-10-22")              # Thu 22 Oct
    _on(monkeypatch, "2026-10-23")                          # Fri 23 Oct
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(TOTO_HTML, seen))
    assert ingest.run("toto", tmp_path, catch_up=True) == 0
    assert seen == []
    assert "no special draw expected" in capsys.readouterr().out


def test_catch_up_fetches_on_a_special_week(monkeypatch, tmp_path):
    """Hong Bao 2026: no Thu 26 Feb draw, the Friday draw (4160) replaced it.
    Latest on file is Monday's, so the Friday run makes exactly one request."""
    _stored_toto(tmp_path, 4159, "2026-02-23")              # Mon 23 Feb
    _on(monkeypatch, "2026-02-27")                          # Fri 27 Feb
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(TOTO_HTML, seen))
    assert ingest.run("toto", tmp_path, catch_up=True) == 0
    assert seen == [ingest.official_url("toto")]


def test_catch_up_retry_skips_once_friday_draw_stored(monkeypatch, tmp_path):
    _stored_toto(tmp_path, 4159, "2026-02-23")
    _stored_toto(tmp_path, 4160, "2026-02-27")              # stored by the 21:45 run
    _on(monkeypatch, "2026-02-27")
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(TOTO_HTML, seen))
    assert ingest.run("toto", tmp_path, catch_up=True) == 0
    assert seen == []


def test_catch_up_recovers_a_missed_thursday(monkeypatch, tmp_path):
    """Bonus: if both Thursday runs failed on a normal week, Friday picks the draw up."""
    _stored_toto(tmp_path, 4227, "2026-10-19")              # only Monday on file
    _on(monkeypatch, "2026-10-23")
    seen = []
    monkeypatch.setattr(ingest.urllib.request, "urlopen", _fake_resp(TOTO_HTML, seen))
    ingest.run("toto", tmp_path, catch_up=True)
    assert len(seen) == 1


def test_catch_up_flag_reaches_run(monkeypatch):
    got = {}
    monkeypatch.setattr(ingest, "run", lambda game, data, draw, catch_up=False: got.update(game=game, catch_up=catch_up) or 0)
    assert ingest.main(["toto", "--catch-up"]) == 0
    assert got == {"game": "toto", "catch_up": True}


def test_yesterday_crosses_month_and_leap_day(monkeypatch):
    monkeypatch.setattr(ingest, "today_sgt", lambda: "2028-03-01")
    assert ingest.yesterday_sgt() == "2028-02-29"


def test_special_draw_fixture_matches_known_numbering():
    """P0-04 samples: each special draw took the next number in sequence on a Friday."""
    data = json.loads((FIX / "special_draws_2026.json").read_text(encoding="utf-8"))
    from datetime import date
    nums = {d["special"]: d for d in data["draws"]}
    assert nums["Hong Bao Draw"]["draw_no"] == 4160
    for d in data["draws"]:
        assert date.fromisoformat(d["draw_date"]).weekday() == 4          # Friday
        assert sorted(d["shares"]) == [str(g) for g in range(1, 8)]
        assert (d["shares"]["5"]["amount"], d["shares"]["6"]["amount"], d["shares"]["7"]["amount"]) == (50, 25, 10)
