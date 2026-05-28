import { useEffect, useRef, useState } from "react";

export function useWebSocket(url: string, onMessage: (msg: any) => void) {
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  useEffect(() => {
    let active = true;

    function connect() {
      // Clean up previous socket if exists
      if (socketRef.current) {
        socketRef.current.close();
      }

      console.log(`Connecting to AgentWatch WebSocket: ${url}`);
      const wsUrl = url.replace("http://", "ws://").replace("https://", "wss://") + "/ws";
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!active) return;
        setConnected(true);
        console.log("AgentWatch WebSocket connected successfully.");
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          console.error("Failed to parse WebSocket message data:", e);
        }
      };

      ws.onclose = () => {
        if (!active) return;
        setConnected(false);
        console.log("AgentWatch WebSocket disconnected. Retrying in 3 seconds...");
        reconnectTimeoutRef.current = setTimeout(() => {
          if (active) connect();
        }, 3000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket connection encountered an error:", err);
        ws.close();
      };
    }

    connect();

    return () => {
      active = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [url]);

  return connected;
}
