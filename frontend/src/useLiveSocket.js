import { useEffect, useRef } from "react";

const MAX_BACKOFF_MS = 15000;
const POLICY_VIOLATION = 1008;

/**
 * A WebSocket that reconnects with exponential backoff after drops
 * (server restart, network blip), but stops for good when the server
 * closes with 1008 - that means "not authorized", and retrying would
 * just hammer the server. `onMessage` and `onUnauthorized` are read
 * through refs, so passing new callbacks on every render never tears
 * the connection down.
 */
export default function useLiveSocket(url, { onMessage, onUnauthorized, onReconnect } = {}) {
  const handlers = useRef({});
  handlers.current = { onMessage, onUnauthorized, onReconnect };

  useEffect(() => {
    let ws;
    let retryTimer;
    let attempts = 0;
    let stopped = false;

    function connect() {
      ws = new WebSocket(url());
      ws.onopen = () => {
        if (attempts > 0) handlers.current.onReconnect?.();
        attempts = 0;
      };
      ws.onmessage = (event) => {
        let data = null;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        handlers.current.onMessage?.(data);
      };
      ws.onclose = (event) => {
        if (stopped) return;
        if (event.code === POLICY_VIOLATION) {
          handlers.current.onUnauthorized?.();
          return;
        }
        const delay = Math.min(1000 * 2 ** attempts, MAX_BACKOFF_MS);
        attempts += 1;
        retryTimer = setTimeout(connect, delay);
      };
    }

    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
    // `url` is a stable function from api.js; reconnecting is driven by close events, not re-renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
