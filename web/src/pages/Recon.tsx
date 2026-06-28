import { useState, useCallback, useMemo } from "react";
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
} from "lucide-react";
import type { AP, AppState, PageId } from "../hooks/useAppState";
import { SignalBars } from "../components/ui/SignalBars";
import { cn, downloadFile, toCSV } from "../lib/utils";

interface ReconProps {
  state: AppState;
  onSelectAP: (ap: AP | null) => void;
  onStartScan: () => void;
  onStopScan: () => void;
  onNavigate: (page: PageId) => void;
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
}: ReconProps) {
  const [sortKey, setSortKey] = useState<SortKey>("power");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filter, setFilter] = useState("");

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
    const filteredAps = [];
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

  const { encCount, openCount, totalClients } = useMemo(() => {
    let enc = 0;
    let clients = 0;
    for (const ap of state.aps) {
      if (!ap.privacy.includes("OPN")) enc++;
      clients += ap.clients;
    }
    return {
      encCount: enc,
      openCount: state.aps.length - enc,
      totalClients: clients,
    };
  }, [state.aps]);

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
              <div className="relative">
                <Filter className="w-4 h-4 text-text-muted absolute left-[10px] top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by SSID, BSSID, vendor…"
                  className="h-8 pl-8 pr-md text-small bg-bg-elevated border border-border rounded-tag text-text-primary placeholder:text-text-muted focus:border-border-hover focus:outline-none w-[260px] transition-colors"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Table */}
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
                  filtered.map((ap) => {
                    const isSelected =
                      state.selectedAP?.bssid === ap.bssid;
                    return (
                      <tr
                        key={ap.bssid}
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
                  })
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Selected AP Detail Panel */}
        {state.selectedAP && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="card border-accent-cyan/20"
          >
            <div className="card-header">
              <div className="card-title">
                <Radar className="w-5 h-5 text-accent-cyan" />
                Selected Target
              </div>
              <button
                className="btn-primary btn-sm"
                onClick={() => onNavigate("attacks")}
              >
                Attack This Target →
              </button>
            </div>
            <div className="grid grid-cols-4 gap-md text-body">
              <div>
                <div className="text-text-muted text-small mb-[2px]">SSID</div>
                <div className="font-medium">
                  {state.selectedAP.essid || "[Hidden]"}
                </div>
              </div>
              <div>
                <div className="text-text-muted text-small mb-[2px]">BSSID</div>
                <div className="font-mono text-small">
                  {state.selectedAP.bssid}
                </div>
              </div>
              <div>
                <div className="text-text-muted text-small mb-[2px]">
                  Channel / Signal
                </div>
                <div className="flex items-center gap-sm">
                  <span>CH {state.selectedAP.channel}</span>
                  <SignalBars power={state.selectedAP.power} />
                  <span className="text-text-muted font-mono text-small">
                    {state.selectedAP.power} dBm
                  </span>
                </div>
              </div>
              <div>
                <div className="text-text-muted text-small mb-[2px]">
                  Security
                </div>
                <SecurityBadge privacy={state.selectedAP.privacy} />
              </div>
            </div>
          </motion.div>
        )}
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
