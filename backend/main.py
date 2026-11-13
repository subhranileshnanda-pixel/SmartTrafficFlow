import asyncio
import time
from collections import deque
from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from traffic_logic import SignalController, SIGNAL_ORDER, MODES
import database as db
from security import (                                            # SECURITY
    verify_password, create_token, decode_token,
    current_user, require_role, require_api_key,
)

app = FastAPI(title="SmartFlow Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.check_connection()

# ---------- Shared state ----------
controller = SignalController(SIGNAL_ORDER)
latest = {
    "densities": {r: {"count": 0, "score": 0, "level": "LOW"} for r in SIGNAL_ORDER},
    "emergency_roads": [],
}
last_time = time.monotonic()
last_traffic_log = 0
TRAFFIC_LOG_INTERVAL = 5
last_sync = None
events = deque(maxlen=8)
pending_commands = []
EMERGENCY_KINDS = ("ambulance", "firetruck", "police")

failed_logins = {}                                                # SECURITY
MAX_FAILED, LOCK_SECONDS = 5, 60                                  # SECURITY


def add_event(text):
    events.appendleft({"time": time.strftime("%H:%M:%S"), "text": text})


def sim_online():
    return last_sync is not None and time.monotonic() - last_sync < 2


class RoadDensity(BaseModel):
    count: int = 0
    score: float = 0
    level: str = "LOW"


class SyncData(BaseModel):
    densities: dict[str, RoadDensity] = {}
    emergency_roads: list[str] = []


class EmergencyRequest(BaseModel):
    road: str
    kind: str = "ambulance"


class CommandRequest(BaseModel):
    kind: str = "ambulance"


class LoginRequest(BaseModel):                                    # SECURITY
    username: str
    password: str


def signal_snapshot():
    return {
        "current_road": controller.current_road(),
        "phase": controller.phase,
        "timer": round(controller.timer, 2),
        "green_time": round(controller.green_time, 1),
        "emergency_mode": controller.emergency_mode,
        "emergency_queue": list(controller.emergency_queue),
        "states": {r: controller.get_state(r) for r in SIGNAL_ORDER},
    }


def live_payload():
    return {
        "signals": signal_snapshot(),
        "densities": latest["densities"],
        "emergency_roads": latest["emergency_roads"],
        "events": list(events),
        "sim_online": sim_online(),
        "mode": controller.mode,
        "forecast": controller.forecaster.snapshot(),
    }


def controller_state():
    return (controller.current_road(), controller.phase, controller.emergency_mode)


def save_changes(before, after):
    old_road, old_phase, old_emg = before
    road, phase, emg = after

    if (road, phase) != (old_road, old_phase):
        db.log_signal(road, phase, controller.timer, emg)

    if emg and not old_emg:
        db.log_emergency(road, "GREEN_GIVEN")
        add_event(f"Emergency green given on {road}")
    if old_emg and not emg:
        db.log_emergency(old_road, "CLEARED")
        add_event(f"Emergency cleared on {old_road}, back to normal")


def query_or_503(sql, params=None):
    rows = db.fetch(sql, params)
    if rows is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return rows


# =====================================================================
# Public endpoints
# =====================================================================
@app.get("/")
async def home():
    return {"message": "SmartFlow backend is running"}


@app.get("/api/health")
def health():
    db_ok = db.fetch("SELECT 1 AS ok") is not None
    return {
        "backend": "ok",
        "database": "ok" if db_ok else "down",
        "simulation": "running" if sim_online() else "not connected",
        "emergency_mode": controller.emergency_mode,
    }


# =====================================================================
# Login                                                      # SECURITY
# =====================================================================
@app.post("/api/login")
def login(req: LoginRequest):
    key = req.username.lower()
    now = time.time()
    recent = [t for t in failed_logins.get(key, []) if now - t < LOCK_SECONDS]
    failed_logins[key] = recent
    if len(recent) >= MAX_FAILED:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in a minute.")

    rows = db.fetch("SELECT username, password_hash, role FROM users WHERE username = :u",
                    {"u": req.username})
    if rows is None:
        raise HTTPException(status_code=503, detail="Database not available, cannot log in")

    user = rows[0] if rows else None
    if user is None or not verify_password(req.password, user["password_hash"]):
        failed_logins[key].append(now)
        db.log_audit(req.username, None, "LOGIN_FAILED")
        raise HTTPException(status_code=401, detail="Wrong username or password")

    failed_logins.pop(key, None)
    db.log_audit(user["username"], user["role"], "LOGIN")
    return {"token": create_token(user["username"], user["role"]),
            "username": user["username"], "role": user["role"]}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return user


@app.get("/api/audit")
def audit(limit: int = 50, user=Depends(require_role("admin"))):
    return query_or_503(
        "SELECT username, role, action, detail, created_at "
        "FROM audit_log ORDER BY id DESC LIMIT :n",
        {"n": min(limit, 500)},
    )


# =====================================================================
# Simulation endpoints: API key required                     # SECURITY
# =====================================================================
@app.post("/api/sync", dependencies=[Depends(require_api_key)])
async def sync(data: SyncData):
    global last_time, last_traffic_log, last_sync
    now = time.monotonic()
    dt = min(now - last_time, 0.5)
    last_time = now
    last_sync = now

    for road in SIGNAL_ORDER:
        if road in data.densities:
            latest["densities"][road] = data.densities[road].model_dump()
    latest["emergency_roads"] = [r for r in data.emergency_roads if r in SIGNAL_ORDER]

    before = controller_state()
    controller.update(dt, latest["densities"], set(latest["emergency_roads"]))
    after = controller_state()
    if after != before:
        save_changes(before, after)

    if now - last_traffic_log >= TRAFFIC_LOG_INTERVAL:
        last_traffic_log = now
        db.log_traffic(latest["densities"])

    commands = pending_commands[:]
    pending_commands.clear()
    return {**signal_snapshot(), "commands": commands}


@app.post("/api/emergency", dependencies=[Depends(require_api_key)])
async def emergency(req: EmergencyRequest):
    road = req.road.upper()
    if road not in SIGNAL_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown road: {req.road}")
    controller.request_emergency(road)
    db.log_emergency(road, "REQUESTED", req.kind)
    add_event(f"{req.kind.title()} requested priority on {road}")
    return {"status": "requested", "road": road, "kind": req.kind}


# =====================================================================
# Dashboard endpoints: login and role required               # SECURITY
# =====================================================================
@app.post("/api/command/emergency")
async def command_emergency(req: CommandRequest, user=Depends(require_role("operator", "admin"))):
    if req.kind not in EMERGENCY_KINDS:
        raise HTTPException(status_code=400, detail="Unknown vehicle kind")
    if not sim_online():
        raise HTTPException(status_code=503, detail="Simulation is not connected")
    pending_commands.append({"type": "spawn_emergency", "kind": req.kind})
    db.log_audit(user["username"], user["role"], "EMERGENCY_DISPATCH", req.kind)
    add_event(f"{req.kind.title()} dispatched by {user['username']}")
    return {"status": "queued", "kind": req.kind}


@app.get("/api/signals", dependencies=[Depends(current_user)])
async def get_signals():
    return signal_snapshot()


@app.get("/api/traffic", dependencies=[Depends(current_user)])
async def get_traffic():
    return latest["densities"]


@app.websocket("/ws")
async def live_feed(websocket: WebSocket, token: str = ""):
    await websocket.accept()
    if decode_token(token) is None:                               # SECURITY
        await websocket.close(code=4401)
        return
    try:
        while True:
            await websocket.send_json(live_payload())
            await asyncio.sleep(0.2)
    except Exception:
        pass


# ---------- History endpoints (login required) ----------
@app.get("/api/history/traffic", dependencies=[Depends(current_user)])
def history_traffic(limit: int = 50):
    return query_or_503(
        "SELECT road, vehicle_count, density_score, level, created_at "
        "FROM traffic_readings ORDER BY id DESC LIMIT :n",
        {"n": min(limit, 500)},
    )


@app.get("/api/history/signals", dependencies=[Depends(current_user)])
def history_signals(limit: int = 50):
    return query_or_503(
        "SELECT road, phase, duration_sec, is_emergency, created_at "
        "FROM signal_history ORDER BY id DESC LIMIT :n",
        {"n": min(limit, 500)},
    )


@app.get("/api/history/emergencies", dependencies=[Depends(current_user)])
def history_emergencies(limit: int = 50):
    return query_or_503(
        "SELECT road, vehicle_kind, event_type, created_at "
        "FROM emergency_events ORDER BY id DESC LIMIT :n",
        {"n": min(limit, 500)},
    )


# ---------- Analytics endpoints (login required) ----------
@app.get("/api/stats/traffic-trend", dependencies=[Depends(current_user)])
def stats_traffic_trend(minutes: int = 5):
    rows = query_or_503(
        "SELECT UNIX_TIMESTAMP(created_at) DIV 5 AS bucket, MIN(created_at) AS t, "
        "road, AVG(density_score) AS score "
        "FROM traffic_readings "
        "WHERE created_at >= NOW() - INTERVAL :m MINUTE "
        "GROUP BY bucket, road ORDER BY bucket",
        {"m": min(max(minutes, 1), 60)},
    )
    points = {}
    for r in rows:
        p = points.setdefault(r["bucket"], {"time": r["t"].strftime("%H:%M:%S")})
        p[r["road"]] = round(float(r["score"]), 1)
    return list(points.values())


@app.get("/api/stats/summary", dependencies=[Depends(current_user)])
def stats_summary():
    levels = query_or_503(
        "SELECT road, level, COUNT(*) AS n FROM traffic_readings GROUP BY road, level")
    level_dist = {r: {"road": r, "LOW": 0, "MEDIUM": 0, "HIGH": 0} for r in SIGNAL_ORDER}
    for row in levels:
        if row["road"] in level_dist:
            level_dist[row["road"]][row["level"]] = int(row["n"])

    greens = query_or_503(
        "SELECT road, ROUND(AVG(duration_sec), 1) AS avg_green, COUNT(*) AS turns "
        "FROM signal_history WHERE phase = 'GREEN' AND is_emergency = FALSE GROUP BY road")
    avg_green = {r: {"road": r, "avg_green": 0, "turns": 0} for r in SIGNAL_ORDER}
    for row in greens:
        if row["road"] in avg_green:
            avg_green[row["road"]] = {"road": row["road"],
                                      "avg_green": float(row["avg_green"]),
                                      "turns": int(row["turns"])}

    event_rows = query_or_503(
        "SELECT event_type, COUNT(*) AS n FROM emergency_events GROUP BY event_type")
    counts = {row["event_type"]: int(row["n"]) for row in event_rows}

    kinds = query_or_503(
        "SELECT vehicle_kind, COUNT(*) AS n FROM emergency_events "
        "WHERE event_type = 'REQUESTED' GROUP BY vehicle_kind")

    resp = query_or_503(
        "SELECT ROUND(AVG(TIMESTAMPDIFF(SECOND, "
        "(SELECT MAX(r.created_at) FROM emergency_events r "
        " WHERE r.event_type = 'REQUESTED' AND r.road = g.road AND r.created_at <= g.created_at), "
        "g.created_at)), 1) AS avg_sec "
        "FROM emergency_events g WHERE g.event_type = 'GREEN_GIVEN'")
    avg_sec = resp[0]["avg_sec"] if resp else None

    total = query_or_503("SELECT COUNT(*) AS n FROM traffic_readings")[0]["n"]

    return {
        "level_distribution": list(level_dist.values()),
        "avg_green": list(avg_green.values()),
        "emergency": {
            "requested": counts.get("REQUESTED", 0),
            "green_given": counts.get("GREEN_GIVEN", 0),
            "cleared": counts.get("CLEARED", 0),
            "avg_response_sec": float(avg_sec) if avg_sec is not None else None,
            "by_kind": [{"kind": r["vehicle_kind"] or "unknown", "count": int(r["n"])} for r in kinds],
        },
        "readings_saved": int(total),
    }

# ---------- AI forecasting and control mode ----------
class ModeRequest(BaseModel):
    mode: str


@app.get("/api/forecast", dependencies=[Depends(current_user)])
def get_forecast():
    return {"mode": controller.mode, "forecast": controller.forecaster.snapshot()}


@app.post("/api/mode")
def set_mode(req: ModeRequest, user=Depends(require_role("admin"))):
    if req.mode not in MODES:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {list(MODES)}")
    controller.mode = req.mode
    db.log_audit(user["username"], user["role"], "MODE_CHANGE", req.mode)
    add_event(f"Control mode set to {req.mode} by {user['username']}")
    return {"mode": controller.mode}    