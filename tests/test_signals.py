import random
import pytest
from traffic_logic import (
    SignalController, SIGNAL_ORDER, MODES, calculate_green_time,
    MIN_GREEN, MAX_GREEN, FIXED_GREEN, EMERGENCY_CLEAR_TIME, EMERGENCY_MAX_HOLD,
    GAP_MIN_GREEN, GAP_EMPTY_TIME,
)
from helpers import dens, step_until, SafetyMonitor


def new(mode="adaptive"):
    c = SignalController(SIGNAL_ORDER)
    c.mode = mode
    return c


# ---------------------------------------------------------------- adaptive timing
@pytest.mark.parametrize("score,green", [(0, 6), (6, 10.8), (15, 18), (25, 20), (50, 20)])
def test_green_time_formula(score, green):
    assert calculate_green_time(score) == pytest.approx(green)

# ---------------------------------------------------------------- gap-out
def test_green_ends_early_when_the_queue_has_cleared():
    c = new()
    d = dens(default=(1, 1.0), NORTH=(0, 0.0))          # NORTH has green but nothing is waiting
    t = step_until(c, lambda x: x.phase == "YELLOW", densities=d)
    assert GAP_MIN_GREEN - 0.1 <= t <= GAP_MIN_GREEN + GAP_EMPTY_TIME
    assert t < MIN_GREEN - 0.2                          # earlier than the planned green


def test_green_is_not_cut_short_while_vehicles_are_waiting():
    c = new()
    t = step_until(c, lambda x: x.phase == "YELLOW", densities=dens(default=(3, 3.0)))
    assert t == pytest.approx(MIN_GREEN, abs=0.2)


def test_fixed_mode_never_ends_a_green_early():
    c = new("fixed")
    t = step_until(c, lambda x: x.phase == "YELLOW", densities=dens(default=(0, 0.0)))
    assert t == pytest.approx(MIN_GREEN, abs=0.2)    


def test_roads_take_turns_in_order_and_greens_stay_in_bounds():
    c, d = new(), dens()
    mon, order, prev, t = SafetyMonitor(c), [], c.phase, 0.0
    while t < 300:
        c.update(0.05, d, set())
        mon.check(0.05)
        t += 0.05
        if prev == "ALL_RED" and c.phase == "GREEN":
            order.append(c.current_road())
            assert MIN_GREEN <= c.green_time <= MAX_GREEN
        prev = c.phase
    assert len(order) >= 8
    assert order == [SIGNAL_ORDER[(1 + i) % 4] for i in range(len(order))]


def test_busy_road_gets_a_longer_green_than_a_quiet_road():
    c = new()
    d = dens(default=(1, 1.0), EAST=(10, 10.0))
    step_until(c, lambda x: x.current_road() == "EAST" and x.phase == "GREEN", densities=d)
    assert c.green_time == pytest.approx(calculate_green_time(10.0))
    assert c.green_time > calculate_green_time(1.0)


def test_empty_roads_are_skipped():
    c = new()
    d = dens(default=(0, 0.0), SOUTH=(4, 4.0))
    step_until(c, lambda x: x.current_road() != "NORTH" and x.phase == "GREEN", densities=d)
    assert c.current_road() == "SOUTH"


def test_fixed_mode_ignores_traffic():
    c, d = new("fixed"), dens(default=(0, 0.0))
    mon, order, prev, t = SafetyMonitor(c), [], c.phase, 0.0
    while t < 300:
        c.update(0.05, d, set())
        mon.check(0.05)
        t += 0.05
        if prev == "ALL_RED" and c.phase == "GREEN":
            order.append(c.current_road())
            assert c.green_time == FIXED_GREEN
        prev = c.phase
    assert order[:4] == ["EAST", "SOUTH", "WEST", "NORTH"]


def test_no_road_starves_when_one_road_is_always_busy():
    c = new()
    d = dens(default=(1, 1.0), NORTH=(30, 30.0))
    mon, starts, prev, t = SafetyMonitor(c), {r: [] for r in SIGNAL_ORDER}, c.phase, 0.0
    while t < 600:
        c.update(0.05, d, set())
        mon.check(0.05)
        t += 0.05
        if prev == "ALL_RED" and c.phase == "GREEN":
            starts[c.current_road()].append(t)
        prev = c.phase
    for road, times in starts.items():
        assert len(times) >= 3, f"{road} got only {len(times)} turns"
        gaps = [b - a for a, b in zip(times, times[1:])]
        assert max(gaps) <= 125, f"{road} waited {max(gaps):.0f}s between turns"


