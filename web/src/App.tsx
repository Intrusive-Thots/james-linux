import { useEffect, useRef, useCallback, useState } from "react";
import { TopNav } from "./components/layout/TopNav";
import { Sidebar } from "./components/layout/Sidebar";
import { StatusBar } from "./components/layout/StatusBar";
import { Dashboard } from "./pages/Dashboard";
import { Recon } from "./pages/Recon";
import { Attacks } from "./pages/Attacks";
import { Handshakes } from "./pages/Handshakes";
import { Logs } from "./pages/Logs";
import { Agent } from "./pages/Agent";
import { SettingsPage } from "./pages/Settings";
import { useAppState } from "./hooks/useAppState";
import { useWebSocket, type WSMessage } from "./hooks/useWebSocket";

const API_WS_URL = import.meta.env.VITE_API_WS_URL || "ws://localhost:8745/ws";

export default function App() {
  const {
    state,
    setPage,
    addLog,
    setAdapter,
    setScanning,
    setAPs,
    selectAP,
    setAttack,
    addHandshake,
    removeHandshake,
  } = useAppState();

  // Agent command response handler
  const [lastAgentResponse, setLastAgentResponse] = useState<{
    response: string;
    ts: number;
  } | null>(null);

  // ── WebSocket connection to JAMES backend ───────────────────
  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      switch (msg.type) {
        case "init":
          if (msg.interfaces?.length > 0) {
            const iface = msg.interfaces[0];
            setAdapter(
              iface.interface || iface.name || "wlan0",
              iface.mode?.toLowerCase() === "monitor" ? "monitor" : "managed"
            );
          }
          addLog("success", "Connected to JAMES backend.");
          break;

        case "log":
          addLog(msg.level, msg.message);
          break;

        case "scan_status":
          setScanning(msg.scanning);
          break;

        case "scan_results": {
          const mapped = (msg.aps || []).map((ap: any) => ({
            bssid: ap.bssid || "",
            essid: ap.essid || ap.ssid || "",
            channel: ap.channel || 0,
            privacy: ap.privacy || ap.encryption || "Unknown",
            power: ap.power || ap.signal || -90,
            clients: ap.clients || ap.num_clients || 0,
            vendor: ap.vendor || "Unknown",
            wps: ap.wps || false,
          }));
          setAPs(mapped);
          addLog(
            "success",
            `Recon complete: ${mapped.length} networks discovered.`
          );
          break;
        }

        case "attack_status":
          setAttack({
            stage: msg.stage as any,
            status: msg.status,
            progress: msg.progress,
            sub_stage: msg.sub_stage,
            total_stages: msg.total_stages,
            stage_name: msg.stage_name,
            ...(msg.result ? { result: msg.result } : {}),
          });
          break;

        case "error":
          addLog("error", msg.message);
          break;

        case "handshake_data":
          if (msg.data) {
            addHandshake({
              id: msg.data.id || `hs-${Date.now()}`,
              essid: msg.data.essid || "",
              bssid: msg.data.bssid || "",
              capturedAt: msg.data.captured_at || new Date().toLocaleString(),
              filePath: msg.data.file_path || "",
              cracked: msg.data.cracked || false,
              key: msg.data.key,
            });
          }
          break;

        case "auto_pilot_target":
          // Auto-select the AP chosen by auto-pilot
          if (msg.target) {
            const ap = {
              bssid: msg.target.bssid || "",
              essid: msg.target.essid || msg.target.ssid || "",
              channel: msg.target.channel || 0,
              privacy: msg.target.privacy || msg.target.encryption || "Unknown",
              power: msg.target.power || msg.target.signal || -90,
              clients: msg.target.clients || msg.target.num_clients || 0,
              vendor: msg.target.vendor || "Unknown",
              wps: msg.target.wps || false,
            };
            selectAP(ap);
          }
          break;

        case "result":
          // Forward result messages for agent commands
          if (msg.action === "agent_command" && msg.data?.response) {
            setLastAgentResponse({ response: msg.data.response, ts: Date.now() });
          }
          break;
      }
    },
    [addLog, setAdapter, setScanning, setAPs, setAttack, addHandshake, selectAP]
  );

  const { connected, send } = useWebSocket({
    url: API_WS_URL,
    onMessage: handleWSMessage,
  });

  // ── Boot log ───────────────────────────────────────────────
  const initialized = useRef(false);
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    addLog("info", "JAMES v2.0 — Tactical UI online.");
  }, [addLog]);

  // ── Global Keyboard Shortcuts ──────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && !e.ctrlKey && !e.shiftKey && !e.metaKey) {
        switch (e.code) {
          case "Digit1":
            e.preventDefault();
            setPage("dashboard");
            break;
          case "Digit2":
            e.preventDefault();
            setPage("recon");
            break;
          case "Digit3":
            e.preventDefault();
            setPage("attacks");
            break;
          case "Digit4":
            e.preventDefault();
            setPage("handshakes");
            break;
          case "Digit5":
            e.preventDefault();
            setPage("agent");
            break;
          case "Digit6":
            e.preventDefault();
            setPage("logs");
            break;
          case "Digit7":
            e.preventDefault();
            setPage("settings");
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setPage]);

  // ── Scan handlers ──────────────────────────────────────────
  const handleStartScan = useCallback(() => {
    if (!state.adapter) {
      addLog("error", "No wireless adapter detected.");
      return;
    }
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }
    send("scan_aps", { interface: state.adapter, duration: 15 });
    addLog("info", `Starting area reconnaissance on ${state.adapter}…`);
  }, [state.adapter, connected, send, addLog]);

  const handleStopScan = useCallback(() => {
    if (connected) {
      send("stop_monitor", { interface: state.adapter || "" });
    }
    setScanning(false);
    setAdapter(state.adapter, "managed");
    addLog("info", "Scan stopped. Restoring managed mode.");
  }, [state.adapter, connected, send, addLog, setAdapter, setScanning]);

  // ── Page rendering ────────────────────────────────────────
  const renderPage = () => {
    switch (state.currentPage) {
      case "dashboard":
        return (
          <Dashboard
            state={state}
            onNavigate={setPage}
            send={send}
            onSelectAP={selectAP}
          />
        );
      case "recon":
        return (
          <Recon
            state={state}
            onSelectAP={selectAP}
            onStartScan={handleStartScan}
            onStopScan={handleStopScan}
            onNavigate={setPage}
          />
        );
      case "attacks":
        return (
          <Attacks
            state={state}
            connected={connected}
            onSetAttack={setAttack}
            addLog={addLog}
            send={send}
          />
        );
      case "handshakes":
        return <Handshakes state={state} onRemoveHandshake={removeHandshake} />;
      case "agent":
        return (
          <Agent
            state={state}
            connected={connected}
            send={send}
            addLog={addLog}
            lastAgentResponse={lastAgentResponse}
          />
        );
      case "logs":
        return <Logs state={state} />;
      case "settings":
        return <SettingsPage />;
      default:
        return (
          <Dashboard
            state={state}
            onNavigate={setPage}
            send={send}
            onSelectAP={selectAP}
          />
        );
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      <TopNav state={state} connected={connected} />

      <div className="flex flex-1 min-h-0">
        <Sidebar currentPage={state.currentPage} onNavigate={setPage} />
        <main className="flex-1 min-w-0 overflow-hidden bg-bg">
          {renderPage()}
        </main>
      </div>

      <StatusBar state={state} />
    </div>
  );
}
