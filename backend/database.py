import os
import queue
import threading
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

DB_USER = "root"
DB_PASSWORD = os.getenv("SMARTFLOW_DB_PASSWORD", "nilesh@123")
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "smartflow"

# quote_plus makes passwords with symbols like @ or # safe inside the URL
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_pre_ping=True,
)

# ---------- Background writer ----------
# The API puts records in this queue and returns immediately.
# A separate thread saves them to MySQL, so the signals never wait for the database.
_queue = queue.Queue(maxsize=1000)


def _worker():
    while True:
        sql, params = _queue.get()
        try:
            with engine.begin() as conn:
                conn.execute(text(sql), params)
        except Exception as e:
            print("DB write failed:", e)


threading.Thread(target=_worker, daemon=True).start()


def _save(sql, params):
    try:
        _queue.put_nowait((sql, params))
    except queue.Full:
        print("DB queue full - dropping a record")


def check_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connected: smartflow")
        return True
    except Exception as e:
        print("WARNING: database not available, history will NOT be saved.")
        print("Reason:", e)
        return False


# ---------- Save functions ----------
def log_traffic(densities):
    rows = [
        {"road": road, "c": d["count"], "s": d["score"], "l": d["level"]}
        for road, d in densities.items()
    ]
    _save(
        "INSERT INTO traffic_readings (road, vehicle_count, density_score, level) "
        "VALUES (:road, :c, :s, :l)",
        rows,
    )


def log_signal(road, phase, duration, is_emergency):
    _save(
        "INSERT INTO signal_history (road, phase, duration_sec, is_emergency) "
        "VALUES (:road, :phase, :dur, :emg)",
        {"road": road, "phase": phase, "dur": round(duration, 1), "emg": bool(is_emergency)},
    )


def log_emergency(road, event_type, vehicle_kind=None):
    _save(
        "INSERT INTO emergency_events (road, vehicle_kind, event_type) "
        "VALUES (:road, :kind, :event)",
        {"road": road, "kind": vehicle_kind, "event": event_type},
    )

def log_audit(username, role, action, detail=""):
    _save(
        "INSERT INTO audit_log (username, role, action, detail) VALUES (:u, :r, :a, :d)",
        {"u": (username or "")[:50], "r": role, "a": action, "d": (detail or "")[:200]},
    )


# ---------- Read function (used by the history endpoints) ----------
def fetch(sql, params=None):
    """Returns a list of dicts, or None if the database is not available."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print("DB read failed:", e)
        return None