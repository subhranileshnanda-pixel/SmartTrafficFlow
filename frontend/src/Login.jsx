import { useState } from "react";
import { login } from "./auth";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Cannot reach the backend. Is it running?" : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <svg width="40" height="40" viewBox="0 0 30 30" aria-hidden="true">
          <rect x="9" y="1" width="12" height="28" rx="6" fill="#0f1c22" stroke="#2e4856" />
          <circle cx="15" cy="7.5" r="3" fill="#ff5a4d" />
          <circle cx="15" cy="15" r="3" fill="#f5c542" />
          <circle cx="15" cy="22.5" r="3" fill="#3ddc84" />
        </svg>
        <h1>Sign in to SmartFlow</h1>
        <p className="muted">Use the account given to you by the control room admin.</p>

        <label htmlFor="username">Username</label>
        <input id="username" value={username} autoFocus autoComplete="username"
               onChange={(e) => setUsername(e.target.value)} />

        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} autoComplete="current-password"
               onChange={(e) => setPassword(e.target.value)} />

        {error && <div className="error-text">{error}</div>}

        <button className="login-btn" type="submit" disabled={busy || !username || !password}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}