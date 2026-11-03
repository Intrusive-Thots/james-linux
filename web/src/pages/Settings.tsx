import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Wifi,
  Shield,
  Package,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Stethoscope,
  Wrench,
  Sliders,
  RefreshCw,
  Loader2,
  HelpCircle,
} from "lucide-react";
import type { SubPageId, SettingsSubPage } from "../hooks/useAppState";
import { cn } from "../lib/utils";

const API_HTTP_URL = import.meta.env.VITE_API_HTTP_URL || "";

const CLIENT_FACTS = [
  { label: "Theme", value: "Dark tactical — the only theme" },
  { label: "Log buffer", value: "Last 500 entries in this session" },
  { label: "Opens on", value: "Dashboard" },
  { label: "API token storage", value: "This browser session only" },
] as const;

const RECOVERY_COMMAND = "./launch_ui.sh --api";

function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = sessionStorage.getItem("james_api_token");
  const headers = new Headers(init.headers);
  if (token) headers.set("X-JAMES-API-Token", token);
  const target =
    typeof input === "string" && API_HTTP_URL && input.startsWith("/")
      ? new URL(input, API_HTTP_URL).toString()
      : input;
  return fetch(target, { ...init, headers });
}

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
          {panel === "diagnostics" && <DiagnosticsPanel connected={connected} />}
          {panel === "advanced" && <AdvancedPanel />}
        </div>
      </div>
    </motion.div>
  );
}

