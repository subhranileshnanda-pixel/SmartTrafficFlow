import { API } from "./useLive";

const KEY = "smartflow_auth";

export function getAuth() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY));
  } catch {
    return null;
  }
}

export function saveAuth(auth) {
  sessionStorage.setItem(KEY, JSON.stringify(auth));
}

export function clearAuth() {
  sessionStorage.removeItem(KEY);
}

export async function login(username, password) {
  const res = await fetch(`${API}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Login failed");
  return body;
}

// fetch() that adds the login token. If the token is rejected, sign the user out.
export async function authFetch(path, options = {}) {
  const auth = getAuth();
  const res = await fetch(API + path, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${auth ? auth.token : ""}` },
  });
  if (res.status === 401) {
    clearAuth();
    window.location.reload();
  }
  return res;
}