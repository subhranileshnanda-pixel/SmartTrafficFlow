const LEVEL_COLOR = { LOW: "#3ddc84", MEDIUM: "#ffb020", HIGH: "#ff5a4d" };
const LAMP_COLOR = { RED: "#ff5a4d", YELLOW: "#ffb020", GREEN: "#3ddc84" };

export default function RoadCard({ road, state, isCurrent, phase, timer, emergencyMode, density, hasEmergency, forecast }) {
  const d = density || { count: 0, score: 0, level: "LOW" };
  const barWidth = Math.min(100, (d.score / 12) * 100);
  const name = road.charAt(0) + road.slice(1).toLowerCase();

  let status = state === "RED" ? "Waiting" : state === "YELLOW" ? "Yellow" : "Go";
  if (isCurrent && phase !== "ALL_RED") {
    status += emergencyMode ? ", emergency" : `, ${Math.ceil(timer)}s left`;
  }

  return (
    <div className={`road-row ${hasEmergency ? "road-row-emg" : ""}`}>
      <span
        className="row-lamp"
        style={{ background: LAMP_COLOR[state], boxShadow: `0 0 10px ${LAMP_COLOR[state]}` }}
        title={state}
      />
      <div className="row-main">
        <div className="row-title">
          <b>{name}</b>
          <span className="badge" style={{ background: LEVEL_COLOR[d.level] }}>{d.level}</span>
        </div>
        <div className="row-sub">
          {hasEmergency ? "Emergency vehicle approaching" : status}
        </div>
        <div className="bar">
          <div className="bar-fill" style={{ width: `${barWidth}%`, background: LEVEL_COLOR[d.level] }} />
        </div>
        {forecast && (
          <div className="row-forecast">
            Forecast in 30 s:{" "}
            <b style={{ color: LEVEL_COLOR[forecast.predicted_level] }}>{forecast.predicted_level}</b>
            , {forecast.trend}
          </div>
        )}
      </div>
      <div className="row-nums">
        <div className="row-count">{d.count}</div>
        <div className="muted">vehicles</div>
      </div>
    </div>
  );
}