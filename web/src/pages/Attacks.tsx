import { motion } from "framer-motion";
import {
  Swords,
  Target,
  ShieldAlert,
  Zap,
  KeyRound,
  CheckCircle2,
  XCircle,
  Loader2,
  Skull,
  ArrowRight,
  Radio,
  Copy,
  WifiOff,
  StopCircle,
} from "lucide-react";
import type { AppState, AttackState } from "../hooks/useAppState";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SignalBars } from "../components/ui/SignalBars";
import { cn } from "../lib/utils";

interface AttacksProps {
  state: AppState;
  connected: boolean;
  onSetAttack: (attack: Partial<AttackState>) => void;
  addLog: (level: "info" | "warn" | "error" | "success", msg: string) => void;
  send: (action: string, params?: Record<string, any>) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

interface Stage {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
  state: "idle" | "active" | "success" | "failed" | "locked";
}

function getStages(attack: AttackState, hasTarget: boolean): Stage[] {
  const s = attack.stage;
  return [
    {
      id: "select",
      label: "Select Target",
      description: hasTarget ? "Target acquired" : "Go to Recon to select an AP",
      icon: Target,
      state: !hasTarget ? "idle" : s === "selecting" ? "active" : "success",
    },
    {
      id: "capture",
      label: "Capture Handshake",
      description: "Deauth + 4-way handshake sniff",
      icon: ShieldAlert,
      state:
        s === "capturing"
          ? "active"
          : s === "cracking" || s === "complete"
            ? "success"
            : !hasTarget
              ? "locked"
              : "idle",
    },
    {
      id: "crack",
      label: "Crack Password",
      description: "Dictionary / smart attack engine",
      icon: KeyRound,
      state:
        s === "cracking"
          ? "active"
          : s === "complete"
            ? attack.result?.found
              ? "success"
              : "failed"
            : s === "capturing"
              ? "idle"
              : "locked",
    },
    {
      id: "result",
      label: "Results",
      description: attack.result?.found
        ? `Key: ${attack.result.key}`
        : "Waiting for analysis",
      icon: CheckCircle2,
      state:
        s === "complete" && attack.result?.found
          ? "success"
          : s === "complete"
            ? "failed"
            : "locked",
    },
  ];
}

export function Attacks({
  state,
  connected,
  onSetAttack,
  addLog,
  send,
}: AttacksProps) {
  const hasTarget = !!state.selectedAP;
  const stages = getStages(state.attack, hasTarget);
  const isActive =
    state.attack.stage === "capturing" || state.attack.stage === "cracking";

  const handleStartCapture = () => {
    if (!state.selectedAP) return;
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }
    addLog(
      "info",
      `Starting handshake capture on ${state.selectedAP.essid || "[Hidden]"} (${state.selectedAP.bssid})`
    );
    send("capture_handshake", {
      interface: state.adapter || "",
      bssid: state.selectedAP.bssid,
      channel: state.selectedAP.channel,
    });
  };

  const handleEvilTwin = () => {
    if (!state.selectedAP) return;
    if (!connected) {
      addLog("error", "Backend offline. Start the API server first.");
      return;
    }
    addLog(
      "info",
      `Launching Evil Twin against ${state.selectedAP.essid || "[Hidden]"} (${state.selectedAP.bssid})`
    );
    send("evil_twin", {
      interface: state.adapter || "",
      bssid: state.selectedAP.bssid,
      essid: state.selectedAP.essid,
      channel: state.selectedAP.channel,
    });
  };

  const handleReset = () => {
    onSetAttack({
      stage: hasTarget ? "selecting" : "idle",
      progress: 0,
      status: "Ready",
      result: undefined,
    });
  };

  const handleAbort = () => {
    send("abort_attack");
    addLog("warn", "Abort signal sent. Stopping active attack…");
    onSetAttack({
      stage: "idle",
      progress: 0,
      status: "Aborted",
      result: undefined,
    });
  };

