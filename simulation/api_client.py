import os
import threading
import time
import requests
from config import SIGNAL_ORDER

BASE_URL = "http://127.0.0.1:8000"
OFFLINE_AFTER = 2.0


class BackendClient:
    """Talks to the backend in a background thread, so the game never freezes."""

    def __init__(self):
        self.signals = None
        self.last_ok = 0
        self._commands = []                  # commands from the dashboard
        self._lock = threading.Lock()
        self._payload = {
            "densities": {r: {"count": 0, "score": 0, "level": "LOW"} for r in SIGNAL_ORDER},
            "emergency_roads": [],
        }
        self._session = requests.Session()
        self._session.headers["X-API-Key"] = os.getenv("SMARTFLOW_SIM_KEY", "smartflow-sim-key")   # <-- NEW
        threading.Thread(target=self._loop, daemon=True).start()

    def set_snapshot(self, densities, emergency_roads):
        with self._lock:
            self._payload = {"densities": densities, "emergency_roads": list(emergency_roads)}

    def pop_commands(self):
        """Returns and clears the commands received from the dashboard."""
        with self._lock:
            cmds = self._commands
            self._commands = []
        return cmds

    def is_online(self):
        return self.signals is not None and time.time() - self.last_ok < OFFLINE_AFTER

    def _loop(self):
        while True:
            with self._lock:
                payload = self._payload
            try:
                r = self._session.post(f"{BASE_URL}/api/sync", json=payload, timeout=1)
                r.raise_for_status()
                data = r.json()
                with self._lock:
                    self._commands.extend(data.get("commands", []))
                self.signals = data
                self.last_ok = time.time()
            except requests.RequestException:
                pass
            time.sleep(0.1)

    def send_emergency(self, road, kind):
        def _send():
            try:
                self._session.post(f"{BASE_URL}/api/emergency",
                                   json={"road": road, "kind": kind}, timeout=1)
            except requests.RequestException:
                print("Could not reach the backend for the emergency request")
        threading.Thread(target=_send, daemon=True).start()


class RemoteSignals:
    """Looks like the old SignalController to draw.py, but reads the backend's data."""

    def __init__(self, client):
        self.client = client

    def _data(self):
        return self.client.signals if self.client.is_online() else None

    def current_road(self):
        d = self._data()
        return d["current_road"] if d else "-"

    def get_state(self, road):
        d = self._data()
        return d["states"][road] if d else "RED"

    @property
    def phase(self):
        d = self._data()
        return d["phase"] if d else "OFFLINE"

    @property
    def timer(self):
        d = self._data()
        return d["timer"] if d else 0

    @property
    def green_time(self):
        d = self._data()
        return d["green_time"] if d else 0

    @property
    def emergency_mode(self):
        d = self._data()
        return d["emergency_mode"] if d else False

    @property
    def emergency_queue(self):
        d = self._data()
        return d["emergency_queue"] if d else []