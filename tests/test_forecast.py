import random
import pytest
from forecast import Forecaster, level_of, MAX_SCORE, CONTROL_HORIZON
from traffic_logic import SIGNAL_ORDER, calculate_green_time


def feed(f, values, road="NORTH"):
    for v in values:
        f.update(1.0, {r: {"score": v if r == road else 0} for r in SIGNAL_ORDER})


def test_no_data_means_no_forecast():
    assert Forecaster(SIGNAL_ORDER).forecast("NORTH", 10) == 0


def test_steady_traffic_is_forecast_as_steady():
    f = Forecaster(SIGNAL_ORDER)
    feed(f, [5] * 40)
    assert f.forecast("NORTH", 10) == pytest.approx(5, abs=0.3)
    assert f.snapshot()["NORTH"]["trend"] == "steady"


def test_rising_traffic_is_forecast_higher_than_now():
    f = Forecaster(SIGNAL_ORDER)
    values = [i * 0.5 for i in range(20)]
    feed(f, values)
    assert f.forecast("NORTH", 10) > values[-1]
    assert f.snapshot()["NORTH"]["trend"] == "rising"


def test_falling_traffic_is_forecast_lower():
    f = Forecaster(SIGNAL_ORDER)
    values = [10 - i * 0.5 for i in range(20)]
    feed(f, values)
    assert f.forecast("NORTH", 10) <= values[-1]
    assert f.snapshot()["NORTH"]["trend"] == "falling"


def test_forecast_is_capped_and_never_negative():
    up, down = Forecaster(SIGNAL_ORDER), Forecaster(SIGNAL_ORDER)
    feed(up, [i * 10 for i in range(30)])
    feed(down, [max(0, 100 - i * 10) for i in range(30)])
    assert up.forecast("NORTH", 60) <= MAX_SCORE
    assert down.forecast("NORTH", 60) >= 0


def test_roads_are_forecast_independently():
    f = Forecaster(SIGNAL_ORDER)
    feed(f, [i * 0.5 for i in range(20)], road="EAST")
    snap = f.snapshot()
    assert snap["EAST"]["trend"] == "rising"
    assert snap["SOUTH"]["trend"] == "steady"


def test_planned_score_is_never_below_the_current_score():
    rng = random.Random(5)
    f = Forecaster(SIGNAL_ORDER)
    for _ in range(200):
        value = rng.uniform(0, 15)
        feed(f, [value])
        assert f.effective_score("NORTH", value) >= value


def test_predictive_gives_extra_green_to_a_road_that_is_filling_up():
    f = Forecaster(SIGNAL_ORDER)
    values = [i * 0.5 for i in range(20)]
    feed(f, values)
    now = values[-1]
    assert calculate_green_time(f.effective_score("NORTH", now)) > calculate_green_time(now)


def test_samples_are_taken_once_per_second():
    f = Forecaster(SIGNAL_ORDER)
    d = {r: {"score": 4} for r in SIGNAL_ORDER}
    for _ in range(9):
        f.update(0.1, d)
    assert f.state["NORTH"] is None
    f.update(0.1, d)
    assert f.state["NORTH"] is not None


@pytest.mark.parametrize("score,level", [(0, "LOW"), (3, "LOW"), (4, "MEDIUM"), (7, "MEDIUM"), (8, "HIGH")])
def test_forecast_levels_use_the_same_thresholds_as_the_simulation(score, level):
    assert level_of(score) == level