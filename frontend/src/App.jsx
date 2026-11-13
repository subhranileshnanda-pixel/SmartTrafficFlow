import { useState } from "react";
import { useLive } from "./useLive";
import { getAuth, saveAuth, clearAuth, authFetch } from "./auth";   // NEW: authFetch
import Login from "./Login";
import Junction from "./Junction";
import RoadCard from "./RoadCard";
import EmergencyPanel from "./EmergencyPanel";
import HistoryPage from "./HistoryPage";
import AuditPage from "./AuditPage";
import "./App.css";

const ROADS = ["NORTH", "EAST", "SOUTH", "WEST"];
const title = (road) => road.charAt(0) + road.slice(1).toLowerCase();

const MODES = [                                                    // NEW
  { id: "fixed", label: "Fixed timer" },
  { id: "adaptive", label: "Adaptive" },
  { id: "predictive", label: "Predictive (AI)" },
];

function Brand() {
  return (
    <div className="brand">
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
        <rect x="9" y="1" width="12" height="28" rx="6" fill="#0f1c22" stroke="#2e4856" />
        <circle cx="15" cy="7.5" r="3" fill="#ff5a4d" />
        <circle cx="15" cy="15" r="3" fill="#f5c542" />
        <circle cx="15" cy="22.5" r="3" fill="#3ddc84" />
      </svg>
      <div>
        <div className="brand-name">SmartFlow</div>
        <div className="brand-sub">Adaptive traffic and emergency control</div>
      </div>
    </div>
  );
}

function Status({ ok, children }) {
  return (
    <span className="status-chip">
      <span className={`status-dot ${ok ? "dot-ok" : "dot-bad"}`} />
      {children}
    </span>
  );
}

function ModeSwitch({ mode, isAdmin }) {                           // NEW
  const [error, setError] = useState("");

  const change = async (id) => {
    try {
      const res = await authFetch("/api/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: id }),
      });
      setError(res.ok ? "" : "Could not change the mode");
    } catch {
      setError("Cannot reach the backend");
    }
  };

  return (
    <div className="mode-row">
      <span className="muted">Signal control mode</span>
      <div className="mode-switch" role="group" aria-label="Signal control mode">
        {MODES.map((m) => (
          <button
            key={m.id}
            className={`mode-btn ${mode === m.id ? "mode-active" : ""}`}
            disabled={!isAdmin}
            title={isAdmin ? "" : "Only admins can change the mode"}
            onClick={() => change(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState(getAuth());
  const [tab, setTab] = useState("live");

  const logout = () => {
    clearAuth();
    setAuth(null);
    setTab("live");
  };
  const handleLogin = (a) => {
    saveAuth(a);
    setAuth(a);
  };

  const { data, connected } = useLive(auth ? auth.token : null, logout);

  if (!auth) return <Login onLogin={handleLogin} />;

  const canDispatch = auth.role === "operator" || auth.role === "admin";

  const userBar = (
    <div className="user-bar">
      <span className="role-chip">{auth.username}, {auth.role}</span>
      <button className="signout" onClick={logout}>Sign out</button>
    </div>
  );

  if (!connected || !data) {
    return (
      <div className="app">
        <header><Brand />{userBar}</header>
        <div className="banner banner-orange">
          Waiting for the backend. Start it with: uvicorn main:app --reload
        </div>
      </div>
    );
  }

  const { signals, densities, events, sim_online, emergency_roads } = data;
  const mode = data.mode || "adaptive";                          // NEW
  const forecast = data.forecast || {};                            // NEW
  const phaseText = {
    GREEN: "has green",
    YELLOW: "is on yellow",
    ALL_RED: "is clearing, all roads red",
  }[signals.phase];

  return (
    <div className="app">
      <header>
        <Brand />
        <div className="status">
          <Status ok>Backend connected</Status>
          <Status ok={sim_online}>{sim_online ? "Simulation running" : "Simulation not connected"}</Status>
          {userBar}
        </div>
      </header>

      <nav className="tabs">
        <button className={`tab ${tab === "live" ? "tab-active" : ""}`} onClick={() => setTab("live")}>
          Live
        </button>
        <button className={`tab ${tab === "history" ? "tab-active" : ""}`} onClick={() => setTab("history")}>
          History and analytics
        </button>
        {auth.role === "admin" && (
          <button className={`tab ${tab === "audit" ? "tab-active" : ""}`} onClick={() => setTab("audit")}>
            Audit log
          </button>
        )}
      </nav>

      {tab === "live" && (
        <>
          <ModeSwitch mode={mode} isAdmin={auth.role === "admin"} />   {/* NEW */}
          <div className="live">
            <section className="panel junction-panel">
              <div className="panel-head">
                <h2>Junction</h2>
                <span className="muted">
                  {title(signals.current_road)} {phaseText}, planned green {signals.green_time}s
                </span>
              </div>
              <Junction signals={signals} densities={densities} emergencyRoads={emergency_roads} />
            </section>

            <EmergencyPanel signals={signals} events={events} simOnline={sim_online} canDispatch={canDispatch} />

            <section className="panel roads-panel">
              <h2>Roads</h2>
              <div className="road-list">
                {ROADS.map((road) => (
                  <RoadCard
                    key={road}
                    road={road}
                    state={signals.states[road]}
                    isCurrent={signals.current_road === road}
                    phase={signals.phase}
                    timer={signals.timer}
                    emergencyMode={signals.emergency_mode}
                    density={densities[road]}
                    hasEmergency={emergency_roads.includes(road)}
                    forecast={forecast[road]}                      // NEW
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}

      {tab === "history" && <HistoryPage />}
      {tab === "audit" && auth.role === "admin" && <AuditPage />}
    </div>
  );
}