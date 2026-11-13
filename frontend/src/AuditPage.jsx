import { useEffect, useState } from "react";
import { authFetch } from "./auth";

export default function AuditPage() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;
    const load = async () => {
      try {
        const res = await authFetch("/api/audit?limit=50");
        if (!res.ok) throw new Error();
        const body = await res.json();
        if (!stopped) { setRows(body); setError(""); }
      } catch {
        if (!stopped) setError("The audit log is not available.");
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { stopped = true; clearInterval(id); };
  }, []);

  if (error) return <div className="banner banner-orange">{error}</div>;
  if (!rows) return <div className="muted">Loading audit log...</div>;

  return (
    <div className="panel">
      <h2>Audit log</h2>
      <p className="muted">Who logged in and who dispatched emergency vehicles.</p>
      <table className="table">
        <thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Detail</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{new Date(r.created_at).toLocaleTimeString()}</td>
              <td>{r.username}</td>
              <td>{r.role || "-"}</td>
              <td className={r.action === "LOGIN_FAILED" ? "audit-bad" : ""}>{r.action}</td>
              <td>{r.detail || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <div className="muted">Nothing recorded yet</div>}
    </div>
  );
}