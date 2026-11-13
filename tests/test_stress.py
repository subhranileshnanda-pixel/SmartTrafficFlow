import pytest
from traffic_logic import MODES
from sim_harness import run_simulation

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("mode", MODES)
def test_heavy_traffic_with_frequent_emergencies(mode):
    r = run_simulation(mode, minutes=4, spawn_range=(0.25, 0.6), emergency_every=30, seed=7)
    assert r["min_gap"] >= -0.5, "vehicles overlapped"
    assert r["emergencies"] >= 5
    assert r["missed"] == 0, "an emergency vehicle never got through"
    assert r["worst_wait"] <= 60, f"an emergency vehicle waited {r['worst_wait']:.0f}s"
    assert sum(r["passed"].values()) > 50


@pytest.mark.parametrize("mode", MODES)
def test_one_extremely_busy_road_does_not_starve_the_others(mode):
    r = run_simulation(mode, minutes=4, spawn_range=(0.3, 0.7), bias=(8, 1, 1, 1), seed=3)
    assert all(count > 0 for count in r["passed"].values()), r["passed"]


def test_light_traffic_runs_cleanly():
    r = run_simulation("predictive", minutes=3, spawn_range=(2.0, 3.5), seed=11)
    assert sum(r["passed"].values()) > 10