# ---------------------------------------------------------------- emergency priority
def test_emergency_cuts_the_current_green_with_a_normal_yellow():
    c = new()
    c.request_emergency("EAST")
    c.update(0.05, dens(), {"EAST"})
    assert c.current_road() == "NORTH" and c.phase == "YELLOW"      # not an instant switch

    step_until(c, lambda x: x.emergency_mode, emergency_roads={"EAST"})
    assert c.current_road() == "EAST" and c.phase == "GREEN"
    assert [r for r in SIGNAL_ORDER if c.get_state(r) != "RED"] == ["EAST"]


def test_emergency_green_is_held_until_the_vehicle_passes():
    c = new()
    c.request_emergency("EAST")
    step_until(c, lambda x: x.emergency_mode, emergency_roads={"EAST"})

    for _ in range(200):                                            # 10 more seconds
        c.update(0.05, dens(), {"EAST"})
    assert c.emergency_mode and c.phase == "GREEN" and c.current_road() == "EAST"

    step_until(c, lambda x: not x.emergency_mode, limit=2)         # vehicle has crossed the line
    assert c.phase == "GREEN"
    assert c.timer == pytest.approx(EMERGENCY_CLEAR_TIME, abs=0.1)


def test_normal_control_resumes_after_an_emergency():
    c = new()
    c.request_emergency("EAST")
    step_until(c, lambda x: x.emergency_mode, emergency_roads={"EAST"})
    step_until(c, lambda x: not x.emergency_mode, limit=2)
    step_until(c, lambda x: x.phase == "GREEN" and not x.emergency_mode and x.current_road() != "EAST")
    assert c.current_road() == "SOUTH"                              # the normal order continues


def test_emergency_on_the_road_that_is_already_green_just_holds_it():
    c = new()
    c.request_emergency("NORTH")
    c.update(0.05, dens(), {"NORTH"})
    assert c.emergency_mode and c.phase == "GREEN" and c.emergency_queue == []


def test_emergency_requested_during_yellow_waits_for_the_all_red():
    c = new()
    step_until(c, lambda x: x.phase == "YELLOW")
    c.request_emergency("WEST")
    assert c.phase == "YELLOW"
    step_until(c, lambda x: x.emergency_mode, emergency_roads={"WEST"})
    assert c.current_road() == "WEST" and c.phase == "GREEN"


def test_two_emergencies_are_served_one_after_the_other():
    c, mon = new(), None
    mon = SafetyMonitor(c)
    pending, held, served, t = {"SOUTH", "WEST"}, {}, [], 0.0
    c.request_emergency("SOUTH")
    c.request_emergency("WEST")
    while t < 120 and len(served) < 2:
        c.update(0.05, dens(), set(pending))
        mon.check(0.05)
        t += 0.05
        road = c.current_road()
        if c.emergency_mode and road in pending:
            if road not in served:
                served.append(road)
            held[road] = held.get(road, 0) + 0.05
            if held[road] >= 2:
                pending.discard(road)                               # this vehicle has passed
    assert served == ["SOUTH", "WEST"]


def test_stuck_emergency_vehicle_cannot_hold_the_green_forever():
    c = new()
    c.request_emergency("EAST")
    step_until(c, lambda x: x.emergency_mode, emergency_roads={"EAST"})
    step_until(c, lambda x: not x.emergency_mode, limit=EMERGENCY_MAX_HOLD + 5,
               emergency_roads={"EAST"})                            # the vehicle never "passes"
    assert EMERGENCY_MAX_HOLD - 0.2 <= c.hold_time <= EMERGENCY_MAX_HOLD + 0.3


def test_duplicate_emergency_requests_are_ignored():
    c = new()
    c.request_emergency("EAST")
    c.request_emergency("EAST")
    assert c.emergency_queue == ["EAST"]


# ---------------------------------------------------------------- randomised safety test
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_traffic_and_emergencies_never_break_safety(mode, seed):
    rng = random.Random(seed)
    c, dt = new(mode), 0.1
    mon, d, emg, prev = SafetyMonitor(c), dens(), set(), c.phase
    for step in range(12000):                                       # 20 simulated minutes
        if step % 10 == 0:
            d = {}
            for r in SIGNAL_ORDER:
                count = rng.randint(0, 9)
                d[r] = {"count": count, "score": count * rng.uniform(0.5, 2), "level": "LOW"}
            emg = {r for r in SIGNAL_ORDER if rng.random() < 0.3} if rng.random() < 0.5 else set()
        if rng.random() < 0.004:
            c.request_emergency(rng.choice(SIGNAL_ORDER))
        c.update(dt, d, emg)
        mon.check(dt)
        if prev == "ALL_RED" and c.phase == "GREEN" and not c.emergency_mode:
            if mode == "fixed":
                assert c.green_time == FIXED_GREEN
            else:
                assert MIN_GREEN <= c.green_time <= MAX_GREEN
        prev = c.phase