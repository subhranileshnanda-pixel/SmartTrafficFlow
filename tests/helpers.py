from forecast import level_of
from traffic_logic import SIGNAL_ORDER, YELLOW_TIME, ALL_RED_TIME
from vehicle import STOP_PROGRESS

ALLOWED_CHANGES = {("GREEN", "YELLOW"), ("YELLOW", "ALL_RED"), ("ALL_RED", "GREEN")}


def dens(default=(1, 1.0), **per_road):
    """Builds a densities dict. Example: dens(NORTH=(5, 5.0), SOUTH=(0, 0.0))."""
    out = {}
    for road in SIGNAL_ORDER:
        count, score = per_road.get(road, default)
        out[road] = {"count": count, "score": score, "level": level_of(score)}
    return out


def place(vehicle, dist_to_line):
    """Puts a vehicle so that its FRONT is dist_to_line pixels before its stop line."""
    front = STOP_PROGRESS[vehicle.road] - dist_to_line
    p = front - vehicle.length / 2
    if vehicle.dx:
        vehicle.x = p * vehicle.dx
    if vehicle.dy:
        vehicle.y = p * vehicle.dy
    return vehicle


def front(vehicle):
    return vehicle.progress() + vehicle.length / 2


class SafetyMonitor:
    """Call check(dt) after every controller update. It fails the test if a rule is broken:
    1. at most one road is non-red
    2. phases only change GREEN -> YELLOW -> ALL_RED -> GREEN
    3. the road only changes after an ALL_RED phase
    4. yellow and all-red last at least their configured time"""

    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.prev_road = ctrl.current_road()
        self.prev_phase = ctrl.phase
        self.elapsed = 0.0
        self.known = False          # the phase we start in has an unknown start time

    def check(self, dt):
        c = self.ctrl
        active = [r for r in SIGNAL_ORDER if c.get_state(r) != "RED"]
        assert len(active) <= 1, f"conflicting signals: {active}"

        self.elapsed += dt
        road, phase = c.current_road(), c.phase
        if (road, phase) != (self.prev_road, self.prev_phase):
            assert (self.prev_phase, phase) in ALLOWED_CHANGES, \
                f"illegal phase change {self.prev_phase} -> {phase}"
            if road != self.prev_road:
                assert self.prev_phase == "ALL_RED", "road changed without an all-red gap"
            if self.known:
                minimum = {"YELLOW": YELLOW_TIME, "ALL_RED": ALL_RED_TIME}.get(self.prev_phase)
                if minimum:
                    assert self.elapsed >= minimum - 0.01, \
                        f"{self.prev_phase} lasted only {self.elapsed:.2f}s"
            self.known = True
            self.elapsed = 0.0
            self.prev_road, self.prev_phase = road, phase


def step_until(ctrl, condition, limit=120.0, dt=0.05, densities=None, emergency_roads=None):
    """Runs the controller until condition(ctrl) is true. Returns the seconds it took."""
    densities = densities or dens()
    emergency_roads = emergency_roads or set()
    monitor = SafetyMonitor(ctrl)
    t = 0.0
    while t < limit:
        if condition(ctrl):
            return t
        ctrl.update(dt, densities, set(emergency_roads))
        monitor.check(dt)
        t += dt
    raise AssertionError(
        f"condition not reached within {limit}s (road={ctrl.current_road()}, phase={ctrl.phase})")