import {
  Wifi,
  WifiOff,
  Zap,
  Activity,
  Radio,
  Users,
  Clock,
  ScrollText,
} from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import type { AppState } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "../ui/Tooltip";

interface TopNavProps {
  state: AppState;
  connected: boolean;
  onLogsClick?: () => void;
}

export function TopNav({ state, connected, onLogsClick }: TopNavProps) {
  // ⚡ Bolt: Moved sessionUptime to local state.
  // Previously, this timer was in useAppState, causing the entire
  // global state to update and every component to re-render every second.
  // Now, only TopNav re-renders every second.
  const [sessionUptime, setSessionUptime] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSessionUptime((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const hours = Math.floor(sessionUptime / 3600);
  const mins = Math.floor((sessionUptime % 3600) / 60);
  const secs = sessionUptime % 60;
  const uptime = `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

  const totalClients = useMemo(() => {
    let sum = 0;
    for (const ap of state.aps) {
      sum += ap.clients;
    }
    return sum;
  }, [state.aps]);

  const modeLabels: Record<string, string> = {
    phantom: "Phantom orchestrator",
    agent: "Manual Operations",
    auto: "Automation",
    settings: "Configuration",
  };

  const errorCount = useMemo(() => {
    let count = 0;
    for (const l of state.logs) {
      if (l.level === "error") count++;
    }
    return count;
  }, [state.logs]);

  return (
    <header
      className="h-[56px] flex items-center justify-between px-lg border-b border-border flex-shrink-0"
      style={{ background: "#0A0E1A" }}
    >
      {/* ── Zone 1: Brand ────────────────────────────── */}
      <div className="flex items-center gap-md">
        <div className="flex items-center gap-sm">
          <div className="w-8 h-8 rounded-[10px] bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center">
            <Zap className="w-4 h-4 text-accent-cyan" />
          </div>
          <div className="leading-tight">
            <h1 className="text-[14px] font-extrabold tracking-widest text-text-primary leading-none">
              JAMES
            </h1>
            <span className="text-[10px] text-text-muted font-medium">
              v2.0 · {modeLabels[state.currentWorkspace] || "Operations"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Zone 2: Runtime Status ───────────────────── */}
      <div className="flex items-center gap-lg">
        {/* Interface */}
        <div className="flex items-center gap-[6px]">
          {state.adapter ? (
            <Wifi className="w-3.5 h-3.5 text-text-muted" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-danger" />
          )}
          <span className="text-[11px] font-mono text-text-secondary">
            {state.adapter || "No Adapter"}
          </span>
          {state.adapterMode && (
            <span
              className={cn(
                "text-[9px] px-[5px] py-[1px] rounded font-bold uppercase tracking-wider",
                state.adapterMode === "monitor"
                  ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
                  : "bg-bg-elevated text-text-muted border border-border"
              )}
            >
              {state.adapterMode}
            </span>
          )}
        </div>

        <div className="h-4 w-px bg-border" />

        {/* AP Count */}
        <div className="flex items-center gap-[5px]">
          <Radio className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-[11px] font-mono text-text-secondary">
            {state.aps.length} <span className="text-text-muted">APs</span>
          </span>
        </div>

        <div className="h-4 w-px bg-border" />

        {/* Clients */}
        <div className="flex items-center gap-[5px]">
          <Users className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-[11px] font-mono text-text-secondary">
            {totalClients} <span className="text-text-muted">Clients</span>
          </span>
        </div>

        <div className="h-4 w-px bg-border" />

        {/* Session Time */}
        <div className="flex items-center gap-[5px]">
          <Clock className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-[11px] font-mono text-text-secondary">{uptime}</span>
        </div>

        {/* Live indicators */}
        {state.scanning && (
          <>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-[5px]">
              <span className="status-dot-active" />
              <span className="text-[10px] text-accent-cyan font-bold uppercase scanning-pulse">
                SCANNING
              </span>
            </div>
          </>
        )}

        {state.attack.stage !== "idle" && state.attack.stage !== "selecting" && (
          <>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-[5px]">
              <span className="status-dot-danger" />
              <span className="text-[10px] text-danger font-bold uppercase">
                ATTACK
              </span>
            </div>
          </>
        )}
      </div>

      {/* ── Zone 3: Actions ──────────────────────────── */}
      <div className="flex items-center gap-sm">
        {/* Connection status */}
        <div
          className={cn(
            "flex items-center gap-[5px] px-sm py-[4px] rounded-tag border text-[10px] font-semibold",
            connected
              ? "bg-success/5 border-success/20 text-success"
              : "bg-danger/5 border-danger/20 text-danger"
          )}
        >
          <span
            className={cn(
              "w-[6px] h-[6px] rounded-full",
              connected ? "bg-success animate-pulse-slow" : "bg-danger"
            )}
          />
          {connected ? "ONLINE" : "OFFLINE"}
        </div>

        {/* Logs button */}
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="btn-ghost btn-sm relative !h-8 !px-sm"
                onClick={onLogsClick}
              >
                <ScrollText className="w-4 h-4" />
                {errorCount > 0 && (
                  <span className="absolute -top-[2px] -right-[2px] w-[6px] h-[6px] bg-danger rounded-full" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" sideOffset={8} className="bg-bg-panel border-border text-text-primary text-xs flex items-center gap-2">
              View logs <span className="text-[10px] text-text-muted font-mono">Alt+6</span>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Power/Activity indicator */}
        <div className="flex items-center gap-[4px] px-sm py-[4px]">
          <Activity
            className={cn(
              "w-3.5 h-3.5",
              state.scanning || state.attack.stage !== "idle"
                ? "text-accent-cyan animate-pulse"
                : "text-text-muted"
            )}
          />
        </div>
      </div>
    </header>
  );
}
