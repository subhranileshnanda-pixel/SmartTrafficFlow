"""Compares fixed, adaptive and predictive signal control on identical traffic.
Runs without a window. Needs no backend. Takes about 1 to 2 minutes."""
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

from config import SIGNAL_ORDER            # simulation settings
from vehicle import try_spawn              # simulation vehicles
from density import measure_all            # simulation density measurement
from traffic_logic import SignalController, MODES   # the same controller the backend uses

DT = 1 / 30
SEEDS = [11, 12, 13]

# (seconds, (min, max) delay between spawns, road weights N, E, S, W)
SCENARIO = [
    (120, (0.8, 1.8), [1, 1, 1, 1]),      # normal traffic
    (120, (0.25, 0.6), [6, 1, 1, 1]),     # heavy, mostly North
    (120, (2.0, 3.5), [1, 1, 1, 1]),      # light traffic
    (120, (0.4, 0.9), [1, 1, 5, 1]),      # busy South
]


def run(mode, seed):
    random.seed(seed)
    ctrl = SignalController(SIGNAL_ORDER)
    ctrl.mode = mode
    vehicles = {r: [] for r in SIGNAL_ORDER}
    densities = measure_all(vehicles)
    waits = []
    passed = 0
    spawned = 0
    spawn_timer = 0.0

    with contextlib.redirect_stdout(io.StringIO()):          # hide the controller's print lines
        for duration, spawn_range, bias in SCENARIO:
            for _ in range(int(duration / DT)):
                ctrl.update(DT, densities, set())

                spawn_timer -= DT
                if spawn_timer <= 0:
                    road = random.choices(SIGNAL_ORDER, weights=bias)[0]
                    before = len(vehicles[road])
                    try_spawn(vehicles[road], road)
                    spawned += len(vehicles[road]) - before
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

    # vehicles still queued at the end have also been waiting
    still_waiting = 0
    for lane in vehicles.values():
        for v in lane:
            if v.before_stop_line():
                still_waiting += 1
                waits.append(getattr(v, "wait", 0.0))

    return {
        "avg_wait": sum(waits) / len(waits) if waits else 0,
        "max_wait": max(waits) if waits else 0,
        "passed": passed,
        "still_waiting": still_waiting,
    }


print(f"Simulating {sum(s[0] for s in SCENARIO)} s of traffic, {len(SEEDS)} runs per mode...\n")
table = {}
for mode in MODES:
    runs = [run(mode, seed) for seed in SEEDS]
    table[mode] = {k: sum(r[k] for r in runs) / len(runs) for k in runs[0]}
    print(f"  finished: {mode}")

print()
print(f"{'Mode':<12}{'Avg wait (s)':>14}{'Max wait (s)':>14}{'Vehicles passed':>18}{'Queued at end':>15}")
for mode in MODES:
    r = table[mode]
    print(f"{mode:<12}{r['avg_wait']:>14.1f}{r['max_wait']:>14.1f}{r['passed']:>18.0f}{r['still_waiting']:>15.1f}")

base = table["fixed"]["avg_wait"]
if base > 0:
    print()
    for mode in ("adaptive", "predictive"):
        change = (base - table[mode]["avg_wait"]) / base * 100
        print(f"{mode} vs fixed timer: average wait {'reduced' if change >= 0 else 'increased'} by {abs(change):.0f}%")
    gain = (table["adaptive"]["avg_wait"] - table["predictive"]["avg_wait"]) / table["adaptive"]["avg_wait"] * 100
    print(f"predictive vs adaptive: average wait {'reduced' if gain >= 0 else 'increased'} by {abs(gain):.0f}%")