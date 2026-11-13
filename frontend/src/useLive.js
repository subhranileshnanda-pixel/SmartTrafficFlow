import { useEffect, useState } from "react";

export const API = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/ws";

export function useLive(token, onAuthError) {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!token) return undefined;
    let ws;
    let retry;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => setData(JSON.parse(e.data));
      ws.onclose = (e) => {
        setConnected(false);
        if (e.code === 4401) {          // the backend rejected our token
          onAuthError();
          return;
        }
        if (!closed) retry = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return { data, connected };
}