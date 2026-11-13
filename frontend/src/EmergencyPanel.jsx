import { useState } from "react";
import { authFetch } from "./auth";

const BUTTONS = [
  { kind: "ambulance", label: "Ambulance" },
  { kind: "firetruck", label: "Fire Truck" },
  { kind: "police", label: "Police" },
];

export default function EmergencyPanel({ signals, events, simOnline, canDispatch }) {
  const [message, setMessage] = useState("");

  const send = async (kind) => {
    try {
      const res = await authFetch("/api/command/emergency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind }),
      });
      if (res.ok) {
        setMessage("");
      } else {
        const err = await res.json();
        setMessage(err.detail || "Request failed");
      }
    } catch {
      setMessage("Cannot reach the backend");
    }
  };

  let banner = null;
  if (signals.emergency_mode) {
    banner = <div className="banner banner-red">EMERGENCY PRIORITY: {signals.current_road} has green</div>;
  } else if (signals.emergency_queue.length > 0) {
    banner = (
      <div className="banner banner-orange">
        Emergency on {signals.emergency_queue[0]}: clearing the junction safely...
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Emergency Control</h2>
      {banner}

      {canDispatch ? (
        <div className="btn-row">
          {BUTTONS.map((b) => (
            <button key={b.kind} className="btn" disabled={!simOnline} onClick={() => send(b.kind)}>
              {b.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="muted notice">
          You are signed in as a viewer. Only operators and admins can dispatch emergency vehicles.
        </div>
      )}
      {message && <div className="error-text">{message}</div>}

      <h3>Recent Events</h3>
      {events.length === 0 && <div className="muted">No emergency events yet</div>}
      <ul className="event-list">
        {events.map((e, i) => (
          <li key={i}><span className="muted">{e.time}</span> {e.text}</li>
        ))}
      </ul>
    </div>
  );
}