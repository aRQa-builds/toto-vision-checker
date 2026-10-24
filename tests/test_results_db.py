"""Results database: official captures + crowd screenshot reads, by draw and by date."""
import csv
import json
import shutil
from pathlib import Path

from lottery_checker import results_db, shared
from tests.test_shared import TODAY, _read
from tests.test_results_screen import _TOP_4228

REAL = Path(__file__).resolve().parent.parent / "data"


def _official(tmp_path, game, n):
    src = REAL / "draws" / game / f"{n}.json"
    if src.is_file():
        dst = tmp_path / "draws" / game / f"{n}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        return True
    return False


def _toto_4227(tmp_path):
    rec = {"game": "toto", "draw_no": 4227, "draw_date": "2026-10-19", "captured_at": "2026-10-19T13:45:01+00:00",
           "winning": [2, 15, 19, 20, 27, 30], "additional": 5,
           "shares": {str(g): {"amount": a, "winners": 1} for g, a in
                      {1: 2928913.0, 2: 68513.0, 3: 1400.0, 4: 412.0, 5: 50.0, 6: 25.0, 7: 10.0}.items()}}
    p = tmp_path / "draws" / "toto" / "4227.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec), encoding="utf-8")


def test_empty_database_compiles(tmp_path):
    comp = results_db.compile(tmp_path)
    assert comp["toto"]["by_draw"] == {} and (tmp_path / "results" / "4d.csv").is_file()


def test_official_and_crowd_by_draw_and_date(tmp_path):
    _toto_4227(tmp_path)
    shared.submit(_read(_TOP_4228), "a", tmp_path, TODAY, device="Android · Chrome")
    shared.submit(_read(_TOP_4228), "b", tmp_path, TODAY, device="iPhone · Safari")
    comp = json.loads((tmp_path / "results" / "toto.json").read_text(encoding="utf-8"))   # written by the hook
    assert comp["counts"] == {"official": 1, "agreed": 1, "waiting": 0, "void": 0}
    assert comp["by_date"] == {"2026-10-22": [4228], "2026-10-19": [4227]}
    crowd = comp["by_draw"]["4228"]
    assert crowd["state"] == "agreed" and crowd["winning"] == [3, 8, 11, 25, 33, 47]
    assert crowd["crowd"]["people"] == 2 and crowd["crowd"]["devices"] == {"Android · Chrome": 1, "iPhone · Safari": 1}
    assert results_db.find("toto", tmp_path, day="2026-10-19")[0]["draw_no"] == 4227
    assert results_db.find("toto", tmp_path, draw_no=4228)[0]["source"] == "users' screenshots"


def test_waiting_and_void_are_kept_for_the_owner(tmp_path):
    other = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    shared.submit(_read(_TOP_4228), "a", tmp_path, TODAY)
    assert results_db.find("toto", tmp_path, 4228)[0]["state"] == "waiting"
    shared.submit(_read(other), "b", tmp_path, TODAY)
    r = results_db.find("toto", tmp_path, 4228)[0]
    assert r["state"] == "void" and "winning" not in r
    assert sorted(x["people"] for x in r["crowd"]["readings"]) == [1, 1]
    assert r["crowd"]["void_why"] == "screenshots read different numbers"


def test_csv_opens_in_excel(tmp_path):
    _toto_4227(tmp_path)
    results_db.compile(tmp_path)
    with (tmp_path / "results" / "toto.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["draw_no"] == "4227" and rows[0]["numbers"] == "02 15 19 20 27 30 + 05"
    assert rows[0]["group1"] == "2928913.0" and rows[0]["state"] == "official"


def test_4d_official_capture(tmp_path):
    if not _official(tmp_path, "4d", 5551):
        rec = {"game": "4d", "draw_no": 5551, "draw_date": "2026-10-21", "first": "8455", "second": "1111",
               "third": "2222", "starter": ["0001"] * 10, "consolation": ["0002"] * 10}
        p = tmp_path / "draws" / "4d" / "5551.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec), encoding="utf-8")
    r = results_db.find("4d", tmp_path, day="2026-10-21")
    assert r and r[0]["draw_no"] == 5551 and r[0]["state"] == "official"


def test_cli(tmp_path, capsys):
    _toto_4227(tmp_path)
    assert results_db.main(["toto", "--draw", "4227", "--data", str(tmp_path)]) == 0
    assert "4227  2026-10-19  official 02 15 19 20 27 30 + 05" in capsys.readouterr().out


# ---------------------------------------------------------------- one CSV per year (owner, 22 Oct)

def test_year_csv_lists_every_draw_from_the_years_first(tmp_path):
    _toto_4227(tmp_path)
    comp = results_db.compile(tmp_path)
    cv = comp["toto"]["years"]["2026"]
    assert (cv["from"], cv["to"], cv["draws"], cv["usable"], cv["missing"]) == (4144, 4227, 84, 1, 83)
    assert cv["missing_draws"][:2] == [4144, 4145] and 4227 not in cv["missing_draws"]
    with (tmp_path / "results" / "toto-2026.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 84 and rows[0]["draw_no"] == "4227" and rows[-1]["draw_no"] == "4144"
    assert rows[-1]["state"] == "missing" and rows[-1]["source"] == "not on file"


def test_crowd_draws_count_in_their_year(tmp_path):
    _toto_4227(tmp_path)
    shared.submit(_read(_TOP_4228), "a", tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), "b", tmp_path, TODAY)
    cv = results_db.compile(tmp_path)["toto"]["years"]["2026"]
    assert cv["to"] == 4228 and cv["usable"] == 2


def test_next_year_gets_its_own_file(tmp_path, monkeypatch):
    monkeypatch.setitem(results_db.YEAR_FIRST, "toto", {2026: 4144, 2027: 4250})
    _toto_4227(tmp_path)
    rec = json.loads((tmp_path / "draws" / "toto" / "4227.json").read_text())
    rec.update(draw_no=4251, draw_date="2027-01-05")
    (tmp_path / "draws" / "toto" / "4251.json").write_text(json.dumps(rec))
    years = results_db.compile(tmp_path)["toto"]["years"]
    assert years["2026"]["to"] == 4227 and (years["2027"]["from"], years["2027"]["to"]) == (4250, 4251)
    assert (tmp_path / "results" / "toto-2027.csv").is_file()


def test_4d_year_starts_at_5426(tmp_path):
    test_4d_official_capture(tmp_path)
    cv = results_db.compile(tmp_path)["4d"]["years"]["2026"]
    assert cv["from"] == 5426 and cv["to"] == 5551 and cv["draws"] == 126
