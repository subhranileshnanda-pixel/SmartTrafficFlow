"""Security checks. Run while SmartFlow is running (start_all.ps1).
Note: the operator test dispatches one real ambulance."""
import time
import jwt
import requests

BASE = "http://127.0.0.1:8000"
results = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    results.append(ok)


def login(user, password):
    return requests.post(BASE + "/api/login", json={"username": user, "password": password}, timeout=5)


def headers(user, password):
    return {"Authorization": f"Bearer {login(user, password).json()['token']}"}


def call(method, path, **kw):
    return requests.request(method, BASE + path, timeout=5, **kw)


try:
    viewer = headers("viewer", "Viewer@123")
    operator = headers("operator", "Operator@123")
    admin = headers("admin", "Admin@123")
except Exception:
    print("Could not log in. Is the backend running, and did you run create_users.py?")
    raise SystemExit(1)

print("\n1. Login protection")
check("Wrong password is rejected (401)", login("viewer", "wrong").status_code == 401)
check("No token is rejected (401)", call("GET", "/api/signals").status_code == 401)
forged = jwt.encode({"sub": "hacker", "role": "admin", "exp": int(time.time()) + 3600},
                    "some-other-secret-that-is-long-enough-123456", algorithm="HS256")
check("Forged admin token is rejected (401)",
      call("GET", "/api/audit", headers={"Authorization": f"Bearer {forged}"}).status_code == 401)

print("\n2. Role permissions")
check("Viewer can read signals (200)", call("GET", "/api/signals", headers=viewer).status_code == 200)
check("Viewer cannot dispatch emergencies (403)",
      call("POST", "/api/command/emergency", headers=viewer, json={"kind": "ambulance"}).status_code == 403)
check("Viewer cannot read the audit log (403)", call("GET", "/api/audit", headers=viewer).status_code == 403)
code = call("POST", "/api/command/emergency", headers=operator, json={"kind": "ambulance"}).status_code
check("Operator can dispatch emergencies", code in (200, 503), f"(HTTP {code})")
check("Operator cannot read the audit log (403)", call("GET", "/api/audit", headers=operator).status_code == 403)
check("Admin can read the audit log (200)", call("GET", "/api/audit", headers=admin).status_code == 200)

print("\n3. Simulation API key")
check("/api/sync without a key is rejected (401)", call("POST", "/api/sync", json={}).status_code == 401)
check("/api/sync with a wrong key is rejected (401)",
      call("POST", "/api/sync", json={}, headers={"X-API-Key": "wrong"}).status_code == 401)
check("An admin token cannot act as the simulation (401)",
      call("POST", "/api/sync", json={}, headers=admin).status_code == 401)

print("\n4. Brute-force protection")
codes = [login("nobody", f"guess{i}").status_code for i in range(8)]
check("Repeated wrong passwords get locked out (429)", 429 in codes)

print("\n5. Audit trail")
actions = {r["action"] for r in call("GET", "/api/audit?limit=100", headers=admin).json()}
check("Failed logins are recorded", "LOGIN_FAILED" in actions)
check("Emergency dispatches are recorded", "EMERGENCY_DISPATCH" in actions)

print("\nResult:", f"{sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)