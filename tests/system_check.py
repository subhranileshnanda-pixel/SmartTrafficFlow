"""End-to-end check. Run it while SmartFlow is already running (start_all.ps1)."""
import time
import requests

BASE = "http://127.0.0.1:8000"
HEADERS = {}          # filled in after login
results = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    results.append(ok)


def get(path):
    return requests.get(BASE + path, headers=HEADERS, timeout=3).json()


print("\n1. Components")
try:
    health = get("/api/health")          # public endpoint, no login needed
except requests.RequestException:
    print("  Backend is not reachable. Run start_all.ps1 first.")
    raise SystemExit(1)
check("Backend running", health["backend"] == "ok")
check("MySQL connected", health["database"] == "ok", health["database"])
check("Simulation connected", health["simulation"] == "running", health["simulation"])
if health["simulation"] != "running":
    print("  Cannot continue without the simulation.")
    raise SystemExit(1)

# Log in as the operator (the other endpoints need a token)
login = requests.post(BASE + "/api/login",
                      json={"username": "operator", "password": "Operator@123"}, timeout=5)
if login.status_code != 200:
    print("  Could not log in as 'operator'. Did you run create_users.py?")
    raise SystemExit(1)
HEADERS["Authorization"] = f"Bearer {login.json()['token']}"
check("Operator login works", True)

print("\n2. Data flows into MySQL (waiting 12 seconds)")
before = get("/api/stats/summary")["readings_saved"]
time.sleep(12)
after = get("/api/stats/summary")["readings_saved"]
check("Traffic readings are being saved", after > before, f"({before} -> {after})")

print("\n3. Emergency vehicle, end to end (up to 60 seconds)")
start = get("/api/stats/summary")["emergency"]
resp = requests.post(BASE + "/api/command/emergency", json={"kind": "ambulance"},
                     headers=HEADERS, timeout=3)
check("Dashboard command accepted", resp.status_code == 200, f"HTTP {resp.status_code}")

t0 = time.time()
seen_emergency_green = None
violations = 0
samples = 0
while time.time() - t0 < 60:
    sig = get("/api/signals")
    samples += 1
    active = [r for r, s in sig["states"].items() if s != "RED"]
    if len(active) > 1:
        violations += 1
    if sig["emergency_mode"] and seen_emergency_green is None:
        seen_emergency_green = time.time() - t0
    if seen_emergency_green is not None and not sig["emergency_mode"]:
        break
    time.sleep(0.1)

check("Emergency road got green", seen_emergency_green is not None,
      f"after {seen_emergency_green:.1f}s" if seen_emergency_green else "")
check("Normal control resumed", not get("/api/signals")["emergency_mode"])
check("Never two non-red signals at once", violations == 0,
      f"({samples} samples, {violations} violations)")

time.sleep(3)   # let the database writer finish
end = get("/api/stats/summary")["emergency"]
check("Event REQUESTED saved", end["requested"] == start["requested"] + 1)
check("Event GREEN_GIVEN saved", end["green_given"] == start["green_given"] + 1)
check("Event CLEARED saved", end["cleared"] == start["cleared"] + 1)

print("\nResult:", f"{sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)