import { useEffect, useRef, useCallback, useState } from "react";

export type WSMessage =
  | { type: "init"; interfaces: any[]; loot: any }
  | { type: "log"; level: "info" | "warn" | "error" | "success"; message: string; timestamp: string }
  | { type: "scan_status"; scanning: boolean }
  | { type: "scan_results"; aps: any[]; count: number }
  | {
      type: "attack_status";
      stage: string;
      status: string;
      progress: number;
      result?: { found: boolean; key?: string };
    }
  | { type: "handshake_data"; data: any }
  | { type: "auto_pilot_target"; target: any }
  | { type: "result"; action: string; id?: string; data: any }
  | { type: "error"; action?: string; id?: string; message: string };

interface UseWebSocketOptions {
  url: string;
  onMessage: (msg: WSMessage) => void;
  reconnectDelay?: number;
}

export function useWebSocket({
  url,
  onMessage,
  reconnectDelay = 3000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log("[WS] Connected to JAMES API");
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage;
        onMessageRef.current(msg);
      } catch (e) {
        console.error("[WS] Failed to parse message:", e);
      }
    };

    ws.onclose = () => {
      console.log("[WS] Disconnected — reconnecting in", reconnectDelay, "ms");
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, reconnectDelay);
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
      ws.close();
    };

    wsRef.current = ws;
  }, [url, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback(
    (action: string, params: Record<string, any> = {}, id?: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action, params, id }));
      } else {
        console.warn("[WS] Not connected, cannot send:", action);
      }
    },
    []
  );

  return { connected, send };
}
