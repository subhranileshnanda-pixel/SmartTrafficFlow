import random
from config import SIGNAL_ORDER
from vehicle import try_spawn, spawn_emergency
from density import measure_all
from traffic_logic import SignalController
from helpers import SafetyMonitor

EMERGENCY_KINDS = ["ambulance", "firetruck", "police"]


def run_simulation(mode, minutes=4, spawn_range=(0.8, 1.8), bias=(1, 1, 1, 1),
                   emergency_every=None, seed=1, dt=1 / 30):
    random.seed(seed)
    ctrl = SignalController(SIGNAL_ORDER)
    ctrl.mode = mode
    monitor = SafetyMonitor(ctrl)
    vehicles = {r: [] for r in SIGNAL_ORDER}
    densities = measure_all(vehicles)

    passed = {r: 0 for r in SIGNAL_ORDER}
    emergencies = []
    min_gap = float("inf")
    spawn_timer = 0.0
    next_emergency = emergency_every
    t = 0.0

    for _ in range(int(minutes * 60 / dt)):
        t += dt

        if next_emergency is not None and t >= next_emergency:
            next_emergency += emergency_every
            roads = SIGNAL_ORDER[:]
            random.shuffle(roads)
            kind = random.choice(EMERGENCY_KINDS)
            for road in roads:
                v = spawn_emergency(vehicles[road], road, kind)
                if v:
                    ctrl.request_emergency(road)
                    emergencies.append({"vehicle": v, "spawned": t, "crossed": None})
                    break

        emergency_roads = {
            r for r, lane in vehicles.items()
            if any(v.is_emergency and v.before_stop_line() for v in lane)
        }
        ctrl.update(dt, densities, emergency_roads)
        monitor.check(dt)

        spawn_timer -= dt
        if spawn_timer <= 0:
            road = random.choices(SIGNAL_ORDER, weights=bias)[0]
            try_spawn(vehicles[road], road)
            spawn_timer = random.uniform(*spawn_range)

        for road, lane in vehicles.items():
            lane.sort(key=lambda v: v.progress(), reverse=True)
            state = ctrl.get_state(road)
            for i, v in enumerate(lane):
                ahead = lane[i - 1] if i > 0 else None
                v.update(state, ahead, dt)
                if not v.before_stop_line() and not getattr(v, "counted", False):
                    v.counted = True
                    passed[road] += 1
            for i in range(1, len(lane)):
                gap = (lane[i - 1].progress() - lane[i - 1].length / 2) - \
                      (lane[i].progress() + lane[i].length / 2)
                min_gap = min(min_gap, gap)
            lane[:] = [v for v in lane if not v.is_off_screen()]

        densities = measure_all(vehicles)
        for e in emergencies:
            if e["crossed"] is None and not e["vehicle"].before_stop_line():
                e["crossed"] = t

    waits = [e["crossed"] - e["spawned"] for e in emergencies if e["crossed"] is not None]
    missed = [e for e in emergencies if e["crossed"] is None and t - e["spawned"] > 60]
    return {
        "passed": passed,
        "min_gap": min_gap,
        "emergencies": len(emergencies),
        "missed": len(missed),
        "worst_wait": max(waits) if waits else 0,
    }