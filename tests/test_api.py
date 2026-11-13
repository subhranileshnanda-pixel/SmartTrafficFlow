import time
import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import security
from traffic_logic import SignalController, SIGNAL_ORDER

USERS = {
    "viewer": (security.hash_password("Viewer@123"), "viewer"),
    "operator": (security.hash_password("Operator@123"), "operator"),
    "admin": (security.hash_password("Admin@123"), "admin"),
}
PASSWORDS = {"viewer": "Viewer@123", "operator": "Operator@123", "admin": "Admin@123"}
KEY = {"X-API-Key": security.SIM_API_KEY}


@pytest.fixture
def client(monkeypatch):
    import database as db

    def fake_fetch(sql, params=None):
        if "FROM users" in sql:
            user = USERS.get(params["u"])
            return [{"username": params["u"], "password_hash": user[0], "role": user[1]}] if user else []
        return []

    monkeypatch.setattr(db, "fetch", fake_fetch)
    for name in ("log_traffic", "log_signal", "log_emergency", "log_audit"):
        monkeypatch.setattr(db, name, lambda *a, **k: None)

    import main
    monkeypatch.setattr(main, "controller", SignalController(SIGNAL_ORDER))
    monkeypatch.setattr(main, "last_sync", None)
    main.failed_logins.clear()
    main.pending_commands.clear()
    return TestClient(main.app)


def auth(client, user):
    token = client.post("/api/login", json={"username": user, "password": PASSWORDS[user]}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- login
def test_login_with_the_right_password(client):
    r = client.post("/api/login", json={"username": "operator", "password": "Operator@123"})
    assert r.status_code == 200 and r.json()["role"] == "operator"


def test_login_with_a_wrong_password_is_rejected(client):
    assert client.post("/api/login", json={"username": "viewer", "password": "nope"}).status_code == 401


def test_unknown_user_is_rejected(client):
    assert client.post("/api/login", json={"username": "ghost", "password": "x"}).status_code == 401


def test_repeated_failures_lock_the_account(client):
    codes = [client.post("/api/login", json={"username": "locktest", "password": f"g{i}"}).status_code
             for i in range(7)]
    assert codes[:5] == [401] * 5 and 429 in codes


def test_dashboard_endpoints_need_a_token(client):
    assert client.get("/api/signals").status_code == 401
    assert client.get("/api/signals", headers=auth(client, "viewer")).status_code == 200


def test_forged_token_is_rejected(client):
    forged = jwt.encode({"sub": "x", "role": "admin", "exp": int(time.time()) + 3600},
                        "a-different-secret-that-is-long-enough-123", algorithm="HS256")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_is_rejected(client):
    old = jwt.encode({"sub": "x", "role": "admin", "exp": int(time.time()) - 10},
                     security.JWT_SECRET, algorithm="HS256")
    assert client.get("/api/signals", headers={"Authorization": f"Bearer {old}"}).status_code == 401


# ---------------------------------------------------------------- roles
def test_viewer_cannot_dispatch_or_read_the_audit_log(client):
    viewer = auth(client, "viewer")
    assert client.post("/api/command/emergency", json={"kind": "ambulance"}, headers=viewer).status_code == 403
    assert client.get("/api/audit", headers=viewer).status_code == 403


def test_operator_can_dispatch_only_when_the_simulation_is_connected(client):
    operator = auth(client, "operator")
    assert client.post("/api/command/emergency", json={"kind": "ambulance"}, headers=operator).status_code == 503

    client.post("/api/sync", json={}, headers=KEY)                    # the simulation connects
    assert client.post("/api/command/emergency", json={"kind": "ambulance"}, headers=operator).status_code == 200

    reply = client.post("/api/sync", json={}, headers=KEY).json()
    assert reply["commands"] == [{"type": "spawn_emergency", "kind": "ambulance"}]


def test_unknown_vehicle_kind_is_rejected(client):
    client.post("/api/sync", json={}, headers=KEY)
    r = client.post("/api/command/emergency", json={"kind": "tank"}, headers=auth(client, "admin"))
    assert r.status_code == 400


def test_only_the_admin_can_change_the_mode(client):
    for user in ("viewer", "operator"):
        assert client.post("/api/mode", json={"mode": "fixed"}, headers=auth(client, user)).status_code == 403
    admin = auth(client, "admin")
    assert client.post("/api/mode", json={"mode": "fixed"}, headers=admin).status_code == 200
    assert client.post("/api/mode", json={"mode": "magic"}, headers=admin).status_code == 400


def test_only_the_admin_can_read_the_audit_log(client):
    assert client.get("/api/audit", headers=auth(client, "operator")).status_code == 403
    assert client.get("/api/audit", headers=auth(client, "admin")).status_code == 200


# ---------------------------------------------------------------- simulation endpoints
def test_sync_needs_the_api_key(client):
    assert client.post("/api/sync", json={}).status_code == 401
    assert client.post("/api/sync", json={}, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/api/sync", json={}, headers=auth(client, "admin")).status_code == 401


def test_sync_returns_exactly_one_active_road(client):
    r = client.post("/api/sync", json={}, headers=KEY).json()
    assert [road for road, s in r["states"].items() if s != "RED"] == [r["current_road"]]


def test_sync_ignores_unknown_roads(client):
    r = client.post("/api/sync", json={"emergency_roads": ["MOON"]}, headers=KEY)
    assert r.status_code == 200


def test_emergency_endpoint_validates_the_road(client):
    assert client.post("/api/emergency", json={"road": "MOON"}, headers=KEY).status_code == 400
    assert client.post("/api/emergency", json={"road": "EAST", "kind": "ambulance"}, headers=KEY).status_code == 200


# ---------------------------------------------------------------- websocket
def test_websocket_rejects_a_bad_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=bad") as ws:
            ws.receive_json()


def test_websocket_streams_live_data_to_a_logged_in_user(client):
    token = auth(client, "viewer")["Authorization"].split()[1]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        data = ws.receive_json()
    assert {"signals", "densities", "forecast", "mode"} <= set(data)