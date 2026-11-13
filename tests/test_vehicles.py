import pytest
from config import SIGNAL_ORDER
from vehicle import Vehicle, try_spawn, spawn_emergency, STOP_PROGRESS, MIN_GAP
from helpers import place, front

DT = 1 / 60


@pytest.mark.parametrize("road", SIGNAL_ORDER)
def test_vehicle_stops_at_a_red_light(road):
    v = place(Vehicle(road, "car"), 250)
    for _ in range(600):                                   # 10 seconds
        v.update("RED", None, DT)
        assert front(v) <= STOP_PROGRESS[road] + 1e-6, "vehicle crossed the stop line on red"
    assert STOP_PROGRESS[road] - front(v) < 1.0            # and it did get up to the line


@pytest.mark.parametrize("road", SIGNAL_ORDER)
def test_vehicle_drives_through_on_green(road):
    v = place(Vehicle(road, "car"), 250)
    for _ in range(600):
        v.update("GREEN", None, DT)
    assert front(v) > STOP_PROGRESS[road] + 50


def test_vehicle_already_past_the_line_keeps_moving_on_red():
    v = place(Vehicle("NORTH", "car"), -10)
    start = v.progress()
    for _ in range(60):
        v.update("RED", None, DT)
    assert v.progress() > start + 50


def test_vehicle_keeps_a_gap_behind_the_one_in_front():
    leader = place(Vehicle("EAST", "bus"), 200)
    leader.speed = 0                                       # a stalled vehicle
    follower = place(Vehicle("EAST", "bike"), 450)
    for _ in range(900):
        follower.update("GREEN", leader, DT)
    gap = (leader.progress() - leader.length / 2) - front(follower)
    assert gap >= MIN_GAP - 1e-6


def test_normal_spawning_never_overlaps():
    lane = []
    for _ in range(300):
        try_spawn(lane, "SOUTH")
    positions = [v.progress() for v in lane]
    assert all(abs(a - b) >= 110 for i, a in enumerate(positions) for b in positions[i + 1:])


def test_normal_spawning_never_creates_emergency_vehicles():
    for _ in range(300):
        lane = []
        try_spawn(lane, "WEST")
        assert not lane or not lane[0].is_emergency


def test_emergency_spawn_is_refused_when_the_entrance_is_blocked():
    assert spawn_emergency([Vehicle("NORTH", "car")], "NORTH", "ambulance") is None


def test_emergency_spawn_works_on_an_empty_road():
    v = spawn_emergency([], "NORTH", "ambulance")
    assert v is not None and v.is_emergency