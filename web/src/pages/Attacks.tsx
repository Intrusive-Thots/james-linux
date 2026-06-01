import { useState } from "react";
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
  Lock,
  Unlock,
  Bot,
  PlusCircle,
  Check,
} from "lucide-react";
import type { AppState, AttackState } from "../hooks/useAppState";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SignalBars } from "../components/ui/SignalBars";
import { SignalScope } from "../components/ui/SignalScope";
import { cn } from "../lib/utils";

interface AttacksProps {
  state: AppState;
  connected: boolean;
  onSetAttack: (attack: Partial<AttackState>) => void;
  addLog: (level: "info" | "warn" | "error" | "success", msg: string) => void;
  send: (action: string, params?: Record<string, unknown>) => void;
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

const CAPTURE_SUB_STAGES = [
  { id: 1, name: "Initializing Monitor Mode", desc: "Setting wireless adapter into monitor mode, stopping conflicting services." },
  { id: 2, name: "Sniffing Airspace & Target", desc: "Starting background packet capture (airodump-ng) targeting the AP's BSSID and Channel." },
  { id: 3, name: "Sending Client Deauth Burst", desc: "Broadcasting deauth frames to force target clients to disconnect and re-authenticate." },
  { id: 4, name: "Sniffing Handshake Packets", desc: "Waiting for client reconnect to grab the WPA 4-way cryptographic handshake." },
  { id: 5, name: "Verifying WPA Handshake", desc: "Running integrity checks to ensure the captured handshake contains all required key-exchange frames." }
];

const CRACKING_SUB_STAGES = [
  { id: 1, name: "SSID-Targeted Dictionary", desc: "Creating targeted list using SSID name, variations, and common local patterns." },
  { id: 2, name: "Aircrack-ng Straight Wordlist", desc: "Running a fast CPU-based dictionary attack against rockyou.txt." },
  { id: 3, name: "Hashcat WPA-Enhanced Mutation", desc: "Converting handshake to hc22000 format and launching GPU-accelerated rules mutation." },
  { id: 4, name: "John the Ripper CPU Fallback", desc: "Running John the Ripper to test complex candidate passwords using CPU rules." },
  { id: 5, name: "JAMES Common Wi-Fi Patterns", desc: "Testing top 10,000 common Wi-Fi router passwords and ISP defaults." },
  { id: 6, name: "Numeric PIN Brute-Force", desc: "Testing all 8-digit and 10-digit numeric ISP default PIN combinations." }
];

const STORYTELLER_DEFAULTS: Record<string, string> = {
  "Initializing Monitor Mode": "Preparing your wireless hardware. JAMES is putting your interface into RF Monitor mode to capture raw radio signals, and checking for conflicting processes.",
  "Sniffing Airspace & Target": "Creating a targeted radio sniffer. We are locking onto the target AP's channel and filtering out other network traffic to ensure a clean capture.",
  "Sending Client Deauth Burst": "Sending deauthentication packets to connected clients. This forces them to briefly disconnect. When they automatically reconnect, they will exchange cryptographic keys.",
  "Sniffing Handshake Packets": "Listening for the WPA 4-way handshake. We need to grab the key-exchange packets (EAPOL) sent between the client and the router during reconnection.",
  "Verifying WPA Handshake": "Validating the captured handshake. JAMES checks the packet integrity. If valid, we save it in the Handshake Vault and start decrypting.",
  "SSID-targeted wordlist search": "Generating a targeted list of passwords using the target's SSID name. Many router passwords include the name of the network, or default configurations based on it.",
  "Aircrack-ng straight wordlist crack": "Running a high-speed dictionary sweep. We are checking the handshake against a pre-loaded dictionary of standard passwords using a fast CPU-based algorithm.",
  "Hashcat WPA-enhanced mutation crack": "Launching GPU-accelerated rules mutation. We use custom rules to append numbers, swap symbols, and modify candidates, multiplying our password search space.",
  "John the Ripper CPU fallback crack": "Triggering John the Ripper fallback mode. John uses advanced rules to mutate candidate passwords and test them against the handshake.",
  "JAMES common Wi-Fi patterns crack": "Testing Wi-Fi patterns. We are testing the top 5,000 most common default patterns used by wireless router brands (ISPs) worldwide.",
  "Numeric PIN patterns crack": "Trying all common router default PIN configurations (like 8-digit or 10-digit codes), which are extremely common default passwords."
};

export function Attacks({
  state,
  connected,
  onSetAttack,
  addLog,
  send,
}: AttacksProps) {
  const [copied, setCopied] = useState(false);
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
      essid: state.selectedAP.essid,
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

  const getSubStageState = (stageId: number, currentSubStage: number) => {
    if (currentSubStage > stageId) return "completed";
    if (currentSubStage === stageId) return "active";
    return "pending";
  };

  const renderRightColumn = () => {
    const isCracked = state.attack.stage === "complete" && state.attack.result?.found;
    const isFailed = state.attack.stage === "complete" && !state.attack.result?.found;

    if (isCracked) {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", duration: 0.5 }}
          className="card border-success/40 bg-success/5 relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-b from-success/5 via-transparent to-transparent pointer-events-none" />
          
          <div className="flex flex-col items-center text-center p-xl space-y-md relative z-10">
            <motion.div
              initial={{ rotate: -10, scale: 0.8 }}
              animate={{ rotate: 0, scale: 1 }}
              transition={{ delay: 0.1, type: "spring" }}
              className="w-20 h-20 rounded-full bg-success/15 border border-success/35 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.2)]"
            >
              <Unlock className="w-10 h-10 text-success" />
            </motion.div>

            <div className="space-y-xs">
              <h3 className="text-h2 font-extrabold text-success tracking-tight uppercase">
                Airspace Decrypted
              </h3>
              <p className="text-body text-text-secondary max-w-[400px]">
                WPA cryptographic handshake successfully decrypted. Network password acquired.
              </p>
            </div>

            <div className="w-full bg-black/60 border border-success/30 rounded-btn p-lg font-mono relative group">
              <div className="text-[10px] text-success/70 font-semibold uppercase tracking-wider absolute top-2 left-3">
                Cracked Password (WPA-PSK)
              </div>
              <div className="text-h1 font-black text-text-primary tracking-widest mt-md select-all">
                {state.attack.result?.key}
              </div>
              
              <button
                className="absolute right-3 bottom-3 btn btn-sm bg-success/15 hover:bg-success/25 border border-success/30 text-success flex items-center gap-xs"
                onClick={() => {
                  if (state.attack.result?.key) {
                    navigator.clipboard.writeText(state.attack.result.key);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }
                }}
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy Key
                  </>
                )}
              </button>
            </div>

            <div className="flex gap-md w-full justify-center pt-md">
              <div className="text-left bg-bg-elevated/60 border border-border/40 rounded-btn p-md flex-1">
                <span className="text-small text-text-muted block font-semibold">SSID / ESSID</span>
                <span className="text-body font-bold text-text-primary">{state.selectedAP?.essid || "[Hidden]"}</span>
              </div>
              <div className="text-left bg-bg-elevated/60 border border-border/40 rounded-btn p-md flex-1">
                <span className="text-small text-text-muted block font-semibold">BSSID / MAC</span>
                <span className="text-body font-bold text-text-primary font-mono">{state.selectedAP?.bssid}</span>
              </div>
            </div>

            <button
              onClick={handleReset}
              className="btn btn-secondary w-full"
            >
              Return to Operations
            </button>
          </div>
        </motion.div>
      );
    }

    if (isFailed) {
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card border-danger/20 bg-danger/[0.02]"
        >
          <div className="p-xl space-y-lg">
            <div className="flex items-start gap-md">
              <div className="w-12 h-12 rounded-btn bg-danger/15 border border-danger/35 flex items-center justify-center flex-shrink-0 text-danger">
                <XCircle className="w-6 h-6" />
              </div>
              <div className="space-y-xs">
                <h3 className="text-h3 font-extrabold text-text-primary">
                  Dictionary Crack Exhausted
                </h3>
                <p className="text-body text-text-secondary leading-relaxed">
                  The captured WPA handshake was successfully analyzed, but the password was not found in our standard cracking dictionaries.
                </p>
              </div>
            </div>

            <div className="bg-bg-elevated/80 border border-border/40 rounded-btn p-lg space-y-md">
              <div className="flex items-center gap-xs text-accent-cyan">
                <Bot className="w-5 h-5" />
                <span className="text-body font-bold uppercase tracking-wider">Smart Recovery Advisor</span>
              </div>
              <p className="text-small text-text-secondary leading-relaxed">
                Standard dictionary attacks only succeed if the network uses a common word. To crack custom or complex passwords, choose one of the automated alternatives below:
              </p>
              
              <div className="grid grid-cols-1 gap-md pt-sm">
                <div className="border border-border/50 rounded-btn p-md bg-bg-panel/40 flex justify-between items-start gap-md hover:border-danger/30 transition-colors">
                  <div className="space-y-xs">
                    <span className="text-body font-bold text-danger flex items-center gap-xs">
                      <Skull className="w-4 h-4" />
                      Option A: Deploy Rogue Evil Twin AP
                    </span>
                    <p className="text-small text-text-muted leading-relaxed">
                      Creates a clone of the targeted network without a password. Clients are deauthenticated and re-routed to a captive portal login where they input the password. Highly effective against custom passwords!
                    </p>
                  </div>
                  <button
                    onClick={handleEvilTwin}
                    className="btn btn-sm btn-danger whitespace-nowrap self-center shadow-[0_0_12px_rgba(239,68,68,0.2)]"
                  >
                    Deploy AP
                  </button>
                </div>

                <div className="border border-border/50 rounded-btn p-md bg-bg-panel/40 flex justify-between items-start gap-md hover:border-accent-cyan/30 transition-colors">
                  <div className="space-y-xs">
                    <span className="text-body font-bold text-accent-cyan flex items-center gap-xs">
                      <PlusCircle className="w-4 h-4" />
                      Option B: Generate Targeted SSID Dictionary
                    </span>
                    <p className="text-small text-text-muted leading-relaxed">
                      Uses our smart dictionary generator to build a targeted wordlist combining the network name ({state.selectedAP?.essid || "SSID"}), common local ISP default rules, and numeric patterns.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      if (!state.selectedAP?.essid) return;
                      send("agent_command", { command: "generate wordlists " + state.selectedAP.essid });
                      addLog("info", "Generating targeted SSID wordlist for " + state.selectedAP.essid);
                    }}
                    className="btn btn-sm btn-primary whitespace-nowrap self-center shadow-glow"
                  >
                    Generate
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-md pt-sm">
              <button
                onClick={handleReset}
                className="btn btn-secondary flex-1"
              >
                Reset Target
              </button>
            </div>
          </div>
        </motion.div>
      );
    }

    if (isActive) {
      const isCapturing = state.attack.stage === "capturing";
      const stagesList = isCapturing ? CAPTURE_SUB_STAGES : CRACKING_SUB_STAGES;
      const currentSubStage = state.attack.sub_stage || 1;
      const currentStageName = state.attack.stage_name || (isCapturing ? "Initializing Monitor Mode" : "SSID-targeted wordlist search");
      
      const storytellerText = STORYTELLER_DEFAULTS[currentStageName] || state.attack.status || "Executing autonomous sub-stage operation...";

      return (
        <div className="space-y-lg">
          <div className="card border-accent-cyan/20">
            <div className="card-header border-b border-border/30 pb-sm mb-md flex justify-between items-center">
              <div className="card-title text-accent-cyan">
                <Loader2 className="w-5 h-5 animate-spin" />
                {isCapturing ? "Handshake Capture Telemetry" : "Cryptographic Decryption HUD"}
              </div>
              <span className="badge-cyan scanning-pulse font-mono">
                {isCapturing ? "SNIFFING MODE" : "DECRYPTING MODE"}
              </span>
            </div>

            <div className="mb-md">
              <SignalScope active={true} />
            </div>

            <div className="grid grid-cols-2 gap-sm">
              {stagesList.map((stg) => {
                const itemState = getSubStageState(stg.id, currentSubStage);
                return (
                  <div
                    key={stg.id}
                    className={cn(
                      "flex items-center gap-sm p-sm rounded-btn border text-left font-mono transition-all duration-200",
                      itemState === "completed" && "bg-success/5 border-success/20 text-success/80",
                      itemState === "active" && "bg-accent-cyan/10 border-accent-cyan/30 text-text-primary shadow-[0_0_12px_rgba(34,211,238,0.08)]",
                      itemState === "pending" && "bg-bg-panel/40 border-border-subtle text-text-muted opacity-50"
                    )}
                  >
                    <div className="flex-shrink-0">
                      {itemState === "completed" ? (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      ) : itemState === "active" ? (
                        <Loader2 className="w-4 h-4 text-accent-cyan animate-spin" />
                      ) : (
                        <Lock className="w-4 h-4 text-text-muted" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] text-text-muted font-bold leading-none">
                        STEP 0{stg.id}
                      </div>
                      <div className="text-small font-bold truncate mt-[2px]">
                        {stg.name}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card border-accent-purple/20 bg-accent-purple/[0.01]">
            <div className="card-header pb-xs border-b border-border/30 mb-sm">
              <div className="card-title text-accent-purple">
                <Bot className="w-5 h-5 text-accent-purple" />
                Live Storyteller Guide
              </div>
            </div>
            
            <div className="space-y-sm p-xs font-mono">
              <div className="text-small text-text-primary font-bold">
                {currentStageName}
              </div>
              <p className="text-small text-text-secondary leading-relaxed bg-black/35 border border-border/30 rounded-btn p-md">
                {storytellerText}
              </p>
              
              <div className="flex justify-between items-center text-xs text-text-muted pt-xs">
                <span>STAGE {currentSubStage} OF {stagesList.length}</span>
                <span className="animate-pulse">{state.attack.progress}% COMPLETED</span>
              </div>
              <ProgressBar value={state.attack.progress} animated variant={isCapturing ? "cyan" : "success"} />
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="card">
        <div className="card-header border-b border-border/30 pb-sm mb-md">
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
    );
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        <motion.div variants={item}>
          <h2 className="text-h2 text-text-primary mb-[2px]">
            Attack Operations
          </h2>
          <p className="text-body text-text-secondary">
            Execute targeted attacks with step-by-step workflow guidance.
          </p>
        </motion.div>

        <div className="grid grid-cols-12 gap-lg">
          <motion.div variants={item} className="col-span-5 space-y-lg">
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

          <motion.div variants={item} className="col-span-7 space-y-lg">
            {renderRightColumn()}
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

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
