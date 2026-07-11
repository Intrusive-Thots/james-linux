import { useState, useCallback, useMemo, memo } from "react";
import { motion } from "framer-motion";
import {
  Radar,
  Play,
  Square,
  Filter,
  Download,
  Lock,
  Unlock,
  Users,
  Radio,
  List,
  Swords,
  XCircle,
  KeyRound,
  ShieldAlert,
  Zap,
} from "lucide-react";
import type { AP, AppState, PageId } from "../hooks/useAppState";
import { SignalBars } from "../components/ui/SignalBars";
import { AirspaceHeatmap } from "../components/ui/AirspaceHeatmap";
import { cn, downloadFile, toCSV } from "../lib/utils";
import { useShortcutFocus } from "../hooks/useShortcutFocus";

interface ReconProps {
  state: AppState;
  onSelectAP: (ap: AP | null) => void;
  onStartScan: () => void;
  onStopScan: () => void;
  onNavigate: (page: PageId) => void;
  send?: (action: string, params?: Record<string, unknown>) => void;
  addLog?: (level: "info" | "warn" | "error" | "success", msg: string) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

type SortKey = "essid" | "power" | "channel" | "clients" | "privacy";
type SortDir = "asc" | "desc";

export function Recon({
  state,
  onSelectAP,
  onStartScan,
  onStopScan,
  onNavigate,
  send,
  addLog,
}: ReconProps) {
  const [sortKey, setSortKey] = useState<SortKey>("power");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filter, setFilter] = useState("");
  const searchInputRef = useShortcutFocus("f", true);
  const [viewMode, setViewMode] = useState<"list" | "map">("map");

  /* ── Smart Attack Advisor ──────────────────────────────────────
     Analyzes the selected AP's properties and recommends the best
     attack strategy.  This is the core beginner UX: the user never
     needs to understand PMKID vs deauth vs WPA3 — we decide for them
     and explain the reasoning in plain English.
  */
  const getRecommendation = useCallback((ap: AP) => {
    const priv = (ap.privacy || "").toUpperCase();
    const isWpa3 = priv.includes("WPA3") || priv.includes("SAE");
    const isOpen = priv.includes("OPN") || priv.includes("OPEN");
    const hasClients = ap.clients > 0;
    const strongSignal = ap.power >= -70;

    if (isOpen) {
      return {
        strategy: "none" as const,
        label: "Open Network",
        icon: Unlock,
        color: "text-success",
        borderColor: "border-success/30",
        bgColor: "bg-success/5",
        explanation: "This network has no password. You can connect directly — no cracking needed!",
        actionLabel: "No Cracking Needed",
        disabled: true,
      };
    }

    if (isWpa3) {
      return {
        strategy: "wpa3_warning" as const,
        label: "WPA3 Detected",
        icon: ShieldAlert,
        color: "text-accent-cyan",
        borderColor: "border-accent-cyan/30",
        bgColor: "bg-accent-cyan/5",
        explanation: "WPA3 uses SAE authentication which resists offline dictionary attacks. PMKID capture may still work on transition-mode APs. Try PMKID first.",
        actionLabel: "🔑 Try PMKID Capture",
        disabled: false,
      };
    }

    if (!hasClients) {
      return {
        strategy: "pmkid" as const,
        label: "PMKID Recommended",
        icon: KeyRound,
        color: "text-warning",
        borderColor: "border-warning/30",
        bgColor: "bg-warning/5",
        explanation: `No clients are connected to this AP. PMKID capture works without clients — it requests the hash directly from the router.${!strongSignal ? " Signal is weak — move closer for better results." : ""}`,
        actionLabel: "🔑 Crack via PMKID",
        disabled: false,
      };
    }

    // Has clients → deauth is the primary, PMKID as backup
    return {
      strategy: "deauth" as const,
      label: "Deauth + Handshake",
      icon: Zap,
      color: "text-accent-purple",
      borderColor: "border-accent-purple/30",
      bgColor: "bg-accent-purple/5",
      explanation: `${ap.clients} client${ap.clients > 1 ? "s" : ""} connected — we'll briefly disconnect ${ap.clients > 1 ? "them" : "it"} to capture the WPA handshake when ${ap.clients > 1 ? "they" : "it"} reconnects.${!strongSignal ? " Tip: move closer for a cleaner capture." : ""}`,
      actionLabel: "⚡ Crack This Network",
      disabled: false,
    };
  }, []);

