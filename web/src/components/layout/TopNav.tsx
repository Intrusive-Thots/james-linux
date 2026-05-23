import {
  Wifi,
  WifiOff,
  Shield,
  Activity,
  Bell,
  Settings,
  Zap,
} from "lucide-react";
import type { AppState } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface TopNavProps {
  state: AppState;
  connected: boolean;
}

export function TopNav({ state, connected }: TopNavProps) {
  const hours = Math.floor(state.sessionUptime / 3600);
  const mins = Math.floor((state.sessionUptime % 3600) / 60);
  const secs = state.sessionUptime % 60;
  const uptime = `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

  const pageLabels: Record<string, string> = {
    dashboard: "Dashboard",
    recon: "Reconnaissance",
    attacks: "Attack Operations",
    handshakes: "Handshake Vault",
    agent: "AI Agent",
    logs: "System Logs",
    settings: "Settings",
  };

  return (
    <header
      className="h-[72px] flex items-center justify-between px-lg border-b border-border flex-shrink-0"
      style={{ background: "#0B1020" }}
    >
      {/* Left: Logo + Page */}
      <div className="flex items-center gap-lg">
        <div className="flex items-center gap-sm">
          <div className="w-9 h-9 rounded-btn bg-accent-cyan/10 flex items-center justify-center">
            <Zap className="w-5 h-5 text-accent-cyan" />
          </div>
          <div>
            <h1 className="text-[15px] font-bold tracking-wide text-text-primary leading-tight">
              JAMES
            </h1>
            <span className="text-xs text-text-muted">Wi-Fi Pentesting Agent</span>
          </div>
        </div>

        <div className="h-8 w-px bg-border mx-sm" />

        <span className="text-body font-medium text-text-secondary">
          {pageLabels[state.currentPage] || "Dashboard"}
        </span>
      </div>

      {/* Center: Session Info */}
      <div className="flex items-center gap-xl">
        <div className="flex items-center gap-sm">
          <Activity className="w-4 h-4 text-text-muted" />
          <span className="text-small text-text-secondary font-mono">{uptime}</span>
        </div>

        {state.scanning && (
          <div className="flex items-center gap-sm">
            <span className="status-dot-active" />
            <span className="text-small text-accent-cyan font-medium scanning-pulse">
              SCANNING
            </span>
          </div>
        )}

        {state.attack.stage !== "idle" && state.attack.stage !== "selecting" && (
          <div className="flex items-center gap-sm">
            <span className="status-dot-danger" />
            <span className="text-small text-danger font-medium">
              ATTACK ACTIVE
            </span>
          </div>
        )}
      </div>

      {/* Right: Adapter + Actions */}
      <div className="flex items-center gap-md">
        <div
          className={cn(
            "flex items-center gap-sm px-md py-[6px] rounded-tag border transition-colors",
            connected
              ? "bg-success/5 border-success/20"
              : "bg-danger/5 border-danger/20"
          )}
        >
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              connected ? "bg-success animate-pulse-slow" : "bg-danger"
            )}
          />
          <span className="text-small text-text-secondary font-medium">
            {connected ? "API Connected" : "API Offline"}
          </span>
        </div>

        <div
          className={cn(
            "flex items-center gap-sm px-md py-[6px] rounded-tag border transition-colors",
            state.adapter
              ? "bg-bg-elevated border-border"
              : "bg-danger/5 border-danger/20"
          )}
        >
          {state.adapter ? (
            <Wifi className="w-4 h-4 text-text-muted" />
          ) : (
            <WifiOff className="w-4 h-4 text-danger" />
          )}
          <span className="text-small text-text-secondary">
            {state.adapter || "No Adapter"}
          </span>
          {state.adapterMode && (
            <span
              className={cn(
                "text-[10px] px-[6px] py-[1px] rounded font-bold uppercase tracking-wider",
                state.adapterMode === "monitor"
                  ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
                  : "bg-bg-elevated text-text-muted border border-border"
              )}
            >
              {state.adapterMode.toUpperCase()}
            </span>
          )}
        </div>

        <button className="btn-ghost btn-sm relative">
          <Bell className="w-4 h-4" />
          {state.logs.filter((l) => l.level === "error").length > 0 && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-danger rounded-full" />
          )}
        </button>

        <button className="btn-ghost btn-sm">
          <Shield className="w-4 h-4" />
        </button>

        <button className="btn-ghost btn-sm">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