/* ── Panel: General ─────────────────────────────────────── */
function GeneralPanel() {
  const savedToken = sessionStorage.getItem("james_api_token") || "";
  const [apiToken, setApiToken] = useState(savedToken);
  const trimmed = apiToken.trim();
  const dirty = trimmed !== savedToken;
  const hasSavedToken = savedToken.length > 0;

  const saveApiToken = () => {
    if (trimmed) sessionStorage.setItem("james_api_token", trimmed);
    else sessionStorage.removeItem("james_api_token");
    window.location.reload();
  };

  return (
    <div className="space-y-lg">
      <PanelHeader
        icon={Sliders}
        title="General Settings"
        description="The only preference stored in this browser is the API token. Theme, notifications, and session timeout are not settings."
      />
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-sm">
        {CLIENT_FACTS.map((fact) => (
          <div
            key={fact.label}
            className="rounded-btn border border-border-subtle bg-bg-elevated/30 px-md py-sm"
          >
            <dt className="text-small text-text-secondary">{fact.label}</dt>
            <dd className="text-body text-text-primary mt-[2px]">{fact.value}</dd>
          </div>
        ))}
      </dl>
      <section className="rounded-lg border border-border-subtle bg-surface-secondary p-md space-y-sm">
        <div>
          <h3 className="text-body font-semibold text-text-primary">Remote API authentication</h3>
          <p className="text-caption text-text-secondary">
            Optional shared token for a remotely hosted backend. Use HTTPS/WSS or a trusted VPN.
            The token is kept in this browser session only.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-sm">
          <input
            type="password"
            autoComplete="current-password"
            value={apiToken}
            onChange={(event) => setApiToken(event.target.value)}
            placeholder="JAMES_API_TOKEN"
            aria-label="JAMES API token"
            className="input flex-1"
          />
          <div className="flex items-center gap-sm shrink-0">
            {hasSavedToken && (
              <button
                type="button"
                onClick={() => setApiToken("")}
                disabled={trimmed.length === 0}
                className="btn btn-ghost"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              onClick={saveApiToken}
              disabled={!dirty}
              className="btn btn-primary"
            >
              Save & reconnect
            </button>
          </div>
        </div>
        <p className="text-small text-text-muted" aria-live="polite">
          {dirty
            ? "Unsaved change — save to apply and reconnect."
            : hasSavedToken
            ? "A token is stored for this browser session."
            : "No token stored. Leave blank when the backend runs locally."}
        </p>
      </section>
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
  const [netGuardEnabled, setNetGuardEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [togglingInterface, setTogglingInterface] = useState<string | null>(null);
  const [actionResults, setActionResults] = useState<Record<string, { success?: boolean; error?: string }>>({});

  const fetchInterfaces = async (): Promise<string | null> => {
    try {
      const res = await apiFetch("/api/interfaces");
      if (!res.ok) return `HTTP ${res.status}`;
      const data = await res.json();
      if (!Array.isArray(data)) return "Unexpected interface payload";
      setInterfaces(data.map((iface: any) => ({
        name: iface.interface || iface.name || "unknown",
        mode: iface.mode || "unknown"
      })));
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Request failed";
    }
  };

  const fetchAudit = async (): Promise<string | null> => {
    try {
      const res = await apiFetch("/api/interfaces/audit");
      if (!res.ok) return `HTTP ${res.status}`;
      const data = await res.json();
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        return "Unexpected audit payload";
      }
      setAuditData(data);
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Request failed";
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
    const [ifaceError, auditError] = await Promise.all([
      fetchInterfaces(),
      fetchAudit(),
    ]);
    setInventoryError(ifaceError || auditError);
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
        netGuardEnabled === null
          ? "bg-bg-elevated/40 border-border text-text-secondary"
          : netGuardEnabled
          ? "bg-emerald-950/10 border-emerald-500/20 text-emerald-300"
          : "bg-amber-950/15 border-amber-500/20 text-amber-300"
      )}>
        <div className="flex items-start justify-between gap-md">
          <div className="space-y-xs">
            <div className="flex items-center gap-sm">
              <Shield className={cn(
                "w-5 h-5 shrink-0",
                netGuardEnabled === null
                  ? "text-text-muted"
                  : netGuardEnabled
                  ? "text-emerald-400"
                  : "text-amber-400"
              )} />
              <h3 className="font-bold text-text-primary">
                NetworkGuard Self-Protection:{" "}
                {netGuardEnabled === null ? "UNKNOWN" : netGuardEnabled ? "ACTIVE" : "BYPASSED"}
              </h3>
            </div>
            <p className="text-body-small text-text-secondary leading-relaxed max-w-3xl">
              {netGuardEnabled === null
                ? "Waiting for the backend to report whether self-protection is on. This panel does not assume it is active."
                : netGuardEnabled
                ? "Prevents JAMES from disabling active network adapters providing the current admin control session or severing local connectivity. Monitor mode switches on active adapters will be blocked."
                : "DANGER Mode. NetworkGuard safety checks are disabled. You can toggle any interface, but putting your primary connection interface into monitor mode will kill your WebSocket connection instantly."}
            </p>
          </div>
          <button
            onClick={() => {
              if (netGuardEnabled === null) return;
              handleToggleNetGuard(!netGuardEnabled);
            }}
            disabled={netGuardEnabled === null || !connected}
            className={cn(
              "btn px-md py-sm font-semibold rounded-btn transition-colors duration-200 disabled:opacity-50",
              netGuardEnabled
                ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                : "bg-amber-600 hover:bg-amber-700 text-black"
            )}
          >
            {netGuardEnabled === null
              ? "Waiting…"
              : netGuardEnabled
              ? "Bypass Protection"
              : "Enable Protection"}
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
            {inventoryError ? (
              <UnavailableNote
                title="Interface inventory unavailable"
                detail={`The backend did not answer (${inventoryError}). Start the API with ${RECOVERY_COMMAND}.`}
              />
            ) : interfaces.length === 0 ? (
              <div className="bg-bg-elevated/20 border border-border-subtle rounded-btn p-lg text-center">
                <AlertTriangle className="w-8 h-8 text-text-muted mx-auto mb-sm" />
                <span className="text-body text-text-secondary">The backend reported no wireless interfaces.</span>
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
                Scores come from the backend hardware audit. Nothing is filled in when that audit is unavailable.
              </p>

              <div className="space-y-sm">
                {inventoryError ? (
                  <div className="text-center py-sm text-body-small text-text-muted">
                    Audit unavailable until the API answers.
                  </div>
                ) : Object.keys(auditData).length === 0 ? (
                  <div className="text-center py-sm text-body-small text-text-muted">
                    The backend reported no adapter audit.
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

type ToolReport = Record<string, boolean>;

interface LiveCheck {
  label: string;
  status: "pass" | "fail" | "unknown";
  detail: string;
}

interface WordlistEntry {
  path: string;
  name?: string;
  category?: string;
  lines?: number;
  size_mb?: number;
}

/* ── Panel: Dependencies ────────────────────────────────── */
function DependenciesPanel() {
  const [tools, setTools] = useState<ToolReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/system-check");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("Unexpected system-check payload");
      }
      const report: ToolReport = {};
      for (const [name, present] of Object.entries(data)) {
        if (typeof present === "boolean") report[name] = present;
      }
      setTools(report);
    } catch (err) {
      setTools(null);
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rows = tools
    ? Object.entries(tools).sort((a, b) => Number(a[1]) - Number(b[1]) || a[0].localeCompare(b[0]))
    : [];
  const installed = rows.filter(([, present]) => present).length;
  const missing = rows.length - installed;

  return (
    <div className="space-y-lg">
      <div className="flex items-start justify-between gap-md">
        <PanelHeader
          className="flex-1 min-w-0 border-b-0 pb-0"
          icon={Package}
          title="Dependencies"
          description="Tools the backend found on this host. Versions are omitted because the API reports presence only."
        />
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="btn btn-secondary flex items-center gap-xs px-md py-sm shrink-0"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          Refresh
        </button>
      </div>
      {loading && !tools ? (
        <LoadingNote label="Checking installed tools…" />
      ) : error ? (
        <UnavailableNote
          title="Tool inventory unavailable"
          detail={`The system check did not complete (${error}). Start the API with ${RECOVERY_COMMAND}.`}
        />
      ) : rows.length === 0 ? (
        <UnavailableNote
          title="No tools reported"
          detail="The backend answered, and it did not list any tools."
        />
      ) : (
        <>
          <div className="flex gap-md">
            <CountPill icon={CheckCircle2} tone="success" label={`${installed} installed`} />
            <CountPill icon={XCircle} tone="danger" label={`${missing} missing`} />
          </div>
          <div className="space-y-[2px]">
            {rows.map(([name, present]) => (
              <div
                key={name}
                className="flex items-center justify-between py-[10px] px-md border-b border-border/20 last:border-0"
              >
                <div className="flex items-center gap-sm">
                  {present ? (
                    <CheckCircle2 className="w-4 h-4 text-success" />
                  ) : (
                    <XCircle className="w-4 h-4 text-danger" />
                  )}
                  <span className="text-body text-text-primary font-mono font-medium">{name}</span>
                </div>
                <span
                  className={cn(
                    "text-[10px] font-bold uppercase px-[6px] py-[1px] rounded",
                    present ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                  )}
                >
                  {present ? "installed" : "missing"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ── Panel: Diagnostics ─────────────────────────────────── */
function DiagnosticsPanel({ connected }: { connected: boolean }) {
  const [checks, setChecks] = useState<LiveCheck[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const next: LiveCheck[] = [
      {
        label: "WebSocket",
        status: connected ? "pass" : "fail",
        detail: connected ? "Connected" : "Disconnected",
      },
    ];
    try {
      const health = await apiFetch("/api/health");
      next.unshift({
        label: "Backend API",
        status: health.ok ? "pass" : "fail",
        detail: health.ok ? "Reachable" : `HTTP ${health.status}`,
      });
      const [ifacesRes, auditRes] = await Promise.all([
        apiFetch("/api/interfaces"),
        apiFetch("/api/interfaces/audit"),
      ]);
      if (ifacesRes.ok) {
        const ifaces = await ifacesRes.json();
        const count = Array.isArray(ifaces) ? ifaces.length : 0;
        next.push({
          label: "Wireless adapters",
          status: count > 0 ? "pass" : "fail",
          detail: count > 0 ? `${count} reported` : "None reported",
        });
      } else {
        next.push({
          label: "Wireless adapters",
          status: "unknown",
          detail: `HTTP ${ifacesRes.status}`,
        });
      }
      if (auditRes.ok) {
        const audit = await auditRes.json();
        const values = audit && typeof audit === "object" ? Object.values(audit) : [];
        const monitor = values.filter(
          (entry) =>
            !!entry &&
            typeof entry === "object" &&
            (entry as { monitor_supported?: boolean }).monitor_supported
        ).length;
        next.push({
          label: "Monitor mode advertised",
          status: values.length === 0 ? "unknown" : monitor > 0 ? "pass" : "fail",
          detail: values.length === 0 ? "No adapter audit" : `${monitor} of ${values.length}`,
        });
      } else {
        next.push({
          label: "Monitor mode advertised",
          status: "unknown",
          detail: `HTTP ${auditRes.status}`,
        });
      }
    } catch {
      next.unshift({
        label: "Backend API",
        status: "fail",
        detail: "Unreachable",
      });
    }
    setChecks(next);
    setLoading(false);
  }, [connected]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-lg">
      <div className="flex items-start justify-between gap-md">
        <PanelHeader
          className="flex-1 min-w-0 border-b-0 pb-0"
          icon={Stethoscope}
          title="Diagnostics"
          description="Checks that can be answered from the live API and this browser's socket. Missing probes stay unknown."
        />
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="btn btn-secondary flex items-center gap-xs px-md py-sm shrink-0"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          Refresh
        </button>
      </div>
      {loading && checks.length === 0 ? (
        <LoadingNote label="Running live checks…" />
      ) : (
        <div className="space-y-[2px]">
          {checks.map((check) => (
            <div
              key={check.label}
              className="flex items-center justify-between gap-md py-[10px] px-md border-b border-border/20 last:border-0"
            >
              <span className="text-body text-text-primary">{check.label}</span>
              <div className="flex items-center gap-sm">
                <span className="text-small text-text-secondary tabular-nums">{check.detail}</span>
                <StatusMark status={check.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Panel: Advanced ────────────────────────────────────── */
function AdvancedPanel() {
  const [wordlists, setWordlists] = useState<WordlistEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/api/wordlists");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setWordlists(Array.isArray(data) ? data : []);
    } catch (err) {
      setWordlists(null);
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-lg">
      <div className="flex items-start justify-between gap-md">
        <PanelHeader
          className="flex-1 min-w-0 border-b-0 pb-0"
          icon={Wrench}
          title="Advanced"
          description="This client does not store attack timings or wordlist paths. The list below is the inventory the backend can see on disk."
        />
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="btn btn-secondary flex items-center gap-xs px-md py-sm shrink-0"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          Refresh
        </button>
      </div>
      {loading && !wordlists ? (
        <LoadingNote label="Loading wordlist inventory…" />
      ) : error ? (
        <UnavailableNote
          title="Wordlist inventory unavailable"
          detail={`The backend did not answer (${error}). Start the API with ${RECOVERY_COMMAND}.`}
        />
      ) : wordlists && wordlists.length === 0 ? (
        <UnavailableNote
          title="No wordlists reported"
          detail="The backend answered, and it did not find wordlists on the configured paths."
        />
      ) : (
        <div className="space-y-[2px]">
          {wordlists?.map((item) => (
            <div
              key={item.path}
              className="flex items-center justify-between gap-md py-[10px] px-md border-b border-border/20 last:border-0"
            >
              <div className="min-w-0">
                <div className="text-body text-text-primary font-medium truncate">
                  {item.name || item.path}
                </div>
                <div className="text-small text-text-secondary font-mono truncate">{item.path}</div>
              </div>
              <span className="text-small text-text-muted font-mono shrink-0 tabular-nums">
                {item.category || "wordlist"}
                {typeof item.size_mb === "number" ? ` · ${item.size_mb} MB` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Shared Sub-components ──────────────────────────────── */

function PanelHeader({
  icon: Icon,
  title,
  description,
  className,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-md pb-lg border-b border-border/30", className)}>
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

function LoadingNote({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-sm py-lg text-text-secondary">
      <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
      <span className="text-body">{label}</span>
    </div>
  );
}

function UnavailableNote({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-btn border border-border bg-bg-elevated/40 p-lg space-y-xs">
      <div className="flex items-center gap-sm">
        <AlertTriangle className="w-4 h-4 text-warning" />
        <h4 className="text-body font-semibold text-text-primary">{title}</h4>
      </div>
      <p className="text-small text-text-secondary">{detail}</p>
    </div>
  );
}

function CountPill({
  icon: Icon,
  tone,
  label,
}: {
  icon: React.ElementType;
  tone: "success" | "danger";
  label: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-sm rounded-tag px-md py-[6px] border",
        tone === "success"
          ? "bg-success/5 border-success/20 text-success"
          : "bg-danger/5 border-danger/20 text-danger"
      )}
    >
      <Icon className="w-4 h-4" />
      <span className="text-small font-bold">{label}</span>
    </div>
  );
}

function StatusMark({ status }: { status: LiveCheck["status"] }) {
  if (status === "pass") {
    return (
      <span className="inline-flex items-center gap-xs text-small font-semibold text-success">
        <CheckCircle2 className="w-4 h-4" />
        PASS
      </span>
    );
  }
  if (status === "fail") {
    return (
      <span className="inline-flex items-center gap-xs text-small font-semibold text-danger">
        <XCircle className="w-4 h-4" />
        FAIL
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-xs text-small font-semibold text-text-secondary">
      <HelpCircle className="w-4 h-4" />
      UNKNOWN
    </span>
  );
}