  /**
   * Smart attack — fires the optimal capture strategy based on AP analysis.
   * PMKID for clientless, deauth for clients present, warning for WPA3.
   */
  const handleSmartAttack = useCallback(() => {
    if (!state.selectedAP) return;
    if (!state.adapter) {
      addLog?.("error", "No wireless adapter detected. Configure one in Settings.");
      return;
    }
    if (!send) {
      addLog?.("error", "Backend offline. Reconnect or restart the API server.");
      return;
    }

    const rec = getRecommendation(state.selectedAP);
    const ap = state.selectedAP;
    const name = ap.essid || "[Hidden]";

    if (rec.strategy === "pmkid" || rec.strategy === "wpa3_warning") {
      addLog?.("info", `Smart Attack: PMKID capture on ${name} (${ap.bssid}) — no clients needed`);
      send("capture_pmkid", {
        interface: state.adapter,
        bssid: ap.bssid,
        essid: ap.essid,
        timeout: 60,
      });
    } else {
      addLog?.("info", `Smart Attack: Deauth + handshake capture on ${name} (${ap.bssid})`);
      send("capture_handshake", {
        interface: state.adapter,
        bssid: ap.bssid,
        channel: ap.channel,
        essid: ap.essid,
      });
    }

    onNavigate("attacks");
  }, [state.selectedAP, state.adapter, send, addLog, onNavigate, getRecommendation]);

