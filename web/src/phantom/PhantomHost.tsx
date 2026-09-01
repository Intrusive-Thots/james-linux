import { useEffect } from "react";
import { PhantomApp } from "./components/PhantomApp";
import { bindJames, type JamesSend } from "./james-bridge";
import "./phantom.css";

export function PhantomHost({
  connected,
  send,
  adapter,
  onBack,
}: {
  connected: boolean;
  send: JamesSend;
  adapter: string | null;
  onBack: () => void;
}) {
  useEffect(() => {
    bindJames({ connected, send, adapter, onBack });
    return () => bindJames(null);
  }, [connected, send, adapter, onBack]);

  return <PhantomApp />;
}
