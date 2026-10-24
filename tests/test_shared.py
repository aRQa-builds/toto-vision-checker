"""P3-07: results shared from users' screenshots, only when two people agree."""
import json
from datetime import date

import pytest

from lottery_checker import shared
from lottery_checker.results_screen import read_screen
from tests.test_results_screen import _BOTTOM, _TOP, _TOP_4228

TODAY = date(2026, 10, 23)


def _read(*texts):
    from lottery_checker.results_screen import merge
    return merge([read_screen(t) for t in texts])


A, B, C = "client-a", "client-b", "client-c"


def test_one_person_is_not_enough(tmp_path):
    assert shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None


def test_two_people_agreeing_is_shared(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), B, tmp_path, TODAY)
    ref = shared.load_shared_ref("toto", 4228, tmp_path)
    assert ref.draw.winning == (3, 8, 11, 25, 33, 47) and ref.draw.additional == 12
    assert str(ref.draw_date) == "2026-10-22"


def test_same_person_twice_is_still_one(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None


def test_a_different_reading_does_not_count_towards_agreement(tmp_path):
    other = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(other), B, tmp_path, TODAY)
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None


def test_two_versions_each_with_two_people_is_a_conflict(tmp_path):
    other = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    for who, text in [(A, _TOP_4228), (B, _TOP_4228), (C, other), ("client-d", other)]:
        shared.submit(_read(text), who, tmp_path, TODAY)
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None


def test_prize_amounts_need_their_own_agreement(tmp_path):
    shared.submit(_read(_TOP_4228, _BOTTOM), A, tmp_path, TODAY)   # top + prize table
    shared.submit(_read(_TOP_4228), B, tmp_path, TODAY)            # top only: G1, G2
    d = shared.load_shared_ref("toto", 4228, tmp_path).draw
    assert d.prize_for(1) == 2928913.0 and d.prize_for(2) == 68513.0   # both saw these
    assert 3 not in d.group_prizes and 4 not in d.group_prizes        # only A saw them: pending
    assert d.prize_for(5) == 50                                      # fixed by the rules


def test_any_conflict_voids_the_draw_even_after_agreement(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), B, tmp_path, TODAY)
    assert shared.status("toto", 4228, tmp_path) == "agreed"
    other = _TOP_4228.replace("3 8 11 25 33 47", "3 8 11 25 33 48")
    shared.submit(_read(other), C, tmp_path, TODAY)                   # one person disagrees
    assert shared.status("toto", 4228, tmp_path) == "void"
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None
    shared.submit(_read(_TOP_4228), "client-d", tmp_path, TODAY)       # more agreement doesn't undo it
    assert shared.status("toto", 4228, tmp_path) == "void"
    rec = json.loads((tmp_path / "shared" / "toto" / "4228.json").read_text())
    assert rec["void"]["why"] == "screenshots read different numbers" and rec["state"] == "void"


def test_a_different_date_voids_the_draw(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    other_date = _TOP_4228.replace("Thu, 22 Oct 2026", "Wed, 21 Oct 2026")
    shared.submit(_read(other_date), B, tmp_path, TODAY)
    assert shared.status("toto", 4228, tmp_path) == "void"


def test_a_disagreeing_amount_leaves_only_that_group_pending(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), B, tmp_path, TODAY)
    odd = _TOP_4228.replace("Group 2 $68,513", "Group 2 $68,518")
    shared.submit(_read(odd.replace("Group 1 $2,928,913 1", "Group 1 $2,928,913 1")), C, tmp_path, TODAY)
    d = shared.load_shared_ref("toto", 4228, tmp_path).draw
    assert d.prize_for(1) == 2928913.0 and 2 not in d.group_prizes


def test_each_entry_records_device_and_time(tmp_path):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY, device="Android · Chrome")
    rec = json.loads((tmp_path / "shared" / "toto" / "4228.json").read_text())
    (cand,) = rec["candidates"].values()
    e = cand["entries"][0]
    assert e["who"] == A and e["device"] == "Android · Chrome" and e["at"].endswith("+00:00")
    assert rec["state"] == "waiting" and shared.status("toto", 4228, tmp_path) == "waiting"


@pytest.mark.parametrize("ua,label", [
    ("Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36", "Android · Chrome"),
    ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/122.0 Mobile Safari/537.36", "Android · Samsung Internet"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1", "iPhone · Safari"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0", "Windows · Edge"),
    (None, "Unknown · Other"),
])
def test_device_label(ua, label):
    assert shared.device_label(ua) == label


def test_nothing_shared_is_none(tmp_path):
    assert shared.status("toto", 4228, tmp_path) is None


def test_captured_draw_is_never_stored(tmp_path):
    p = tmp_path / "draws" / "toto" / "4227.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"game": "toto", "draw_no": 4227}))
    assert not shared.submit(_read(_TOP), A, tmp_path, TODAY)


def test_before_last_year_or_in_the_future_is_not_stored(tmp_path):
    """This year and last year are kept (owner, 22 Oct 2026); 2026 draws stop being taken in 2028."""
    assert shared.submit(_read(_TOP_4228), "x", tmp_path, date(2027, 12, 31))
    assert not shared.submit(_read(_TOP_4228), A, tmp_path, date(2028, 1, 1))
    assert not shared.submit(_read(_TOP_4228), A, tmp_path, date(2026, 10, 21))


def test_incomplete_reads_are_not_stored(tmp_path):
    assert not shared.submit(read_screen(_BOTTOM), A, tmp_path, TODAY)


def test_switch_off(tmp_path, monkeypatch):
    shared.submit(_read(_TOP_4228), A, tmp_path, TODAY)
    shared.submit(_read(_TOP_4228), B, tmp_path, TODAY)
    monkeypatch.setenv("TOTO_SHARED_RESULTS", "0")
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None
    assert not shared.submit(_read(_TOP_4228), C, tmp_path, TODAY)


def test_addresses_are_never_stored(tmp_path):
    who = shared.client_id("203.0.113.7", tmp_path)
    assert who != shared.client_id("203.0.113.8", tmp_path) and who == shared.client_id("203.0.113.7", tmp_path)
    shared.submit(_read(_TOP_4228), who, tmp_path, TODAY)
    for f in (tmp_path / "shared").rglob("*"):
        if f.is_file():
            assert "203.0.113" not in f.read_text(encoding="utf-8")


def test_a_damaged_file_is_not_a_result(tmp_path):
    p = tmp_path / "shared" / "toto" / "4228.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not json")
    assert shared.load_shared_ref("toto", 4228, tmp_path) is None


def test_a_stored_date_that_cannot_belong_to_the_draw_is_void(tmp_path):
    """Records saved before the 22 Oct date fix (draw 4216 dated 22 Oct) must not be served."""
    p = tmp_path / "shared" / "toto" / "4216.json"
    p.parent.mkdir(parents=True)
    e = [{"who": "a", "device": "x", "at": "t"}, {"who": "b", "device": "x", "at": "t"}]
    p.write_text(json.dumps({"game": "toto", "draw_no": 4216, "amounts": {},
                             "dates": {"2026-10-22": e},
                             "candidates": {"x": {"numbers": {"winning": [6, 16, 26, 30, 39, 42], "additional": 27},
                                                  "entries": e}}}))
    assert shared.status("toto", 4216, tmp_path) == "void"
    assert shared.load_shared_ref("toto", 4216, tmp_path) is None