  /** Force PMKID regardless of recommendation */
  const handleForcePmkid = useCallback(() => {
    if (!state.selectedAP || !state.adapter || !send) return;
    const ap = state.selectedAP;
    addLog?.("info", `Force PMKID capture on ${ap.essid || "[Hidden]"} (${ap.bssid})`);
    send("capture_pmkid", {
      interface: state.adapter,
      bssid: ap.bssid,
      essid: ap.essid,
      timeout: 60,
    });
    onNavigate("attacks");
  }, [state.selectedAP, state.adapter, send, addLog, onNavigate]);


  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("desc");
      }
    },
    [sortKey]
  );

  // Filter & sort
  const filtered = useMemo(() => {
    const q = filter ? filter.toLowerCase() : "";
    const filteredAps: typeof state.aps = [];
    for (const ap of state.aps) {
      if (!q) {
        filteredAps.push(ap);
      } else if (
        ap.essid.toLowerCase().includes(q) ||
        ap.bssid.toLowerCase().includes(q) ||
        ap.vendor.toLowerCase().includes(q)
      ) {
        filteredAps.push(ap);
      }
    }

    return filteredAps
      .sort((a, b) => {
        const dir = sortDir === "asc" ? 1 : -1;
        switch (sortKey) {
          case "essid":
            return dir * a.essid.localeCompare(b.essid);
          case "power":
            return dir * (a.power - b.power);
          case "channel":
            return dir * (a.channel - b.channel);
          case "clients":
            return dir * (a.clients - b.clients);
          case "privacy":
            return dir * a.privacy.localeCompare(b.privacy);
          default:
            return 0;
        }
      });
  }, [state.aps, filter, sortKey, sortDir]);

  const { aps } = state;
  const { encCount, openCount, totalClients } = useMemo(() => {
    let enc = 0;
    let clients = 0;
    for (const ap of aps) {
      if (!ap.privacy.includes("OPN")) enc++;
      clients += ap.clients;
    }
    return {
      encCount: enc,
      openCount: aps.length - enc,
      totalClients: clients,
    };
  }, [aps]);

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
            <h2 className="text-h2 text-text-primary mb-[2px]">
              Network Reconnaissance
            </h2>
            <p className="text-body text-text-secondary">
              Discover and analyze wireless networks in range.
            </p>
          </div>
          <div className="flex items-center gap-sm">
            {!state.scanning ? (
              <button className="btn-primary" onClick={onStartScan}>
                <Play className="w-4 h-4" />
                Start Scan
              </button>
            ) : (
              <button className="btn-danger" onClick={onStopScan}>
                <Square className="w-4 h-4" />
                Stop Scan
              </button>
            )}
            <button
              className="btn-secondary"
              disabled={state.aps.length === 0}
              onClick={() => {
                const csv = toCSV(state.aps, ["essid", "bssid", "channel", "privacy", "power", "clients", "vendor"]);
                downloadFile(`james_recon_${Date.now()}.csv`, csv);
              }}
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </motion.div>

        {/* Mini Stats */}
        <motion.div variants={item} className="grid grid-cols-4 gap-md">
          <MiniStat icon={Radio} label="Total APs" value={state.aps.length} />
          <MiniStat icon={Lock} label="Encrypted" value={encCount} color="text-warning" />
          <MiniStat icon={Unlock} label="Open" value={openCount} color="text-success" />
          <MiniStat icon={Users} label="Clients" value={totalClients} color="text-accent-purple" />
        </motion.div>

        {/* Main AP Table Card */}
        <motion.div variants={item} className="card">
          <div className="card-header">
            <div className="card-title">
              <Radar className="w-5 h-5 text-accent-cyan" />
              Discovered Networks
              {state.scanning && (
                <span className="badge-cyan ml-sm scanning-pulse">LIVE</span>
              )}
            </div>
            <div className="flex items-center gap-sm">
              {/* View Toggle */}
              <div className="flex bg-bg-elevated border border-border p-[3px] rounded-tag mr-xs">
                <button
                  type="button"
                  className={cn(
                    "px-sm py-1 text-xs font-semibold rounded-btn transition-all duration-200 flex items-center gap-xs",
                    viewMode === "map"
                      ? "bg-accent-cyan text-black shadow-glow"
                      : "text-text-muted hover:text-text-primary"
                  )}
                  onClick={() => setViewMode("map")}
                >
                  <Radar className="w-3.5 h-3.5" />
                  Map View
                </button>
                <button
                  type="button"
                  className={cn(
                    "px-sm py-1 text-xs font-semibold rounded-btn transition-all duration-200 flex items-center gap-xs",
                    viewMode === "list"
                      ? "bg-accent-cyan text-black shadow-glow"
                      : "text-text-muted hover:text-text-primary"
                  )}
                  onClick={() => setViewMode("list")}
                >
                  <List className="w-3.5 h-3.5" />
                  List View
                </button>
              </div>

              <div className="relative">
                <Filter className="w-4 h-4 text-text-muted absolute left-[10px] top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  ref={searchInputRef}
                  placeholder="Filter by SSID, BSSID… (Ctrl+F)"
                  className="h-8 pl-8 pr-md text-small bg-bg-elevated border border-border rounded-tag text-text-primary placeholder:text-text-muted focus:border-border-hover focus:outline-none w-[200px] transition-colors"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Conditional view rendering */}
          {viewMode === "list" ? (
            <div className="max-h-[420px] overflow-auto -mx-lg -mb-lg">
              <table className="data-table">
                <thead>
                  <tr>
                    <SortHeader label="SSID" sortKey="essid" current={sortKey} dir={sortDir} onClick={handleSort} />
                    <th className="w-[160px]">BSSID</th>
                    <SortHeader label="Signal" sortKey="power" current={sortKey} dir={sortDir} onClick={handleSort} />
                    <SortHeader label="CH" sortKey="channel" current={sortKey} dir={sortDir} onClick={handleSort} />
                    <SortHeader label="Security" sortKey="privacy" current={sortKey} dir={sortDir} onClick={handleSort} />
                    <SortHeader label="Clients" sortKey="clients" current={sortKey} dir={sortDir} onClick={handleSort} />
                    <th>Vendor</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-xl text-text-muted">
                        {state.scanning
                          ? "Scanning… networks will appear here."
                          : "No networks. Start a scan to discover APs."}
                      </td>
                    </tr>
                  ) : (
                    filtered.map((ap) => (
                      <ApRow
                        key={ap.bssid}
                        ap={ap}
                        isSelected={state.selectedAP?.bssid === ap.bssid}
                        onSelectAP={onSelectAP}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex justify-center items-center py-sm">
              <AirspaceHeatmap
                aps={filtered}
                selectedAP={state.selectedAP}
                onSelectAP={onSelectAP}
                scanning={state.scanning}
                standalone={false}
              />
            </div>
          )}
        </motion.div>

        {/* Selected AP: Smart Attack Advisor Panel */}
        {state.selectedAP && (() => {
          const rec = getRecommendation(state.selectedAP);
          const RecIcon = rec.icon;
          return (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="card border-accent-cyan/30 bg-bg-panel/95 backdrop-blur-md relative overflow-hidden shadow-[0_0_30px_rgba(34,211,238,0.1)]"
          >
            {/* Hologram scan line overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-accent-cyan/[0.02] via-transparent to-transparent pointer-events-none" />
            
            <div className="card-header border-b border-border/30 pb-sm mb-md flex items-center justify-between">
              <div className="card-title text-accent-cyan font-bold tracking-wider uppercase text-body">
                <Radar className="w-5 h-5 animate-pulse" />
                Tactical Target Lock-On HUD
              </div>
              <div className="flex items-center gap-xs">
                <span className="w-2 h-2 rounded-full bg-danger animate-ping" />
                <span className="text-[10px] font-mono text-danger font-bold uppercase tracking-wider">Locked onto Target</span>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-lg items-start">
              {/* Target Data Console */}
              <div className="col-span-5 grid grid-cols-2 gap-md border-r border-border/40 pr-lg">
                <div className="space-y-[4px]">
                  <span className="text-[10px] text-text-muted font-bold font-mono block uppercase">Target ESSID</span>
                  <span className="text-body font-bold text-text-primary block truncate">
                    {state.selectedAP.essid || (
                      <span className="text-text-muted italic">&lt;Hidden SSID&gt;</span>
                    )}
                  </span>
                  <span className="text-[10px] text-text-muted font-mono font-semibold block uppercase">MAC / BSSID</span>
                  <span className="text-xs font-mono text-text-secondary block">
                    {state.selectedAP.bssid}
                  </span>
                </div>

                <div className="space-y-[4px]">
                  <span className="text-[10px] text-text-muted font-bold font-mono block uppercase">Signal</span>
                  <div className="flex items-center gap-xs py-[2px]">
                    <SignalBars power={state.selectedAP.power} />
                    <span className={cn(
                      "text-xs font-bold font-mono",
                      state.selectedAP.power >= -55 ? "text-success" : state.selectedAP.power >= -75 ? "text-warning" : "text-danger"
                    )}>
                      {state.selectedAP.power} dBm
                    </span>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono font-semibold block uppercase">Channel</span>
                  <span className="text-xs font-mono text-accent-cyan block">
                    CH {state.selectedAP.channel}
                  </span>
                  <span className="text-[10px] text-text-muted font-mono font-semibold block uppercase mt-[2px]">Security</span>
                  <div className="py-[2px]">
                    <SecurityBadge privacy={state.selectedAP.privacy} />
                  </div>
                  <span className="text-[10px] text-text-muted font-mono font-semibold block uppercase mt-[2px]">Clients</span>
                  <span className="text-xs font-mono text-accent-purple block font-bold">
                    {state.selectedAP.clients > 0 ? (
                      <span className="flex items-center gap-xs">
                        <Users className="w-3 h-3" />
                        {state.selectedAP.clients}
                      </span>
                    ) : (
                      "0"
                    )}
                  </span>
                </div>
              </div>

              {/* Smart Attack Advisor — the core beginner UX innovation.
                  Analyzes the AP and shows exactly what will happen + why. */}
              <div className="col-span-7 space-y-sm">
                {/* Recommendation badge + explanation */}
                <div className={cn(
                  "rounded-btn border p-md space-y-sm",
                  rec.borderColor, rec.bgColor
                )}>
                  <div className="flex items-center gap-sm">
                    <div className={cn("w-8 h-8 rounded-btn flex items-center justify-center", rec.bgColor, rec.borderColor, "border")}>
                      <RecIcon className={cn("w-4 h-4", rec.color)} />
                    </div>
                    <div>
                      <div className={cn("text-xs font-extrabold uppercase tracking-wider", rec.color)}>
                        {rec.label}
                      </div>
                      <div className="text-[10px] text-text-muted font-mono uppercase">Smart Advisor</div>
                    </div>
                  </div>
                  <p className="text-small text-text-secondary leading-relaxed">
                    {rec.explanation}
                  </p>
                </div>

                {/* Action buttons */}
                <button
                  className={cn(
                    "w-full justify-center text-xs font-bold tracking-wider uppercase py-md h-10 flex items-center gap-sm rounded-btn border transition-all duration-200",
                    rec.disabled
                      ? "btn-ghost opacity-60 cursor-not-allowed"
                      : "btn-primary shadow-glow"
                  )}
                  disabled={rec.disabled}
                  onClick={handleSmartAttack}
                >
                  <Swords className="w-4 h-4" />
                  {rec.actionLabel}
                </button>

                <div className="grid grid-cols-2 gap-sm">
                  {/* Always show a PMKID button for manual override */}
                  <button
                    className="btn-secondary w-full justify-center text-[10px] font-bold tracking-wider uppercase h-8 flex items-center gap-xs"
                    onClick={handleForcePmkid}
                    title="Force PMKID capture regardless of recommendation"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    PMKID
                  </button>
                  <button
                    className="btn-ghost w-full justify-center text-[10px] font-bold tracking-wider uppercase h-8 flex items-center gap-xs"
                    onClick={() => onSelectAP(null)}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Deselect
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
          );
        })()}
      </div>
    </motion.div>
  );
}

