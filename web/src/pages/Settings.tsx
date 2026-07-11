import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Wifi,
  Shield,
  Palette,
  Bell,
  Package,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Stethoscope,
  Wrench,
  Sliders,
  Monitor,
  HardDrive,
  Clock,
  RefreshCw,
  Loader2,
} from "lucide-react";
import type { SubPageId, SettingsSubPage } from "../hooks/useAppState";
import { cn } from "../lib/utils";

interface SettingsPageProps {
  activePanel?: SubPageId;
  state: any;
  setAdapter: (adapter: string | null, mode?: "managed" | "monitor" | null) => void;
  send: (action: string, params?: Record<string, any>, id?: string) => void;
  connected: boolean;
}

export function SettingsPage({
  activePanel = "general",
  state,
  setAdapter,
  send,
  connected,
}: SettingsPageProps) {
  const panel = activePanel as SettingsSubPage;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        <div>
          <h2 className="text-h2 text-text-primary mb-[2px]">Settings</h2>
          <p className="text-body text-text-secondary">
            Configure JAMES agent preferences, interfaces, and system diagnostics.
          </p>
        </div>

        {/* Content panel — one at a time */}
        <div className="card min-h-[400px]">
          {panel === "general" && <GeneralPanel />}
          {panel === "interfaces" && (
            <InterfacesPanel
              state={state}
              setAdapter={setAdapter}
              send={send}
              connected={connected}
            />
          )}
          {panel === "dependencies" && <DependenciesPanel />}
          {panel === "diagnostics" && <DiagnosticsPanel />}
          {panel === "advanced" && <AdvancedPanel />}
        </div>
      </div>
    </motion.div>
  );
}

/* ── Panel: General ─────────────────────────────────────── */
function GeneralPanel() {
  return (
    <div className="space-y-lg">
      <PanelHeader
        icon={Sliders}
        title="General Settings"
        description="Application preferences and UI configuration."
      />
      <div className="grid grid-cols-2 gap-lg">
        <SettingsGroup
          icon={Palette}
          title="Appearance"
          items={[
            { label: "Theme", value: "Dark Tactical" },
            { label: "Animations", value: "Enabled" },
            { label: "Compact Mode", value: "Disabled" },
          ]}
        />
        <SettingsGroup
          icon={Bell}
          title="Notifications"
          items={[
            { label: "Sound alerts", value: "Disabled" },
            { label: "Desktop notifications", value: "Enabled" },
            { label: "Auto-report", value: "Enabled" },
          ]}
        />
        <SettingsGroup
          icon={Monitor}
          title="Display"
          items={[
            { label: "Log retention", value: "500 entries" },
            { label: "Auto-scroll logs", value: "Enabled" },
            { label: "Show timestamps", value: "Enabled" },
          ]}
        />
        <SettingsGroup
          icon={Clock}
          title="Session"
          items={[
            { label: "Session timeout", value: "Never" },
            { label: "Auto-save state", value: "Enabled" },
            { label: "Startup page", value: "Dashboard" },
          ]}
        />
      </div>
    </div>
  );
}

/* ── Panel: Interfaces ──────────────────────────────────── */
interface InterfacesPanelProps {
  send: (action: string, params?: Record<string, any>, id?: string) => void;
  connected: boolean;
  state: any;
  setAdapter: (adapter: string | null, mode?: "managed" | "monitor" | null) => void;
}

