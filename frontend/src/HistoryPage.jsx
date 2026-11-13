import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { useHistory } from "./useHistory";

const ROADS = ["NORTH", "EAST", "SOUTH", "WEST"];
const ROAD_COLORS = { NORTH: "#5aaeff", EAST: "#f5c542", SOUTH: "#3ddc84", WEST: "#d28cff" };
const LEVEL_COLORS = { LOW: "#3ddc84", MEDIUM: "#ffb020", HIGH: "#ff5a4d" };

const tooltipStyle = {
  contentStyle: { background: "#1b303a", border: "1px solid #2e4856", borderRadius: 10 },
  labelStyle: { color: "#eaf0f2" },
  itemStyle: { color: "#eaf0f2" },
};

const fmtTime = (s) => new Date(s).toLocaleTimeString();

function Tile({ label, value, note }) {
  return (
    <div className="tile">
      <div className="tile-value">{value}</div>
      <div className="tile-label">{label}</div>
      {note && <div className="muted">{note}</div>}
    </div>
  );
}

function ChartBox({ title, empty, children }) {
  return (
    <div className="panel">
      <h3 className="chart-title">{title}</h3>
      {empty ? <div className="muted">No data yet. Let the simulation run for a minute.</div>
             : <div style={{ height: 260 }}>{children}</div>}
    </div>
  );
}

export default function HistoryPage() {
  const { data, error } = useHistory();

  if (error) return <div className="banner banner-orange">{error}</div>;
  if (!data) return <div className="muted">Loading history...</div>;

  const { trend, summary, signals, emergencies } = data;
  const em = summary.emergency;
  const kinds = em.by_kind.map((k) => `${k.kind} ${k.count}`).join(", ");

  return (
    <div>
      <div className="tiles">
        <Tile label="Emergencies requested" value={em.requested} note={kinds} />
        <Tile label="Emergencies cleared" value={em.cleared} />
        <Tile label="Avg. time to emergency green"
              value={em.avg_response_sec === null ? "-" : `${em.avg_response_sec}s`} />
        <Tile label="Traffic readings saved" value={summary.readings_saved} />
      </div>

      <div className="chart-grid">
        <ChartBox title="Traffic density over the last 5 minutes" empty={trend.length === 0}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend}>
              <CartesianGrid stroke="#2a3846" strokeDasharray="3 3" />
              <XAxis dataKey="time" stroke="#8b98a6" tick={{ fontSize: 11 }} />
              <YAxis stroke="#8b98a6" tick={{ fontSize: 11 }} />
              <Tooltip {...tooltipStyle} />
              <Legend />
              {ROADS.map((r) => (
                <Line key={r} type="monotone" dataKey={r} stroke={ROAD_COLORS[r]}
                      dot={false} strokeWidth={2} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Time spent at each traffic level (readings)"
                  empty={summary.readings_saved === 0}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary.level_distribution}>
              <CartesianGrid stroke="#2a3846" strokeDasharray="3 3" />
              <XAxis dataKey="road" stroke="#8b98a6" tick={{ fontSize: 12 }} />
              <YAxis stroke="#8b98a6" tick={{ fontSize: 11 }} />
              <Tooltip {...tooltipStyle} />
              <Legend />
              {["LOW", "MEDIUM", "HIGH"].map((l) => (
                <Bar key={l} dataKey={l} stackId="a" fill={LEVEL_COLORS[l]} isAnimationActive={false} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Average green time per road (seconds)"
                  empty={summary.avg_green.every((g) => g.turns === 0)}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary.avg_green}>
              <CartesianGrid stroke="#2a3846" strokeDasharray="3 3" />
              <XAxis dataKey="road" stroke="#8b98a6" tick={{ fontSize: 12 }} />
              <YAxis stroke="#8b98a6" tick={{ fontSize: 11 }} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="avg_green" name="Avg green (s)" fill="#f5c542" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>
      </div>

      <div className="table-grid">
        <div className="panel">
          <h3 className="chart-title">Recent signal changes</h3>
          <table className="table">
            <thead><tr><th>Time</th><th>Road</th><th>Phase</th><th>Duration</th><th>Type</th></tr></thead>
            <tbody>
              {signals.map((s, i) => (
                <tr key={i}>
                  <td>{fmtTime(s.created_at)}</td>
                  <td>{s.road}</td>
                  <td><span className={`phase phase-${s.phase}`}>{s.phase}</span></td>
                  <td>{s.duration_sec}s</td>
                  <td>{s.is_emergency ? "Emergency" : "Normal"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {signals.length === 0 && <div className="muted">No signal changes yet</div>}
        </div>

        <div className="panel">
          <h3 className="chart-title">Recent emergency events</h3>
          <table className="table">
            <thead><tr><th>Time</th><th>Road</th><th>Vehicle</th><th>Event</th></tr></thead>
            <tbody>
              {emergencies.map((e, i) => (
                <tr key={i}>
                  <td>{fmtTime(e.created_at)}</td>
                  <td>{e.road}</td>
                  <td>{e.vehicle_kind || "-"}</td>
                  <td>{e.event_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {emergencies.length === 0 && <div className="muted">No emergency events yet</div>}
        </div>
      </div>
    </div>
  );
}