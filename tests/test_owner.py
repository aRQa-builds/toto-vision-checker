"""Owner view of the results database: /owner and /api/owner/*, locked by data/owner.key."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api, owner, shared  # noqa: E402
from tests.test_api import STORED, data  # noqa: E402,F401  (fixture)
from tests.test_results_screen import _TOP_4228  # noqa: E402
from tests.test_shared import TODAY, _read  # noqa: E402


@pytest.fixture
def keyed(data):  # noqa: F811
    k = owner.make_key(data)
    return TestClient(api.create_app(data)), k, data


def test_off_without_a_key_file(data):  # noqa: F811
    c = TestClient(api.create_app(data))
    assert c.get("/api/owner/results", headers={"X-Owner-Key": "x" * 64}).status_code == 404


def test_wrong_or_missing_key_refused(keyed):
    c, k, _ = keyed
    assert c.get("/api/owner/results").status_code == 401
    assert c.get("/api/owner/results", headers={"X-Owner-Key": "0" * 64}).status_code == 401
    assert c.get(f"/api/owner/results?key={k}").status_code == 401     # never from the URL


def test_too_many_wrong_keys_slowed_down(keyed):
    c, k, _ = keyed
    for _ in range(owner.OWNER_FAILS_PER_HOUR):
        c.get("/api/owner/results", headers={"X-Owner-Key": "bad"})
    assert c.get("/api/owner/results", headers={"X-Owner-Key": k}).status_code == 429


def test_lists_both_games_and_finds_by_draw_or_date(keyed):
    c, k, data_dir = keyed
    h = {"X-Owner-Key": k}
    shared.submit(_read(_TOP_4228), "a", data_dir, TODAY, device="Android · Chrome")
    j = c.get("/api/owner/results?game=toto", headers=h).json()
    assert [r["draw_no"] for r in j["draws"]] == [4228, 4227]
    assert j["counts"] == {"official": 1, "agreed": 0, "waiting": 1, "void": 0}
    assert c.get("/api/owner/results?game=toto&q=4227", headers=h).json()["draws"][0]["state"] == "official"
    for q in ("19/10/26", "2026-10-19", "19.10.2026"):
        assert [r["draw_no"] for r in c.get(f"/api/owner/results?game=toto&q={q}", headers=h).json()["draws"]] == [4227]
    j = c.get("/api/owner/results?game=4d&q=21/10/26", headers=h).json()
    assert j["draws"][0]["first"] == "8455" and j["counts"]["official"] == 1
    assert c.get("/api/owner/results?game=toto&q=31/02/26", headers=h).status_code == 422
    assert c.get("/api/owner/results?game=x", headers=h).status_code == 422


def test_csv_download(keyed):
    c, k, _ = keyed
    r = c.get("/api/owner/results.csv?game=toto", headers={"X-Owner-Key": k})
    assert r.status_code == 200 and "4227,2026-10-19,official" in r.text


def test_page_is_served_unindexed_and_uncached(keyed):
    c, _, _ = keyed
    r = c.get("/owner")
    assert r.status_code == 200 and "Results database" in r.text
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]


def test_cli_prints_links_with_the_key_after_the_hash(tmp_path, capsys):
    owner.main(["--data", str(tmp_path)])
    out = capsys.readouterr().out
    k = owner.owner_key(tmp_path)
    assert f"https://toto.zenqi.cc/owner#key={k}" in out and f"http://127.0.0.1:8765/owner#key={k}" in out
    owner.main(["--data", str(tmp_path), "--new"])
    assert owner.owner_key(tmp_path) != k


def test_year_csv_and_coverage(keyed):
    c, k, _ = keyed
    h = {"X-Owner-Key": k}
    j = c.get("/api/owner/results?game=4d", headers=h).json()
    assert j["years"]["2026"]["from"] == 5426 and j["years"]["2026"]["missing"] == 125
    r = c.get("/api/owner/results.csv?game=4d&year=2026", headers=h)
    assert r.status_code == 200 and r.text.count("\n") == 127 and "5426,,missing" in r.text
    assert c.get("/api/owner/results.csv?game=4d&year=2019", headers=h).status_code == 404
    assert c.get("/api/owner/results.csv?game=4d&year=../x", headers=h).status_code == 422