  const handleCopyKey = () => {
    if (state.attack.result?.key) {
      navigator.clipboard.writeText(state.attack.result.key);
      addLog("info", "Key copied to clipboard.");
    }
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
        <motion.div variants={item}>
          <h2 className="text-h2 text-text-primary mb-[2px]">
            Attack Operations
          </h2>
          <p className="text-body text-text-secondary">
            Execute targeted attacks with step-by-step workflow guidance.
          </p>
        </motion.div>

        <div className="grid grid-cols-12 gap-lg">
          {/* Left: Target Info */}
          <motion.div variants={item} className="col-span-5 space-y-lg">
            {/* Target Card */}
            <div className={cn("card", hasTarget && "border-accent-cyan/20")}>
              <div className="card-header">
                <div className="card-title">
                  <Target className="w-5 h-5 text-accent-cyan" />
                  Target
                </div>
                {hasTarget && <span className="badge-cyan">LOCKED</span>}
              </div>

              {hasTarget && state.selectedAP ? (
                <div className="space-y-md">
                  <div>
                    <div className="text-h3 text-text-primary font-bold mb-[2px]">
                      {state.selectedAP.essid || "[Hidden]"}
                    </div>
                    <div className="text-small text-text-muted font-mono">
                      {state.selectedAP.bssid}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-sm">
                    <div className="bg-bg-elevated rounded-tag p-sm text-center">
                      <div className="text-xs text-text-muted">Channel</div>
                      <div className="text-body font-bold text-text-primary">
                        {state.selectedAP.channel}
                      </div>
                    </div>
                    <div className="bg-bg-elevated rounded-tag p-sm text-center">
                      <div className="text-xs text-text-muted">Signal</div>
                      <div className="flex items-center justify-center gap-[4px]">
                        <SignalBars power={state.selectedAP.power} />
                        <span className="text-xs text-text-muted font-mono">
                          {state.selectedAP.power}
                        </span>
                      </div>
                    </div>
                    <div className="bg-bg-elevated rounded-tag p-sm text-center">
                      <div className="text-xs text-text-muted">Clients</div>
                      <div className="text-body font-bold text-accent-purple">
                        {state.selectedAP.clients}
                      </div>
                    </div>
                  </div>

                  {/* Security type */}
                  <div className="flex items-center gap-sm">
                    <Radio className="w-4 h-4 text-text-muted" />
                    <span className="text-small text-text-secondary">
                      {state.selectedAP.privacy}
                    </span>
                    {state.selectedAP.wps && (
                      <span className="badge-danger">WPS</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="py-xl text-center">
                  <Target className="w-10 h-10 text-text-muted mx-auto mb-md opacity-40" />
                  <p className="text-body text-text-muted">
                    No target selected.
                  </p>
                  <p className="text-small text-text-muted mt-[4px]">
                    Go to <strong>Recon</strong> and select an AP to attack.
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Zap className="w-5 h-5 text-accent-cyan" />
                  Actions
                </div>
              </div>
              <div className="space-y-sm">
                {isActive ? (
                  <button
                    className="btn-danger w-full justify-center"
                    onClick={handleAbort}
                  >
                    <StopCircle className="w-4 h-4" />
                    Abort Attack
                  </button>
                ) : (
                  <>
                    <button
                      className="btn-primary w-full justify-center"
                      disabled={!hasTarget}
                      onClick={handleStartCapture}
                    >
                      <Swords className="w-4 h-4" />
                      {state.attack.stage === "complete"
                        ? "Run Again"
                        : "Start Capture & Crack"}
                    </button>

                    <div className="grid grid-cols-2 gap-sm">
                      <button
                        className="btn-danger w-full justify-center"
                        disabled={!hasTarget}
                        onClick={handleEvilTwin}
                      >
                        <Skull className="w-4 h-4" />
                        Evil Twin
                      </button>
                      <button
                        className="btn-ghost w-full justify-center"
                        disabled={state.attack.stage === "idle"}
                        onClick={handleReset}
                      >
                        <WifiOff className="w-4 h-4" />
                        Reset
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </motion.div>

          {/* Right: Workflow + Progress */}
          <motion.div variants={item} className="col-span-7 space-y-lg">
            {/* Workflow Stages */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <ArrowRight className="w-5 h-5 text-accent-cyan" />
                  Attack Workflow
                </div>
              </div>
              <div className="space-y-[2px]">
                {stages.map((stage, idx) => (
                  <WorkflowStep
                    key={stage.id}
                    stage={stage}
                    index={idx}
                    isLast={idx === stages.length - 1}
                  />
                ))}
              </div>
            </div>

            {/* Live Progress */}
            {isActive && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="card border-accent-cyan/20"
              >
                <div className="card-header">
                  <div className="card-title">
                    <Loader2 className="w-5 h-5 text-accent-cyan animate-spin" />
                    Live Progress
                  </div>
                  <span className="badge-cyan scanning-pulse">ACTIVE</span>
                </div>
                <div className="space-y-md">
                  <ProgressBar
                    value={state.attack.progress}
                    variant={
                      state.attack.stage === "capturing" ? "cyan" : "success"
                    }
                    showLabel
                    label={state.attack.status}
                    animated
                  />
                </div>
              </motion.div>
            )}

            {/* Result */}
            {state.attack.stage === "complete" && state.attack.result && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn(
                  "card",
                  state.attack.result.found
                    ? "border-success/30"
                    : "border-danger/30"
                )}
              >
                <div className="flex items-center gap-md p-md">
                  {state.attack.result.found ? (
                    <>
                      <div className="w-14 h-14 rounded-btn bg-success/10 flex items-center justify-center flex-shrink-0">
                        <KeyRound className="w-7 h-7 text-success" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-h3 text-success font-bold">
                          Key Found!
                        </div>
                        <div className="text-h2 font-mono text-text-primary mt-[2px] truncate">
                          {state.attack.result.key}
                        </div>
                      </div>
                      <button
                        className="btn-ghost btn-sm flex-shrink-0"
                        onClick={handleCopyKey}
                        title="Copy key to clipboard"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="w-14 h-14 rounded-btn bg-danger/10 flex items-center justify-center flex-shrink-0">
                        <XCircle className="w-7 h-7 text-danger" />
                      </div>
                      <div>
                        <div className="text-h3 text-danger font-bold">
                          Not Cracked
                        </div>
                        <div className="text-body text-text-secondary mt-[2px]">
                          Key not found in wordlist. Try a larger dictionary or
                          Evil Twin.
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Workflow Step ──────────────────────────── */

function WorkflowStep({
  stage,
  index,
  isLast,
}: {
  stage: Stage;
  index: number;
  isLast: boolean;
}) {
  const Icon = stage.icon;

  const stateStyles = {
    idle: "border-border bg-bg-panel",
    active: "border-accent-cyan/30 bg-accent-cyan/5",
    success: "border-success/30 bg-success/5",
    failed: "border-danger/30 bg-danger/5",
    locked: "border-border-subtle bg-bg-panel/50 opacity-50",
  };

  const iconStyles = {
    idle: "text-text-muted bg-bg-elevated",
    active: "text-accent-cyan bg-accent-cyan/10",
    success: "text-success bg-success/10",
    failed: "text-danger bg-danger/10",
    locked: "text-text-muted bg-bg-elevated/50",
  };

  return (
    <div className="flex items-start gap-md">
      {/* Vertical connector */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className={cn(
            "w-10 h-10 rounded-btn flex items-center justify-center",
            iconStyles[stage.state]
          )}
        >
          {stage.state === "active" ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : stage.state === "success" ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : stage.state === "failed" ? (
            <XCircle className="w-5 h-5" />
          ) : (
            <Icon className="w-5 h-5" />
          )}
        </div>
        {!isLast && (
          <div
            className={cn(
              "w-px h-6",
              stage.state === "success" ? "bg-success/30" : "bg-border"
            )}
          />
        )}
      </div>

      {/* Content */}
      <div
        className={cn(
          "flex-1 p-md rounded-btn border mb-sm transition-all duration-200",
          stateStyles[stage.state]
        )}
      >
        <div className="flex items-center gap-sm">
          <span className="text-xs text-text-muted font-mono">
            {String(index + 1).padStart(2, "0")}
          </span>
          <span className="text-body font-semibold text-text-primary">
            {stage.label}
          </span>
          {stage.state === "active" && (
            <span className="badge-cyan text-xs scanning-pulse">
              IN PROGRESS
            </span>
          )}
        </div>
        <p className="text-small text-text-secondary mt-[2px] ml-[22px]">
          {stage.description}
        </p>
      </div>
    </div>
  );
}
