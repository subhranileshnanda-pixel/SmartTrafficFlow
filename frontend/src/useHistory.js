import { useEffect, useState } from "react";
import { authFetch } from "./auth";

const URLS = [
  "/api/stats/traffic-trend?minutes=5",
  "/api/stats/summary",
  "/api/history/signals?limit=20",
  "/api/history/emergencies?limit=15",
];

export function useHistory(intervalMs = 5000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;

    const load = async () => {
      try {
        const responses = await Promise.all(URLS.map((u) => authFetch(u)));
        if (responses.some((r) => !r.ok)) throw new Error("bad response");
        const [trend, summary, signals, emergencies] = await Promise.all(
          responses.map((r) => r.json())
        );
        if (!stopped) {
          setData({ trend, summary, signals, emergencies });
          setError("");
        }
      } catch {
        if (!stopped) setError("History is not available. Check that the backend and MySQL are running.");
      }
    };

    load();
    const id = setInterval(load, intervalMs);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, error };
}