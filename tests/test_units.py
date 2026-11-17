"""P6-15 slice A: unit share and unit stake (spec p6-15-units-share)."""
import pytest

from lottery_checker.units import UNIT_KINDS, unit_share, unit_stake


def test_kinds():
    assert UNIT_KINDS == ("group", "itoto")


def test_group_share_is_win_over_units_whatever_the_unit_number():
    assert unit_share(300.0, "group", 1, 3) == pytest.approx(100.0)
    assert unit_share(300.0, "group", 3, 3) == pytest.approx(100.0)
    assert unit_share(50.0, "group", 2, 3) == pytest.approx(50.0 / 3)      # not rounded


def test_itoto_share_is_win_times_units_bought_over_total():
    assert unit_share(2800.0, "itoto", 1, 28) == pytest.approx(100.0)
    assert unit_share(2800.0, "itoto", 3, 28) == pytest.approx(300.0)


def test_zero_win_is_zero_and_unpublished_stays_none():
    assert unit_share(0.0, "group", 1, 3) == 0.0
    assert unit_share(None, "group", 1, 3) is None
    assert unit_share(None, "itoto", 1, 28) is None


def test_stake_is_the_per_unit_price():
    assert unit_stake(24.0, "group", 1, 3) == pytest.approx(8.0)           # the specimen: $24 over 3 units
    assert unit_stake(924.0, "itoto", 1, 28) == pytest.approx(33.0)        # the specimen: System 12
    assert unit_stake(924.0, "itoto", 2, 28) == pytest.approx(66.0)
    assert unit_stake(24.0, "group", 1, 7) == pytest.approx(24.0 / 7)      # not rounded


@pytest.mark.parametrize("kind,a,b", [("bogus", 1, 3), ("group", 1, 0), ("group", 0, 3),
                                      ("group", 4, 3), ("itoto", 29, 28), ("itoto", 1, -2)])
def test_bad_units_raise(kind, a, b):
    with pytest.raises(ValueError):
        unit_share(10.0, kind, a, b)
    with pytest.raises(ValueError):
        unit_stake(10.0, kind, a, b)
