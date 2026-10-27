import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  StopCircle,
  Play,
  Crosshair,
  Activity,
  CheckCircle2,
  Clock,
  Zap,
  AlertTriangle,
  Target,
} from "lucide-react";
import type { AppState } from "../hooks/useAppState";
import { ProgressBar } from "../components/ui/ProgressBar";
import { ActivityCard } from "../components/ui/ActivityCard";
import { cn } from "../lib/utils";

interface AutoPilotProps {
  state: AppState;
  connected: boolean;
  send: (action: string, params?: Record<string, any>) => void;
  addLog: (level: "info" | "warn" | "error" | "success", msg: string) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function AutoPilot({ state, connected, send, addLog }: AutoPilotProps) {
  const [running, setRunning] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const isAttacking =
    state.attack.stage === "capturing" || state.attack.stage === "cracking";
  const isComplete = state.attack.stage === "complete";

  const crackedCount = useMemo(() => {
    let count = 0;
    for (const h of state.handshakes) {
      if (h.cracked) count++;
    }
    return count;
  }, [state.handshakes]);


  // Timer
  useEffect(() => {
    if (!running || !startTime) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [running, startTime]);

  // Watch attack state for completion
  useEffect(() => {
    if (running && isComplete) {
      setTimeout(() => {
        setRunning(false);
        if (state.attack.result?.found) {
          addLog("success", `Auto-Pilot complete! Key: ${state.attack.result.key}`);
        } else {
          addLog("warn", "Auto-Pilot complete. Key not found in wordlist.");
        }
      }, 0);
    }
  }, [isComplete, running, state.attack.result, addLog]);

  const handleStart = () => {
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }
    if (!state.adapter) {
      addLog("error", "No wireless adapter detected.");
      return;
    }
    setRunning(true);
    setStartTime(Date.now());
    setElapsed(0);
    addLog("info", "Auto-Pilot launched. Autonomous pipeline active.");
    send("auto_pilot", { interface: state.adapter });
  };

  const handleStop = () => {
    send("abort_attack");
    setRunning(false);
    addLog("warn", "Auto-Pilot abort signal sent.");
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const pipelineStatus = running
    ? isAttacking
      ? state.attack.stage === "cracking"
        ? "CRACKING"
        : "CAPTURING"
      : state.scanning
        ? "SCANNING"
        : "INITIALIZING"
    : isComplete
      ? "COMPLETE"
      : "STANDBY";


  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        {/* Header */}
        <motion.div variants={item} className="flex items-center justify-between">
          <div>
            <h2 className="text-h2 text-text-primary mb-[2px] flex items-center gap-sm">
              <Sparkles className="w-6 h-6 text-accent-purple" />
              Auto-Pilot
            </h2>
            <p className="text-body text-text-secondary">
              Fully autonomous scan → capture → crack pipeline.
            </p>
          </div>
          {!running ? (
            <button
              className="btn-primary shadow-glow"
              onClick={handleStart}
              disabled={!connected || !state.adapter}
            >
              <Play className="w-4 h-4" />
              Launch Auto-Pilot
            </button>
          ) : (
            <button className="btn-danger" onClick={handleStop}>
              <StopCircle className="w-4 h-4" />
              Abort Mission
            </button>
          )}
        </motion.div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-lg">
          {/* Main Status Panel */}
          <motion.div variants={item} className="col-span-1 xl:col-span-8 space-y-lg">
            {/* Pipeline Status Card */}
            <div
              className={cn(
                "card border transition-colors",
                running ? "border-accent-purple/30" : "border-border"
              )}
            >
              <div className="card-header">
                <div className="card-title">
                  <Activity className="w-5 h-5 text-accent-purple" />
                  Pipeline Status
                </div>
                <span
                  className={cn(
                    "text-[10px] font-bold uppercase tracking-wider font-mono px-sm py-[2px] rounded-tag border",
                    running
                      ? "bg-accent-purple/10 border-accent-purple/30 text-accent-purple scanning-pulse"
                      : isComplete
                        ? state.attack.result?.found
                          ? "bg-success/10 border-success/30 text-success"
                          : "bg-danger/10 border-danger/30 text-danger"
                        : "bg-bg-elevated border-border text-text-muted"
                  )}
                >
                  {pipelineStatus}
                </span>
              </div>

              {/* Pipeline Stepper */}
              {(() => {
                const stages = [
                  {
                    label: "Scan",
                    desc: "Sweep the airspace",
                    icon: Crosshair,
                    active: running && state.scanning,
                    done:
                      isComplete ||
                      (running && !state.scanning && state.aps.length > 0),
                  },
                  {
                    label: "Target",
                    desc: "Lock the best AP",
                    icon: Target,
                    active: running && !!state.selectedAP && state.attack.stage === "selecting",
                    done:
                      isComplete ||
                      (running && !!state.selectedAP && state.attack.stage !== "selecting"),
                  },
                  {
                    label: "Capture",
                    desc: "Grab the handshake",
                    icon: Zap,
                    active: running && state.attack.stage === "capturing",
                    done: isComplete || (running && state.attack.stage === "cracking"),
                  },
                  {
                    label: "Crack",
                    desc: "Recover the key",
                    icon: CheckCircle2,
                    active: running && state.attack.stage === "cracking",
                    done: isComplete,
                  },
                ];
                return (
                  <ol className="flex items-start mt-md" aria-label="Auto-Pilot pipeline">
                    {stages.map((stage, idx) => {
                      const Icon = stage.done ? CheckCircle2 : stage.icon;
                      const state_ = stage.done
                        ? "done"
                        : stage.active
                          ? "active"
                          : "pending";
                      // connector to the LEFT of this node reflects the prior node's completion
                      const connectorLit = idx > 0 && stages[idx - 1].done;
                      return (
                        <li
                          key={stage.label}
                          className="flex-1 flex flex-col items-center text-center min-w-0"
                          aria-current={stage.active ? "step" : undefined}
                        >
                          {/* node row: left connector · badge · right connector */}
                          <div className="flex items-center w-full">
                            <span
                              className={cn(
                                "h-[2px] flex-1 rounded-full transition-colors",
                                idx === 0
                                  ? "opacity-0"
                                  : connectorLit
                                    ? "bg-success/50"
                                    : "bg-border-subtle"
                              )}
                            />
                            <span
                              className={cn(
                                "relative flex items-center justify-center w-10 h-10 rounded-full border-2 shrink-0 transition-colors",
                                state_ === "active"
                                  ? "border-accent-cyan bg-accent-cyan/10"
                                  : state_ === "done"
                                    ? "border-success/60 bg-success/10"
                                    : "border-border-subtle bg-bg-panel/60"
                              )}
                            >
                              <Icon
                                className={cn(
                                  "w-[18px] h-[18px]",
                                  state_ === "active"
                                    ? "text-accent-cyan"
                                    : state_ === "done"
                                      ? "text-success"
                                      : "text-text-muted"
                                )}
                              />
                              {state_ === "active" && (
                                <span className="absolute inset-0 rounded-full border-2 border-accent-cyan/60 scanning-pulse" />
                              )}
                            </span>
                            <span
                              className={cn(
                                "h-[2px] flex-1 rounded-full transition-colors",
                                idx === stages.length - 1
                                  ? "opacity-0"
                                  : stage.done
                                    ? "bg-success/50"
                                    : "bg-border-subtle"
                              )}
                            />
                          </div>
                          <div className="mt-sm px-[2px]">
                            <div
                              className={cn(
                                "text-small font-bold leading-tight",
                                state_ === "active"
                                  ? "text-accent-cyan"
                                  : state_ === "done"
                                    ? "text-success"
                                    : "text-text-secondary"
                              )}
                            >
                              {stage.label}
                            </div>
                            <div
                              className={cn(
                                "text-xs leading-tight mt-[1px]",
                                state_ === "pending" ? "text-text-muted" : "text-text-secondary"
                              )}
                            >
                              {stage.active ? "In progress…" : stage.done ? "Done" : stage.desc}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                );
              })()}

              {/* Progress */}
              {running && (isAttacking || state.scanning) && (
                <div className="mt-lg space-y-sm">
                  <div className="flex justify-between text-xs font-mono text-text-muted">
                    <span>{state.attack.stage_name || state.attack.status}</span>
                    <span>{state.attack.progress}%</span>
                  </div>
                  <ProgressBar
                    value={state.attack.progress}
                    animated
                    variant={state.attack.stage === "cracking" ? "success" : "cyan"}
                  />
                </div>
              )}

              {/* Result */}
              {isComplete && state.attack.result && (
                <div
                  className={cn(
                    "mt-lg p-md rounded-btn border text-center font-mono",
                    state.attack.result.found
                      ? "bg-success/10 border-success/30"
                      : "bg-danger/10 border-danger/30"
                  )}
                >
                  {state.attack.result.found ? (
                    <div className="space-y-sm">
                      <div className="text-success font-bold text-body">
                        ✅ KEY FOUND
                      </div>
                      <div className="text-h3 font-extrabold text-text-primary bg-black/40 px-md py-sm rounded border border-success/30 select-all">
                        {state.attack.result.key}
                      </div>
                    </div>
                  ) : (
                    <div className="text-danger font-bold flex items-center justify-center gap-sm">
                      <AlertTriangle className="w-4 h-4" />
                      Key not found in dictionary
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Target Info (if acquired) */}
            {state.selectedAP && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
              >
                <div className="card-header">
                  <div className="card-title">
                    <Target className="w-5 h-5 text-accent-cyan" />
                    Current Target
                  </div>
                  <span className="badge-warning text-[10px]">ACQUIRED</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-md mt-sm">
                  <div>
                    <span className="text-[10px] text-text-muted font-mono block">ESSID</span>
                    <span className="text-body font-bold text-text-primary">
                      {state.selectedAP.essid || "[Hidden]"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-text-muted font-mono block">BSSID</span>
                    <span className="text-small font-mono text-text-secondary">
                      {state.selectedAP.bssid}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-text-muted font-mono block">CH / SEC</span>
                    <span className="text-small font-mono text-accent-cyan">
                      CH {state.selectedAP.channel} · {state.selectedAP.privacy}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-text-muted font-mono block">SIGNAL</span>
                    <span
                      className={cn(
                        "text-small font-mono font-bold",
                        state.selectedAP.power >= -55
                          ? "text-success"
                          : state.selectedAP.power >= -75
                            ? "text-warning"
                            : "text-danger"
                      )}
                    >
                      {state.selectedAP.power} dBm
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* Right Sidebar */}
          <motion.div variants={item} className="col-span-1 xl:col-span-4 space-y-lg">
            {/* Metrics */}
            <div className="card">
              <div className="card-header">
                <div className="card-title text-small">
                  <Clock className="w-4 h-4 text-text-muted" />
                  Session Metrics
                </div>
              </div>
              <div className="space-y-sm">
                <MetricRow label="Elapsed" value={formatTime(elapsed)} />
                <MetricRow label="Networks Found" value={String(state.aps.length)} />
                <MetricRow label="Handshakes" value={String(state.handshakes.length)} />
                <MetricRow
                  label="Keys Cracked"
                  value={String(crackedCount)}
                />
              </div>
            </div>

            {/* Activity */}
            <ActivityCard state={state} />
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-[4px] border-b border-border/20 last:border-0">
      <span className="text-small text-text-secondary">{label}</span>
      <span className="text-small text-text-primary font-bold font-mono">{value}</span>
    </div>
  );
}
