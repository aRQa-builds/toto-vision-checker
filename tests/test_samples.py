"""Sample tickets for the testing phase: valid, on empty draws, never random garbage."""
import random

import pytest

from lottery_checker import samples
from lottery_checker.ticket_entry import parse_ticket


@pytest.mark.parametrize("kind,n", [("toto", 1), ("4d", 1), ("five", 5)])
def test_samples_parse_ready_and_price_matches(kind, n, tmp_path):
    for seed in range(25):
        out = samples.make(kind, tmp_path, random.Random(seed))
        assert len(out) == n
        for s in out:
            d = parse_ticket(s["text"])
            assert d.ready, (s["text"], d.problems())
            assert d.draw_numbers == s["draws"]
            assert d.printed_price == d.stake()          # PRICE line matches the bets
            assert not d.warnings


def test_five_mixes_games_and_uses_distinct_draws(tmp_path):
    out = samples.make("five", tmp_path, random.Random(3))
    assert {"toto", "4d"} <= {s["game"] for s in out}
    for g in ("toto", "4d"):
        drawn = [n for s in out if s["game"] == g for n in s["draws"]]
        assert len(drawn) == len(set(drawn)) or len(drawn) > 10   # no draw repeated while others are free


def test_prefers_draws_with_nothing_on_file(tmp_path, monkeypatch):
    monkeypatch.setattr(samples.results_db, "wanted",
                        lambda game, d: {"to": 99, "wanted": [{"draw_no": 5430}, {"draw_no": 5431}]})
    for seed in range(10):
        s = samples.make("4d", tmp_path, random.Random(seed))[0]
        assert set(s["draws"]) <= {5430, 5431}


def test_bad_kind(tmp_path):
    with pytest.raises(ValueError):
        samples.make("lotto", tmp_path)
