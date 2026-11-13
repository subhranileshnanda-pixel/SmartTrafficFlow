"""Round 2: shorter greens and gap-out. Takes a few minutes, needs no backend."""
import contextlib
import io
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "simulation"))

import traffic_logic as tl
from config import SIGNAL_ORDER
from vehicle import try_spawn
from density import measure_all
from traffic_logic import SignalController

DT = 1 / 30
SEEDS = [1, 2, 3]
SCENARIO = [
    (120, (0.8, 1.8), [1, 1, 1, 1]),
    (120, (0.25, 0.6), [6, 1, 1, 1]),
    (120, (2.0, 3.5), [1, 1, 1, 1]),
    (120, (0.4, 0.9), [1, 1, 5, 1]),
]


class GapOutController(SignalController):
    """Ends a normal green early once the road has had no waiting vehicles for 1 second."""
    gap_min = 5

    def __init__(self, order):
        super().__init__(order)
        self.empty_for = 0.0

    def update(self, dt, densities, emergency_roads):
        if self.phase == "GREEN" and not self.emergency_mode and not self.emergency_queue:
            if densities[self.current_road()]["count"] == 0:
                self.empty_for += dt
            else:
                self.empty_for = 0.0
            if self.green_time - self.timer >= self.gap_min and self.empty_for >= 1.0:
                self.timer = 0.0            # the normal path then goes to YELLOW
                self.empty_for = 0.0
        else:
            self.empty_for = 0.0
        super().update(dt, densities, emergency_roads)


DEFAULTS = dict(mode="adaptive", min_green=8, max_green=25, sps=1.5, fixed=15, gap=False)

VARIANTS = [
    ("fixed 10 s (best so far)", dict(mode="fixed", fixed=10)),
    ("fixed 7 s", dict(mode="fixed", fixed=7)),
    ("adaptive (current)", {}),
    ("adaptive, min 5, max 15, 0.5 s/point", dict(min_green=5, max_green=15, sps=0.5)),
    ("adaptive, min 6, max 20, 0.8 s/point", dict(min_green=6, max_green=20, sps=0.8)),
    ("gap-out + current settings", dict(gap=True)),
    ("gap-out, min 5, max 15, 0.5 s/point", dict(gap=True, min_green=5, max_green=15, sps=0.5)),
    ("gap-out, min 6, max 20, 0.8 s/point", dict(gap=True, min_green=6, max_green=20, sps=0.8)),
    ("gap-out, min 8, max 25, 1.0 s/point", dict(gap=True, min_green=8, max_green=25, sps=1.0)),
]


def run(cfg, seed):
    tl.MIN_GREEN, tl.MAX_GREEN = cfg["min_green"], cfg["max_green"]
    tl.SECONDS_PER_SCORE, tl.FIXED_GREEN = cfg["sps"], cfg["fixed"]
    random.seed(seed)
    ctrl = (GapOutController if cfg["gap"] else SignalController)(SIGNAL_ORDER)
    ctrl.mode = cfg["mode"]
    vehicles = {r: [] for r in SIGNAL_ORDER}
    densities = measure_all(vehicles)
    waits, passed, spawn_timer = [], 0, 0.0

    with contextlib.redirect_stdout(io.StringIO()):
        for duration, spawn_range, bias in SCENARIO:
            for _ in range(int(duration / DT)):
                ctrl.update(DT, densities, set())
                spawn_timer -= DT
                if spawn_timer <= 0:
                    road = random.choices(SIGNAL_ORDER, weights=bias)[0]
                    try_spawn(vehicles[road], road)
                    spawn_timer = random.uniform(*spawn_range)

                for road, lane in vehicles.items():
                    lane.sort(key=lambda v: v.progress(), reverse=True)
                    state = ctrl.get_state(road)
                    for i, v in enumerate(lane):
                        ahead = lane[i - 1] if i > 0 else None
                        x0, y0 = v.x, v.y
                        v.update(state, ahead, DT)
                        if v.before_stop_line():
                            if abs(v.x - x0) + abs(v.y - y0) < 1e-6:
                                v.wait = getattr(v, "wait", 0.0) + DT
                        elif not getattr(v, "counted", False):
                            v.counted = True
                            passed += 1
                            waits.append(getattr(v, "wait", 0.0))
                    lane[:] = [v for v in lane if not v.is_off_screen()]
                densities = measure_all(vehicles)

    for lane in vehicles.values():
        for v in lane:
            if v.before_stop_line():
                waits.append(getattr(v, "wait", 0.0))
    return (sum(waits) / len(waits) if waits else 0, max(waits) if waits else 0, passed)


print(f"Testing {len(VARIANTS)} variants, {len(SEEDS)} runs each. This takes a few minutes...\n")
rows = []
for name, change in VARIANTS:
    cfg = {**DEFAULTS, **change}
    runs = [run(cfg, s) for s in SEEDS]
    rows.append((name, *[sum(r[i] for r in runs) / len(runs) for i in range(3)]))
    print(f"  done: {name}")

rows.sort(key=lambda r: r[1])
print(f"\n{'Variant':<42}{'Avg wait (s)':>14}{'Max wait (s)':>14}{'Passed':>9}")
for name, avg, mx, passed in rows:
    print(f"{name:<42}{avg:>14.1f}{mx:>14.1f}{passed:>9.0f}")
print("\nDONE")