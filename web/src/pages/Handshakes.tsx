import { motion } from "framer-motion";
import {
  FileKey,
  Key,
  Lock,
  Download,
  Trash2,
  Clock,
  HardDrive,
} from "lucide-react";
import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { useShortcutFocus } from "../hooks/useShortcutFocus";
import type { AppState } from "../hooks/useAppState";
import { downloadFile, toCSV } from "../lib/utils";

interface HandshakesProps {
  state: AppState;
  onRemoveHandshake?: (id: string) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function Handshakes({ state, onRemoveHandshake }: HandshakesProps) {
  const { handshakes } = state;
  const [filter, setFilter] = useState("");
  const searchInputRef = useShortcutFocus("f", true);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setFilter("");
      e.currentTarget.blur();
    }
  };

  const { cracked, pending } = useMemo(() => {
    const cracked: typeof state.handshakes = [];
    const pending: typeof state.handshakes = [];
    for (const h of handshakes) {
      if (h.cracked) cracked.push(h);
      else pending.push(h);
    }
    return { cracked, pending };
  }, [handshakes]);

  const filteredHandshakes = useMemo(() => {
    const q = filter;
    const qRegex = q ? new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') : null;
    const result: typeof state.handshakes = [];
    for (const hs of handshakes) {
      if (!qRegex) {
        result.push(hs);
      } else if (
        qRegex.test(hs.essid) ||
        qRegex.test(hs.bssid)
      ) {
        result.push(hs);
      }
    }
    return result;
  }, [handshakes, filter]);

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
            <h2 className="text-h2 text-text-primary mb-[2px]">Handshake Vault</h2>
            <p className="text-body text-text-secondary">
              Manage captured handshakes and cracked credentials.
            </p>
          </div>
          <button
            className="btn-secondary"
            disabled={state.handshakes.length === 0}
            onClick={() => {
              const csv = toCSV(state.handshakes, ["essid", "bssid", "capturedAt", "filePath", "cracked", "key"]);
              downloadFile(`james_handshakes_${Date.now()}.csv`, csv);
            }}
          >
            <Download className="w-4 h-4" />
            Export All
          </button>
        </motion.div>

        {/* Stats */}
        <motion.div variants={item} className="grid grid-cols-3 gap-md">
          <div className="card !p-md flex items-center gap-sm">
            <FileKey className="w-5 h-5 text-accent-purple" />
            <div>
              <div className="text-h3 font-bold text-accent-purple">{state.handshakes.length}</div>
              <div className="text-xs text-text-muted">Total Captures</div>
            </div>
          </div>
          <div className="card !p-md flex items-center gap-sm">
            <Key className="w-5 h-5 text-success" />
            <div>
              <div className="text-h3 font-bold text-success">{cracked.length}</div>
              <div className="text-xs text-text-muted">Cracked</div>
            </div>
          </div>
          <div className="card !p-md flex items-center gap-sm">
            <Lock className="w-5 h-5 text-warning" />
            <div>
              <div className="text-h3 font-bold text-warning">{pending.length}</div>
              <div className="text-xs text-text-muted">Pending</div>
            </div>
          </div>
        </motion.div>

        {/* Table */}
        <motion.div variants={item} className="card">
          <div className="card-header">
            <div className="card-title">
              <HardDrive className="w-5 h-5 text-accent-cyan" />
              Captured Files
            </div>
            <div className="relative">
              <Search className="w-4 h-4 text-text-muted absolute left-[10px] top-1/2 -translate-y-1/2" />
              <input
                type="text"
                ref={searchInputRef}
                placeholder="Filter by SSID, BSSID... (Ctrl+F)"
                className="h-8 pl-8 pr-md text-small bg-bg-elevated border border-border rounded-tag text-text-primary placeholder:text-text-muted focus:border-border-hover focus:outline-none w-[200px] transition-colors"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>
          </div>

          <div className="max-h-[500px] overflow-auto -mx-lg -mb-lg">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SSID</th>
                  <th>BSSID</th>
                  <th>Captured</th>
                  <th>Status</th>
                  <th>Key</th>
                  <th className="w-[100px]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {state.handshakes.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-xl text-text-muted">
                      No handshakes captured yet. Start an attack to collect captures.
                    </td>
                  </tr>
                ) : (
                  filteredHandshakes.map((hs) => (
                    <tr key={hs.id}>
                      <td className="font-medium">{hs.essid}</td>
                      <td className="font-mono text-small text-text-secondary">
                        {hs.bssid}
                      </td>
                      <td>
                        <div className="flex items-center gap-sm text-small text-text-secondary">
                          <Clock className="w-3.5 h-3.5 text-text-muted" />
                          {hs.capturedAt}
                        </div>
                      </td>
                      <td>
                        {hs.cracked ? (
                          <span className="badge-success">CRACKED</span>
                        ) : (
                          <span className="badge-warning">PENDING</span>
                        )}
                      </td>
                      <td>
                        {hs.key ? (
                          <span className="font-mono text-success font-bold">
                            {hs.key}
                          </span>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-[4px]">
                          <button
                            className="btn-ghost btn-sm !h-7 !px-[6px]"
                            title="Copy file path"
                            onClick={() => navigator.clipboard.writeText(hs.filePath)}
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          <button
                            className="btn-ghost btn-sm !h-7 !px-[6px] text-danger hover:text-danger"
                            title="Remove entry"
                            onClick={() => onRemoveHandshake?.(hs.id)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
