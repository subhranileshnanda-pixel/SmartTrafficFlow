import pytest
from config import DETECTION_ZONE, SIGNAL_ORDER, VEHICLE_WEIGHT
from vehicle import Vehicle
from density import density_level, in_detection_zone, measure_road, measure_all
from helpers import place


@pytest.mark.parametrize("score,level", [
    (0, "LOW"), (3, "LOW"), (3.5, "MEDIUM"), (7, "MEDIUM"), (7.5, "HIGH"), (30, "HIGH"),
])
def test_density_levels(score, level):
    assert density_level(score) == level


@pytest.mark.parametrize("dist,expected", [
    (100, True), (DETECTION_ZONE, True), (DETECTION_ZONE + 50, False), (-50, False),
])
def test_detection_zone_edges(dist, expected):
    v = place(Vehicle("NORTH", "car"), dist)
    assert in_detection_zone(v) is expected


@pytest.mark.parametrize("road", SIGNAL_ORDER)
def test_zone_works_on_all_four_roads(road):
    result = measure_road([place(Vehicle(road, "car"), 100)])
    assert result["count"] == 1 and result["score"] == 1


@pytest.mark.parametrize("kind", list(VEHICLE_WEIGHT))
def test_each_vehicle_type_uses_its_weight(kind):
    result = measure_road([place(Vehicle("EAST", kind), 100)])
    assert result["score"] == VEHICLE_WEIGHT[kind]


def test_mixed_queue_score_and_level():
    lane = [place(Vehicle("SOUTH", k), 50 + 80 * i) for i, k in enumerate(["car", "bus", "bike"])]
    result = measure_road(lane)
    assert result["count"] == 3
    assert result["score"] == 3.5
    assert result["level"] == "MEDIUM"


def test_long_queue_is_high():
    # 4 buses (weight 2 each) inside the 300 px detection zone -> score 8
    lane = [place(Vehicle("WEST", "bus"), 10 + 80 * i) for i in range(4)]
    result = measure_road(lane)
    assert result["score"] == 8
    assert result["level"] == "HIGH"


def test_vehicles_outside_the_zone_are_ignored():
    lane = [place(Vehicle("NORTH", "car"), 500), place(Vehicle("NORTH", "car"), -40)]
    result = measure_road(lane)
    assert result["count"] == 0 and result["level"] == "LOW"


def test_measure_all_covers_every_road():
    result = measure_all({r: [] for r in SIGNAL_ORDER})
    assert set(result) == set(SIGNAL_ORDER)
    assert all(v["level"] == "LOW" for v in result.values())