function InterfacesPanel({ send, connected, state, setAdapter }: InterfacesPanelProps) {
  const [interfaces, setInterfaces] = useState<{ name: string; mode: string }[]>([]);
  const [auditData, setAuditData] = useState<Record<string, {
    driver: string;
    chipset: string;
    monitor_supported: boolean;
    score: string | number;
    reason: string;
  }>>({});
  const [netGuardEnabled, setNetGuardEnabled] = useState<boolean>(true);
  const [loading, setLoading] = useState(true);
  const [togglingInterface, setTogglingInterface] = useState<string | null>(null);
  const [actionResults, setActionResults] = useState<Record<string, { success?: boolean; error?: string }>>({});

  const fetchInterfaces = async () => {
    try {
      const res = await fetch("/api/interfaces");
      if (res.ok) {
        const data = await res.json();
        const normalized = data.map((iface: any) => ({
          name: iface.interface || iface.name || "unknown",
          mode: iface.mode || "unknown"
        }));
        setInterfaces(normalized);
      }
    } catch (err) {
      console.error("Failed to fetch interfaces:", err);
    }
  };

  const fetchAudit = async () => {
    try {
      const res = await fetch("/api/interfaces/audit");
      if (res.ok) {
        const data = await res.json();
        setAuditData(data);
      }
    } catch (err) {
      console.error("Failed to fetch hardware audit:", err);
    }
  };

  const fetchNetGuardStatus = useCallback(async () => {
    if (!send) return;
    try {
      await new Promise((resolve, reject) => {
        const id = Math.random().toString(36).substring(2, 11);
        const handleResult = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            setNetGuardEnabled(!!msg.data?.enabled);
            resolve(msg.data);
          }
        };
        const handleError = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            reject();
          }
        };
        const cleanup = () => {
          window.removeEventListener("ws_result", handleResult);
          window.removeEventListener("ws_error", handleError);
        };
        window.addEventListener("ws_result", handleResult);
        window.addEventListener("ws_error", handleError);
        send("get_net_guard_status", {}, id);
        setTimeout(() => {
          cleanup();
          reject();
        }, 5000);
      });
    } catch (err) {
      // silent fallback
    }
  }, [send]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchInterfaces(),
      fetchAudit(),
    ]);
    if (connected) {
      await fetchNetGuardStatus();
    }
    setLoading(false);
  }, [connected, fetchNetGuardStatus]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Sync NetGuard status when connected state changes
  useEffect(() => {
    if (connected) {
      fetchNetGuardStatus();
    }
  }, [connected, fetchNetGuardStatus]);

  const handleToggleMode = async (ifaceName: string, currentMode: string) => {
    if (!send || !connected) return;
    setTogglingInterface(ifaceName);
    setActionResults(prev => ({ ...prev, [ifaceName]: {} }));
    
    const targetAction = currentMode.toLowerCase() === "monitor" ? "stop_monitor" : "start_monitor";
    
    try {
      await new Promise((resolve, reject) => {
        const id = Math.random().toString(36).substring(2, 11);
        
        const handleResult = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            if (msg.data?.error) {
              reject(new Error(msg.data.error));
            } else {
              resolve(msg.data);
            }
          }
        };

        const handleError = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            reject(new Error(msg.message || "Action failed"));
          }
        };

        const cleanup = () => {
          window.removeEventListener("ws_result", handleResult);
          window.removeEventListener("ws_error", handleError);
        };

        window.addEventListener("ws_result", handleResult);
        window.addEventListener("ws_error", handleError);

        send(targetAction, { interface: ifaceName }, id);
        
        setTimeout(() => {
          cleanup();
          reject(new Error("Operation timed out"));
        }, 35000);
      });
      
      const newMode = currentMode.toLowerCase() === "monitor" ? "managed" : "monitor";
      setActionResults(prev => ({ ...prev, [ifaceName]: { success: true } }));
      await fetchInterfaces();
      if (setAdapter) {
        setAdapter(ifaceName, newMode as any);
      }
    } catch (error: any) {
      console.error("Mode toggle failed:", error);
      setActionResults(prev => ({
        ...prev,
        [ifaceName]: { success: false, error: error.message || "Failed to switch mode" }
      }));
    } finally {
      setTogglingInterface(null);
    }
  };

  const handleToggleNetGuard = async (newEnabled: boolean) => {
    if (!send || !connected) return;
    try {
      await new Promise((resolve, reject) => {
        const id = Math.random().toString(36).substring(2, 11);
        const handleResult = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            resolve(msg.data);
          }
        };
        const handleError = (e: Event) => {
          const msg = (e as CustomEvent).detail;
          if (msg.id === id) {
            cleanup();
            reject(new Error(msg.message || "Action failed"));
          }
        };
        const cleanup = () => {
          window.removeEventListener("ws_result", handleResult);
          window.removeEventListener("ws_error", handleError);
        };
        window.addEventListener("ws_result", handleResult);
        window.addEventListener("ws_error", handleError);
        send("toggle_net_guard", { enabled: newEnabled }, id);
        setTimeout(() => {
          cleanup();
          reject(new Error("Timeout toggling NetworkGuard"));
        }, 5000);
      });
      setNetGuardEnabled(newEnabled);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-lg">
      <div className="flex items-center justify-between">
        <PanelHeader
          icon={Wifi}
          title="Interface Settings"
          description="Control default adapters, toggle monitor/managed modes, and override network protection."
        />
        <button
          onClick={refreshAll}
          disabled={loading}
          className="btn btn-secondary flex items-center gap-xs px-md py-sm"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          <span>Refresh</span>
        </button>
      </div>

      {/* NetworkGuard self-protection status panel */}
      <div className={cn(
        "border rounded-btn p-lg transition-all duration-300",
        netGuardEnabled 
          ? "bg-emerald-950/10 border-emerald-500/20 text-emerald-300"
          : "bg-amber-950/15 border-amber-500/20 text-amber-300"
      )}>
        <div className="flex items-start justify-between gap-md">
          <div className="space-y-xs">
            <div className="flex items-center gap-xs">
              <Shield className={cn("w-5 h-5", netGuardEnabled ? "text-emerald-400" : "text-amber-400")} />
              <h3 className="font-bold text-text-primary">
                NetworkGuard Self-Protection: {netGuardEnabled ? "ACTIVE" : "BYPASSED"}
              </h3>
            </div>
            <p className="text-body-small text-text-secondary leading-relaxed max-w-3xl">
              {netGuardEnabled 
                ? "Prevents JAMES from disabling active network adapters providing the current admin control session or severing local connectivity. Monitor mode switches on active adapters will be blocked."
                : "DANGER Mode. NetworkGuard safety checks are disabled. You can toggle any interface, but putting your primary connection interface into monitor mode will kill your WebSocket connection instantly."}
            </p>
          </div>
          <button
            onClick={() => handleToggleNetGuard(!netGuardEnabled)}
            className={cn(
              "btn px-md py-sm font-semibold rounded-btn transition-colors duration-200",
              netGuardEnabled 
                ? "bg-emerald-600 hover:bg-emerald-700 text-white" 
                : "bg-amber-600 hover:bg-amber-700 text-black"
            )}
          >
            {netGuardEnabled ? "Bypass Protection" : "Enable Protection"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-xl space-y-md">
          <Loader2 className="w-8 h-8 text-accent-cyan animate-spin" />
          <span className="text-body text-text-secondary">Auditing system wireless hardware...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
          {/* Detected Interface cards */}
          <div className="space-y-md">
            <h3 className="text-small font-bold text-text-primary uppercase tracking-wider">
              Detected Interfaces
            </h3>
            {interfaces.length === 0 ? (
              <div className="bg-bg-elevated/20 border border-border-subtle rounded-btn p-lg text-center">
                <AlertTriangle className="w-8 h-8 text-text-muted mx-auto mb-sm" />
                <span className="text-body text-text-secondary">No wireless interfaces detected on this system.</span>
              </div>
            ) : (
              interfaces.map((iface) => {
                const audit = auditData[iface.name] || {} as any;
                const isToggling = togglingInterface === iface.name;
                const result = actionResults[iface.name] || {};
                const isMonitor = iface.mode.toLowerCase() === "monitor";

                return (
                  <div key={iface.name} className="bg-bg-elevated/20 border border-border-subtle rounded-btn p-md space-y-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-md">
                        <div className={cn(
                          "w-10 h-10 rounded-full flex items-center justify-center",
                          isMonitor ? "bg-cyan-500/10 text-cyan-400" : "bg-text-muted/10 text-text-secondary"
                        )}>
                          {isMonitor ? <Shield className="w-5 h-5" /> : <Wifi className="w-5 h-5" />}
                        </div>
                        <div>
                          <div className="flex items-center gap-sm">
                            <span className="text-body font-bold text-text-primary">{iface.name}</span>
                            {state?.adapter === iface.name && (
                              <span className="text-[10px] bg-accent-cyan/15 text-accent-cyan px-[6px] py-[2px] rounded font-bold uppercase tracking-wider">
                                Default
                              </span>
                            )}
                          </div>
                          <span className="text-body-small text-text-secondary">
                            Mode: <span className="font-bold text-text-primary capitalize">{iface.mode}</span>
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleToggleMode(iface.name, iface.mode)}
                        disabled={isToggling || !connected}
                        className={cn(
                          "btn flex items-center gap-xs px-md py-sm font-semibold rounded-btn transition-all duration-200 min-w-[130px] justify-center",
                          isMonitor 
                            ? "bg-bg-elevated border border-border-subtle text-text-primary hover:bg-bg-elevated/80"
                            : "bg-accent-cyan text-black hover:bg-cyan-400"
                        )}
                      >
                        {isToggling ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : isMonitor ? (
                          "Managed Mode"
                        ) : (
                          "Monitor Mode"
                        )}
                      </button>
                    </div>

                    {/* Inline compatibility details */}
                    {audit.chipset && (
                      <div className="grid grid-cols-2 gap-sm pt-xs border-t border-border-subtle/50 text-body-small">
                        <div>
                          <span className="text-text-muted">Chipset:</span>
                          <span className="text-text-primary ml-xs truncate block font-mono">{audit.chipset}</span>
                        </div>
                        <div>
                          <span className="text-text-muted">Driver:</span>
                          <span className="text-text-primary ml-xs truncate block font-mono">{audit.driver}</span>
                        </div>
                      </div>
                    )}

                    {/* Action result alerts (NetworkGuard errors etc) */}
                    {result.error && (
                      <div className="bg-red-950/20 border border-red-500/30 text-red-400 p-sm rounded text-body-small flex items-start gap-xs">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-[2px]" />
                        <span>{result.error}</span>
                      </div>
                    )}
                    {result.success && (
                      <div className="bg-emerald-950/20 border border-emerald-500/30 text-emerald-400 p-sm rounded text-body-small flex items-center gap-xs">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>Successfully updated interface mode.</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Compatibility Audit Summary */}
          <div className="space-y-md">
            <h3 className="text-small font-bold text-text-primary uppercase tracking-wider">
              Compatibility Diagnostic
            </h3>
            <div className="bg-bg-elevated/20 border border-border-subtle rounded-btn p-md space-y-md">
              <div className="flex items-center gap-xs">
                <Sliders className="w-5 h-5 text-accent-cyan" />
                <h4 className="font-bold text-text-primary">Pentesting Performance Audit</h4>
              </div>
              <p className="text-body-small text-text-secondary">
                Audit metrics show system interfaces capable of monitor mode and packet injection. Ensure you use supported chipsets (e.g. Atheros, Ralink, Realtek RTL8812AU).
              </p>

              <div className="space-y-sm">
                {Object.keys(auditData).length === 0 ? (
                  <div className="text-center py-sm text-body-small text-text-muted">
                    No hardware data found.
                  </div>
                ) : (
                  Object.entries(auditData).map(([iface, details]) => {
                    const isGreen = details.score === "green" || (typeof details.score === "number" && details.score >= 80);
                    const isOrange = details.score === "orange" || (typeof details.score === "number" && details.score >= 50 && details.score < 80);
                    
                    const displayLabel = typeof details.score === "number"
                      ? `${details.score}%`
                      : details.score === "green"
                      ? "Excellent"
                      : details.score === "orange"
                      ? "Moderate"
                      : "Poor";
                      
                    const barWidth = typeof details.score === "number"
                      ? `${details.score}%`
                      : details.score === "green"
                      ? "100%"
                      : details.score === "orange"
                      ? "60%"
                      : "20%";

                    return (
                      <div key={iface} className="bg-bg-elevated/10 border border-border-subtle/50 rounded p-sm space-y-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-text-primary text-body-small">{iface}</span>
                          <span className={cn(
                            "text-xs px-2 py-0.5 rounded font-bold uppercase tracking-wide",
                            isGreen 
                              ? "bg-emerald-500/10 text-emerald-400" 
                              : isOrange 
                              ? "bg-amber-500/10 text-amber-400" 
                              : "bg-red-500/10 text-red-400"
                          )}>
                            Compatibility: {displayLabel}
                          </span>
                        </div>
                        
                        {/* Bar indicator */}
                        <div className="w-full bg-bg-elevated h-1.5 rounded-full overflow-hidden">
                          <div 
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              isGreen ? "bg-emerald-500" : isOrange ? "bg-amber-500" : "bg-red-500"
                            )} 
                            style={{ width: barWidth }} 
                          />
                        </div>

                        <div className="text-body-small text-text-secondary font-mono leading-snug">
                          {details.reason}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Panel: Dependencies ────────────────────────────────── */
function DependenciesPanel() {
  const deps = [
    { name: "aircrack-ng", status: "installed" as const, version: "1.7" },
    { name: "hashcat", status: "installed" as const, version: "6.2.6" },
    { name: "hcxdumptool", status: "installed" as const, version: "6.3.1" },
    { name: "hcxpcapngtool", status: "installed" as const, version: "6.3.1" },
    { name: "john", status: "installed" as const, version: "1.9.0" },
    { name: "hostapd-mana", status: "missing" as const, version: "—" },
    { name: "dnsmasq", status: "installed" as const, version: "2.89" },
    { name: "macchanger", status: "installed" as const, version: "1.7.0" },
  ];

  let installed = 0;
  let missing = 0;
  for (const d of deps) {
    if (d.status === "installed") installed++;
    if (d.status === "missing") missing++;
  }

  return (
    <div className="space-y-lg">
      <PanelHeader
        icon={Package}
        title="Dependencies"
        description="What is missing? Status of required system tools."
      />
      <div className="flex gap-md mb-md">
        <div className="flex items-center gap-sm bg-success/5 border border-success/20 rounded-tag px-md py-[6px]">
          <CheckCircle2 className="w-4 h-4 text-success" />
          <span className="text-small text-success font-bold">{installed} Installed</span>
        </div>
        {missing > 0 && (
          <div className="flex items-center gap-sm bg-danger/5 border border-danger/20 rounded-tag px-md py-[6px]">
            <XCircle className="w-4 h-4 text-danger" />
            <span className="text-small text-danger font-bold">{missing} Missing</span>
          </div>
        )}
      </div>
      <div className="space-y-[2px]">
        {deps.map((dep) => (
          <div
            key={dep.name}
            className="flex items-center justify-between py-[10px] px-md border-b border-border/20 last:border-0 hover:bg-bg-elevated/30 rounded-tag transition-colors"
          >
            <div className="flex items-center gap-sm">
              {dep.status === "installed" ? (
                <CheckCircle2 className="w-4 h-4 text-success" />
              ) : (
                <XCircle className="w-4 h-4 text-danger" />
              )}
              <span className="text-body text-text-primary font-mono font-medium">
                {dep.name}
              </span>
            </div>
            <div className="flex items-center gap-md">
              <span className="text-small text-text-muted font-mono">{dep.version}</span>
              <span
                className={cn(
                  "text-[10px] font-bold uppercase px-[6px] py-[1px] rounded",
                  dep.status === "installed"
                    ? "bg-success/10 text-success"
                    : "bg-danger/10 text-danger"
                )}
              >
                {dep.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Panel: Diagnostics ─────────────────────────────────── */
function DiagnosticsPanel() {
  const checks = [
    { label: "Wireless adapter detected", status: "ok" as const },
    { label: "Monitor mode supported", status: "ok" as const },
    { label: "Packet injection capable", status: "ok" as const },
    { label: "Backend API reachable", status: "ok" as const },
    { label: "WebSocket connected", status: "ok" as const },
    { label: "Root/sudo privileges", status: "ok" as const },
    { label: "hostapd-mana installed", status: "warn" as const },
    { label: "GPU acceleration (hashcat)", status: "warn" as const },
  ];

  return (
    <div className="space-y-lg">
      <PanelHeader
        icon={Stethoscope}
        title="Diagnostics"
        description="What is broken? System health and connectivity checks."
      />
      <div className="space-y-[2px]">
        {checks.map((check) => (
          <div
            key={check.label}
            className="flex items-center justify-between py-[10px] px-md border-b border-border/20 last:border-0"
          >
            <span className="text-body text-text-primary">{check.label}</span>
            <div className="flex items-center gap-sm">
              {check.status === "ok" ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  <span className="text-small text-success font-semibold">PASS</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-warning" />
                  <span className="text-small text-warning font-semibold">WARN</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Panel: Advanced ────────────────────────────────────── */
function AdvancedPanel() {
  return (
    <div className="space-y-lg">
      <PanelHeader
        icon={Wrench}
        title="Advanced Settings"
        description="Attack engine parameters and expert configuration."
      />
      <div className="grid grid-cols-2 gap-lg">
        <SettingsGroup
          icon={Shield}
          title="Attack Engine"
          items={[
            { label: "Auto-crack after capture", value: "Enabled" },
            { label: "Default wordlist", value: "rockyou.txt" },
            { label: "Hashcat rules", value: "best64.rule" },
            { label: "Max crack time", value: "30 min" },
          ]}
        />
        <SettingsGroup
          icon={HardDrive}
          title="Capture"
          items={[
            { label: "Recon duration", value: "20 seconds" },
            { label: "Deauth attempts", value: "3" },
            { label: "Handshake timeout", value: "60 seconds" },
            { label: "Evil Twin timeout", value: "10 min" },
          ]}
        />
        <SettingsGroup
          icon={Wifi}
          title="PMKID"
          items={[
            { label: "PMKID timeout", value: "60 seconds" },
            { label: "Auto-fallback to deauth", value: "Enabled" },
          ]}
        />
        <SettingsGroup
          icon={Package}
          title="Paths"
          items={[
            { label: "Wordlist directory", value: "/usr/share/wordlists" },
            { label: "Handshake directory", value: "~/.james/handshakes" },
            { label: "Log directory", value: "~/.james/logs" },
          ]}
        />
      </div>
    </div>
  );
}

/* ── Shared Sub-components ──────────────────────────────── */

function PanelHeader({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-md pb-lg border-b border-border/30">
      <div className="w-10 h-10 rounded-btn bg-accent-cyan/10 flex items-center justify-center flex-shrink-0">
        <Icon className="w-5 h-5 text-accent-cyan" />
      </div>
      <div>
        <h3 className="text-h3 text-text-primary">{title}</h3>
        <p className="text-small text-text-secondary mt-[2px]">{description}</p>
      </div>
    </div>
  );
}

function SettingsGroup({
  icon: Icon,
  title,
  items,
}: {
  icon: React.ElementType;
  title: string;
  items: { label: string; value: string }[];
}) {
  return (
    <div className="bg-bg-elevated/30 border border-border-subtle rounded-btn p-md space-y-sm">
      <div className="flex items-center gap-sm mb-sm">
        <Icon className="w-4 h-4 text-accent-cyan" />
        <span className="text-small font-bold text-text-primary uppercase tracking-wider">
          {title}
        </span>
      </div>
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between py-[3px]">
          <span className="text-small text-text-secondary">{item.label}</span>
          <span className="text-small text-text-primary font-medium">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
