"""P5-01 draw statistics: descriptive only, owner view."""
import json

from lottery_checker import stats


def toto(n, win, add):
    return {"game": "toto", "draw_no": n, "winning": win, "additional": add}


def fourd(n, first, second="0000", third="0000", starter=(), consolation=()):
    return {"game": "4d", "draw_no": n, "first": first, "second": second, "third": third,
            "starter": list(starter), "consolation": list(consolation)}


def test_note_has_no_prediction_words():
    for w in ("hot", "cold", "due", "lucky"):
        assert w not in stats.NOTE.lower().split()
    assert "independent" in stats.NOTE and "do not predict" in stats.NOTE


def test_toto_counts_and_expected():
    draws = [toto(1, [1, 2, 3, 4, 5, 6], 7), toto(2, [1, 8, 9, 10, 11, 12], 2)]
    s = stats.toto_stats(draws)
    assert s["game"] == "toto" and s["draws"] == 2 and s["enough"] is False
    assert len(s["numbers"]) == 49
    one, two, seven, forty = (s["numbers"][i] for i in (0, 1, 6, 39))
    assert one["number"] == 1 and one["drawn"] == 2 and one["additional"] == 0
    assert two["drawn"] == 1 and two["additional"] == 1
    assert seven["drawn"] == 0 and seven["additional"] == 1
    assert forty["drawn"] == 0 and forty["additional"] == 0
    assert abs(one["expected"] - 2 * 6 / 49) < 1e-9


def test_toto_since_counts_draws_after_last_seen_in_the_six():
    draws = [toto(3, [9, 8, 7, 6, 5, 4], 1), toto(1, [1, 2, 3, 4, 5, 6], 7), toto(2, [10, 11, 12, 13, 14, 15], 1)]
    s = stats.toto_stats(draws)       # draw order is by draw number, whatever the input order
    by = {r["number"]: r for r in s["numbers"]}
    assert by[9]["since"] == 0
    assert by[10]["since"] == 1
    assert by[1]["since"] == 2
    assert by[49]["since"] is None
    assert by[7]["since"] == 0      # 7 was the Additional in draw 1 but is in the six in draw 3


def test_toto_numbers_stay_in_number_order_never_ranked():
    draws = [toto(i, [40, 41, 42, 43, 44, 45], 46) for i in range(1, 40)]
    s = stats.toto_stats(draws)
    assert s["enough"] is True
    assert [r["number"] for r in s["numbers"]] == list(range(1, 50))


def test_fourd_first_prize_digits_by_position():
    draws = [fourd(1, "8455"), fourd(2, "8123")]
    s = stats.fourd_stats(draws)
    assert s["game"] == "4d" and s["draws"] == 2 and s["enough"] is False
    pos = s["first_digits"]
    assert len(pos) == 4 and all(len(p) == 10 for p in pos)
    assert pos[0][8] == 2 and pos[0][0] == 0
    assert pos[1][4] == 1 and pos[1][1] == 1
    assert pos[3][5] == 1 and pos[3][3] == 1
    assert s["expected_per_digit"] == 0.2


def test_fourd_distinct_numbers_cover_all_prizes():
    draws = [fourd(1, "1111", "2222", "3333", ["4444", "5555"], ["6666"]),
             fourd(2, "1111", "2222", "3333", ["4444", "7777"], ["6666"])]
    assert stats.fourd_stats(draws)["distinct_numbers"] == 7


def test_empty_input_is_safe():
    assert stats.toto_stats([])["draws"] == 0
    assert stats.fourd_stats([])["first_digits"] == [[0] * 10 for _ in range(4)]
    assert stats.toto_stats([])["numbers"][0]["since"] is None


def test_all_stats_reads_captured_draws_only(tmp_path):
    (tmp_path / "draws" / "toto").mkdir(parents=True)
    (tmp_path / "draws" / "4d").mkdir(parents=True)
    (tmp_path / "draws" / "toto" / "1.json").write_text(json.dumps(toto(1, [1, 2, 3, 4, 5, 6], 7)))
    (tmp_path / "draws" / "toto" / "bad.json").write_text("{not json")
    (tmp_path / "draws" / "4d" / "9.json").write_text(json.dumps(fourd(9, "1234")))
    out = stats.all_stats(tmp_path)
    assert out["toto"]["draws"] == 1 and out["4d"]["draws"] == 1
    assert out["note"] == stats.NOTE
    assert stats.all_stats(tmp_path / "nowhere")["toto"]["draws"] == 0


def test_min_draws_threshold():
    assert stats.MIN_DRAWS == 30
    assert stats.toto_stats([toto(i, [1, 2, 3, 4, 5, 6], 7) for i in range(30)])["enough"] is True
    assert stats.toto_stats([toto(i, [1, 2, 3, 4, 5, 6], 7) for i in range(29)])["enough"] is False