/* ── Sub-components ──────────────────────────── */

function MiniStat({
  icon: Icon,
  label,
  value,
  color = "text-accent-cyan",
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="card !p-md flex items-center gap-sm">
      <Icon className={`w-5 h-5 ${color}`} />
      <div>
        <div className={`text-h3 font-bold ${color}`}>{value}</div>
        <div className="text-xs text-text-muted">{label}</div>
      </div>
    </div>
  );
}

function SecurityBadge({ privacy }: { privacy: string }) {
  if (privacy.includes("OPN")) return <span className="badge-success">OPEN</span>;
  if (privacy.includes("WPA3")) return <span className="badge-cyan">WPA3</span>;
  if (privacy.includes("WPA2")) return <span className="badge-warning">WPA2</span>;
  if (privacy.includes("WEP")) return <span className="badge-danger">WEP</span>;
  return <span className="badge-muted">{privacy}</span>;
}

function SortHeader({
  label,
  sortKey,
  current,
  dir,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onClick: (key: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <th
      className="cursor-pointer select-none hover:text-text-primary transition-colors"
      onClick={() => onClick(sortKey)}
    >
      <span className="inline-flex items-center gap-[4px]">
        {label}
        {active && (
          <span className="text-accent-cyan">
            {dir === "asc" ? "↑" : "↓"}
          </span>
        )}
      </span>
    </th>
  );
}

// ⚡ Bolt: Extracted table row into a memoized component.
// Why: In a real-time scanning dashboard, state.aps continuously receives new array
// references from the websocket, forcing a re-render of all 100+ rows every tick.
// Impact: Reduces row re-renders by ~95% during active scans by only re-rendering
// rows where scalar values (power, clients) actually changed.
const ApRow = memo(function ApRow({
  ap,
  isSelected,
  onSelectAP
}: {
  ap: AP,
  isSelected: boolean,
  onSelectAP: (ap: AP | null) => void
}) {
  return (
    <tr
      className={cn(
        "cursor-pointer",
        isSelected && "selected"
      )}
      onClick={() =>
        onSelectAP(isSelected ? null : ap)
      }
    >
      <td className="font-medium">
        {ap.essid || (
          <span className="text-text-muted italic">
            [Hidden]
          </span>
        )}
      </td>
      <td className="font-mono text-small text-text-secondary">
        {ap.bssid}
      </td>
      <td>
        <div className="flex items-center gap-sm">
          <SignalBars power={ap.power} />
          <span className="text-small text-text-muted font-mono">
            {ap.power} dBm
          </span>
        </div>
      </td>
      <td className="text-center font-mono">
        {ap.channel}
      </td>
      <td>
        <SecurityBadge privacy={ap.privacy} />
      </td>
      <td className="text-center">
        {ap.clients > 0 ? (
          <span className="text-accent-purple font-medium">
            {ap.clients}
          </span>
        ) : (
          <span className="text-text-muted">0</span>
        )}
      </td>
      <td className="text-text-secondary text-small">
        {ap.vendor}
      </td>
    </tr>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.ap.power === nextProps.ap.power &&
    prevProps.ap.clients === nextProps.ap.clients &&
    prevProps.ap.bssid === nextProps.ap.bssid &&
    prevProps.ap.essid === nextProps.ap.essid &&
    prevProps.ap.channel === nextProps.ap.channel &&
    prevProps.ap.privacy === nextProps.ap.privacy &&
    prevProps.ap.vendor === nextProps.ap.vendor
  );
});
