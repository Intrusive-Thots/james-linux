import { motion } from "framer-motion";
import {
  Radar,
  FileKey,
  Key,
  Wifi,
  AlertTriangle,
  ArrowRight,
  Crosshair,
  Zap,
  Play,
  Ban,
  X,
  Lock,
  Unlock,
  Radio,
import { useMemo } from "react";
import type { AppState, PageId, AP } from "../hooks/useAppState";
import { RadarScanner } from "../components/ui/RadarScanner";
import { SignalScope } from "../components/ui/SignalScope";
import { ProgressBar } from "../components/ui/ProgressBar";
import { ActivityCard } from "../components/ui/ActivityCard";
import { cn } from "../lib/utils";
interface DashboardProps {
  state: AppState;
  onNavigate: (page: PageId) => void;
  send?: (action: string, params?: Record<string, any>, id?: string) => void;
  onSelectAP?: (ap: AP | null) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function Dashboard({ state, onNavigate, send, onSelectAP }: DashboardProps) {
  const { crackedCount, pendingCount } = useMemo(() => {
    let crackedCount = 0;
    let pendingCount = 0;
    for (const h of state.handshakes) {
      if (h.cracked) crackedCount++;
      else pendingCount++;
    }
    return { crackedCount, pendingCount };
  }, [state.handshakes]);

  const errorCount = useMemo(() => {
    let count = 0;
    for (const l of state.logs) {
      if (l.level === "error") count++;
    }
    return count;
  }, [state.logs]);
  const recentLogs = useMemo(() => state.logs.slice(-8), [state.logs]);

  const activeAttack = state.attack.stage !== "idle";
  const selectedAP = state.selectedAP;

  // Handle Quick Scan Toggle from the Dashboard
  const handleScanToggle = () => {
    if (!send) return;
    if (state.scanning) {
      send("stop_monitor", { interface: state.adapter || "" });
    } else {
      send("scan_aps", { interface: state.adapter || "wlan0", duration: 15 });
    }
  };

  // Launch direct attack on selected AP from Engagement HUD
  const handleLaunchAttack = () => {
    if (!send || !selectedAP || !state.adapter) return;
    send("capture_handshake", {
      interface: state.adapter,
      bssid: selectedAP.bssid,
      channel: selectedAP.channel,
      essid: selectedAP.essid,
    });
  };

  // Abort active attack
  const handleAbortAttack = () => {
    if (!send) return;
    send("abort_attack");
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        {/* Header */}
        <motion.div variants={item} className="flex justify-between items-end border-b border-border/30 pb-md">
          <div>
            <h2 className="text-h2 text-text-primary tracking-tight font-extrabold flex items-center gap-xs">
              <Radio className="w-6 h-6 text-accent-cyan animate-pulse" />
              Tactical Operator Dashboard
            </h2>
            <p className="text-body text-text-secondary">
              Real-time wireless airspace monitoring and autonomous engagement control.
            </p>
          </div>
          <div className="flex gap-sm">
            <button
              onClick={handleScanToggle}
              className={cn(
                "btn btn-sm font-mono border",
                state.scanning
                  ? "bg-danger/10 text-danger border-danger/30 hover:bg-danger/20"
                  : "bg-accent-cyan/10 text-accent-cyan border-accent-cyan/30 hover:bg-accent-cyan/20"
              )}
            >
              {state.scanning ? "Stop Airspace Scan" : "Quick Airspace Scan"}
            </button>
          </div>
        </motion.div>

        {/* Stat Cards Row */}
        <motion.div
          variants={item}
          className="grid grid-cols-4 gap-md"
        >
          <StatCard
            icon={Radar}
            label="Networks Found"
            value={String(state.aps.length)}
            accent="cyan"
            description="Nearby access points"
          />
          <StatCard
            icon={FileKey}
            label="Handshake Vault"
            value={String(state.handshakes.length)}
            accent="purple"
            description={`${pendingCount} pending verification`}
          />
          <StatCard
            icon={Key}
            label="Keys Cracked"
            value={String(crackedCount)}
            accent="green"
            description="Active decrypted networks"
          />
          <StatCard
            icon={AlertTriangle}
            label="System Alerts"
            value={String(errorCount)}
            accent={errorCount > 0 ? "red" : "muted"}
            description={errorCount > 0 ? `${errorCount} active alerts` : "All systems nominal"}
          />
        </motion.div>

        {/* Main Tactical Grid: 3 Columns */}
        <div className="grid grid-cols-12 gap-lg">
          
          {/* Column 1 (span-4): Tactical Engagement HUD */}
          <motion.div variants={item} className="col-span-4 flex flex-col gap-md">
            <div className="card flex-1 flex flex-col justify-between min-h-[360px]">
              <div>
                <div className="card-header mb-md pb-sm">
                  <div className="card-title text-accent-purple">
                    <Crosshair className="w-5 h-5" />
                    Engagement HUD
                  </div>
                  {selectedAP && (
                    <span className="badge-warning text-[10px] animate-pulse">
                      TARGET ACQUIRED
                    </span>
                  )}
                </div>

                {selectedAP ? (
                  <div className="space-y-md">
                    {/* Selected Target Stats */}
                    <div className="bg-bg-surface/50 border border-border/40 rounded-btn p-md space-y-sm">
                      <div className="flex justify-between items-start">
                        <span className="text-small text-text-muted">TARGET ESSID</span>
                        <span className="text-body font-bold text-text-primary">
                          {selectedAP.essid || <span className="italic text-text-muted">&lt;Hidden&gt;</span>}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-small text-text-muted">BSSID / MAC</span>
                        <span className="text-small font-mono text-text-secondary">{selectedAP.bssid}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-small text-text-muted">CHANNEL / ENCR</span>
                        <span className="text-small font-mono text-accent-cyan">
                          CH {selectedAP.channel} · {selectedAP.privacy}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-small text-text-muted">SIGNAL STRENGTH</span>
                        <div className="flex items-center gap-xs">
                          <span className={cn(
                            "text-small font-mono font-bold",
                            selectedAP.power >= -55 ? "text-success" : selectedAP.power >= -75 ? "text-warning" : "text-danger"
                          )}>
                            {selectedAP.power} dBm
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Active Attack Status */}
                    {activeAttack && (
                      <div className="space-y-xs">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-text-secondary uppercase">Stage: {state.attack.stage}</span>
                          <span className="text-accent-cyan animate-pulse">{state.attack.progress}%</span>
                        </div>
                        <ProgressBar value={state.attack.progress} animated variant="cyan" />
                        <div className="text-[11px] font-mono text-text-secondary bg-black/20 p-sm rounded-tag border border-border-subtle truncate">
                          {state.attack.status}
                        </div>
                      </div>
                    )}

                    {/* Crack Results */}
                    {state.attack.stage === "complete" && state.attack.result && (
                      <div className={cn(
                        "p-md rounded-btn border text-center font-mono text-small flex flex-col gap-xs",
                        state.attack.result.found
                          ? "bg-success/10 border-success/30 text-success shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                          : "bg-danger/10 border-danger/30 text-danger"
                      )}>
                        {state.attack.result.found ? (
                          <>
                            <span className="font-bold flex items-center justify-center gap-xs">
                              <Unlock className="w-4 h-4" />
                              KEY DECRYPTED SUCCESSFULLY
                            </span>
                            <span className="text-body font-extrabold bg-black/40 px-md py-xs rounded border border-success/45 mt-xs select-all text-text-primary tracking-wide">
                              {state.attack.result.key}
                            </span>
                          </>
                        ) : (
                          <span className="flex items-center justify-center gap-xs">
                            <Lock className="w-4 h-4" />
                            KEY NOT FOUND IN DICTIONARY
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center text-center py-lg opacity-60">
                    <Crosshair className="w-12 h-12 text-text-muted mb-md animate-pulse-slow" />
                    <p className="text-body text-text-secondary max-w-[200px]">
                      No target selected. Click an AP on the radar scan to lock coordinates.
                    </p>
                  </div>
                )}
              </div>

              {selectedAP && (
                <div className="flex gap-sm mt-md pt-sm border-t border-border/30">
                  {activeAttack ? (
                    <button
                      onClick={handleAbortAttack}
                      className="btn btn-danger w-full shadow-[0_0_12px_rgba(239,68,68,0.2)]"
                    >
                      <Ban className="w-4 h-4" />
                      Abort Attack
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={handleLaunchAttack}
                        className="btn btn-primary flex-1 shadow-glow"
                        disabled={!state.adapter}
                      >
                        <Play className="w-4 h-4" />
                        Attack Target
                      </button>
                      <button
                        onClick={() => onSelectAP && onSelectAP(null)}
                        className="btn btn-secondary px-sm"
                        title="Deselect Target"
                      >
                        <X className="w-4 h-4 text-text-secondary hover:text-text-primary" />
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </motion.div>

          {/* Column 2 (span-4): Radar Airspace Scanner */}
          <motion.div variants={item} className="col-span-4 flex">
            <RadarScanner
              aps={state.aps}
              selectedAP={selectedAP}
              onSelectAP={onSelectAP ? onSelectAP : () => {}}
              scanning={state.scanning}
            />
          </motion.div>

          {/* Column 3 (span-4): Quick Actions & Live Oscilloscope */}
          <motion.div variants={item} className="col-span-4 flex flex-col gap-md">
            {/* Quick Actions */}
            <div className="card flex-1 flex flex-col justify-between">
              <div>
                <div className="card-header pb-sm mb-md">
                  <div className="card-title text-accent-cyan">
                    <Zap className="w-5 h-5" />
                    Quick Actions
                  </div>
                </div>
                <div className="space-y-sm">
                  <ActionButton
                    label="Reconnaissance Scan"
                    description={state.scanning ? "RF analyzer active..." : "Scan environment for nearby targets"}
                    icon={Radar}
                    onClick={() => onNavigate("recon")}
                    active={state.scanning}
                  />
                  <ActionButton
                    label="View Handshake Vault"
                    description={`${pendingCount} pending · ${crackedCount} cracked keys`}
                    icon={FileKey}
                    onClick={() => onNavigate("handshakes")}
                  />
                </div>
              </div>

              {/* Signal oscilloscope widget */}
              <div className="mt-md space-y-xs">
                <span className="text-xs font-mono font-semibold text-text-secondary block">
                  Airspace Signal Activity Scope
                </span>
                <SignalScope active={state.scanning || activeAttack} />
              </div>
            </div>
          </motion.div>
        </div>

        {/* System Status + Activity */}
        <div className="grid grid-cols-12 gap-lg">
          {/* System Status Details */}
          <motion.div variants={item} className="col-span-7 card">
            <div className="card-header mb-md pb-xs">
              <div className="card-title">
                <Wifi className="w-5 h-5 text-accent-cyan" />
                Hardware Status
              </div>
              <span className={cn(
                "badge font-mono",
                state.adapter ? "badge-success" : "badge-danger"
              )}>
                {state.adapter ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
            
            <div className="space-y-sm">
              <StatusRow
                label="Active Wireless Adapter"
                value={state.adapter || "No adapter detected"}
                status={state.adapter ? "ok" : "error"}
              />
              <StatusRow
                label="Adapter Mode"
                value={state.adapterMode?.toUpperCase() || "—"}
                status={state.adapterMode === "monitor" ? "active" : "idle"}
              />
              <StatusRow
                label="Airspace RF Scan Engine"
                value={state.scanning ? "Sweeping Channels" : "Standby"}
                status={state.scanning ? "active" : "idle"}
              />
              <StatusRow
                label="Cracking GPU Engine"
                value={state.attack.stage === "cracking" ? "Hashcat Running" : "Standby"}
                status={state.attack.stage === "cracking" ? "active" : "idle"}
              />
              <StatusRow
                label="Uptime"
                value={formatUptime(state.sessionUptime)}
                status="ok"
              />
            </div>
          </motion.div>

          {/* Activity Card */}
          <motion.div variants={item} className="col-span-5">
            <ActivityCard state={state} />
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Sub-components ──────────────────────────── */

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
  description,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  accent: "cyan" | "purple" | "green" | "red" | "muted";
  description?: string;
}) {
  const colors = {
    cyan: { bg: "bg-accent-cyan/8", text: "text-accent-cyan", icon: "text-accent-cyan", border: "hover:border-accent-cyan/30 hover:shadow-[0_0_15px_rgba(34,211,238,0.12)]" },
    purple: { bg: "bg-accent-purple/8", text: "text-accent-purple", icon: "text-accent-purple", border: "hover:border-accent-purple/30 hover:shadow-[0_0_15px_rgba(139,92,246,0.12)]" },
    green: { bg: "bg-success/8", text: "text-success", icon: "text-success", border: "hover:border-success/30 hover:shadow-[0_0_15px_rgba(16,185,129,0.12)]" },
    red: { bg: "bg-danger/8", text: "text-danger", icon: "text-danger", border: "hover:border-danger/30 hover:shadow-[0_0_15px_rgba(239,68,68,0.12)] animate-pulse" },
    muted: { bg: "bg-bg-elevated", text: "text-text-muted", icon: "text-text-muted", border: "hover:border-border" },
  };
  const c = colors[accent];

  return (
    <div className={cn("card flex items-center gap-md relative overflow-hidden group", c.border)}>
      <div
        className={`w-12 h-12 rounded-btn ${c.bg} flex items-center justify-center flex-shrink-0 transition-transform duration-300 group-hover:scale-105`}
      >
        <Icon className={`w-6 h-6 ${c.icon}`} />
      </div>
      <div>
        <div className={`text-h2 font-extrabold ${c.text}`}>{value}</div>
        <div className="text-small font-semibold text-text-primary tracking-tight">{label}</div>
        {description && <div className="text-[10px] text-text-muted font-medium">{description}</div>}
      </div>
      {/* Background visual gloss glow */}
      <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full bg-white/[0.01] pointer-events-none group-hover:scale-150 transition-transform duration-500" />
    </div>
  );
}

function ActionButton({
  label,
  description,
  icon: Icon,
  onClick,
  variant = "default",
  active = false,
}: {
  label: string;
  description: string;
  icon: React.ElementType;
  onClick: () => void;
  variant?: "default" | "danger";
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-md p-md rounded-btn border transition-all duration-200 text-left group",
        active
          ? "bg-bg-elevated/80 border-accent-cyan/40 shadow-glow"
          : "border-border hover:border-border-hover hover:bg-bg-elevated/40"
      )}
    >
      <div
        className={cn(
          "w-10 h-10 rounded-tag flex items-center justify-center flex-shrink-0 transition-colors duration-250",
          variant === "danger" 
            ? "bg-danger/10 group-hover:bg-danger/20" 
            : active 
              ? "bg-accent-cyan/15" 
              : "bg-bg-elevated group-hover:bg-bg-surface"
        )}
      >
        <Icon
          className={cn(
            "w-5 h-5 transition-colors",
            variant === "danger"
              ? "text-danger"
              : active
                ? "text-accent-cyan"
                : "text-text-muted group-hover:text-accent-cyan"
          )}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-body font-bold text-text-primary group-hover:text-text-primary transition-colors">
          {label}
        </div>
        <div className="text-small text-text-muted truncate">{description}</div>
      </div>
      <ArrowRight className={cn(
        "w-4 h-4 text-text-muted transition-all duration-200",
        active ? "text-accent-cyan translate-x-1" : "group-hover:text-text-secondary group-hover:translate-x-1"
      )} />
    </button>
  );
}

function StatusRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: "ok" | "active" | "idle" | "error";
}) {
  const dotClass = {
    ok: "status-dot-success",
    active: "status-dot-active",
    idle: "status-dot-idle",
    error: "status-dot-danger",
  };

  return (
    <div className="flex items-center justify-between py-[8px] border-b border-border/20 last:border-0">
      <span className="text-body text-text-secondary">{label}</span>
      <div className="flex items-center gap-sm">
        <span className={dotClass[status]} />
        <span className="text-body text-text-primary font-semibold font-mono">{value}</span>
      </div>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
