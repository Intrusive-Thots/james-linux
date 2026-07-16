import React, { useState, useEffect, useRef, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ScrollText,
  Search,
  Download,
  AlertCircle,
  Info,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import type { LogEntry, AppState } from "../hooks/useAppState";
import { cn, downloadFile } from "../lib/utils";
import { useShortcutFocus } from "../hooks/useShortcutFocus";

interface LogsProps {
  state: AppState;
}

const LEVEL_ICONS: Record<LogEntry["level"], React.ElementType> = {
  info: Info,
  warn: AlertTriangle,
  error: AlertCircle,
  success: CheckCircle2,
};

const LEVEL_COLORS: Record<LogEntry["level"], string> = {
  info: "text-accent-cyan",
  warn: "text-warning",
  error: "text-danger",
  success: "text-success",
};

// ⚡ Bolt: Extract log row into a memoized component to prevent re-rendering
// all 500 logs every time a single new log is added to the global state.
const LogRow = React.memo(function LogRow({ log }: { log: LogEntry }) {
  const LevelIcon = LEVEL_ICONS[log.level];
  return (
    <div className="log-entry flex items-start gap-sm py-[3px] px-sm rounded-[4px] hover:bg-bg-elevated/50 transition-colors">
      <span className="text-text-muted font-mono flex-shrink-0 select-all">
        {log.timestamp}
      </span>
      <LevelIcon
        className={cn(
          "w-3.5 h-3.5 flex-shrink-0 mt-[2px]",
          LEVEL_COLORS[log.level]
        )}
      />
      <span
        className={cn(
          "text-xs font-semibold uppercase w-[56px] flex-shrink-0",
          LEVEL_COLORS[log.level]
        )}
      >
        {log.level}
      </span>
      <span className="text-text-primary font-mono text-small flex-1">
        {log.message}
      </span>
    </div>
  );
});

export function Logs({ state }: LogsProps) {
  const [filter, setFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState<LogEntry["level"] | "all">("all");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const searchInputRef = useShortcutFocus("f", true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.logs.length, autoScroll]);

  const filtered = useMemo(() => {
    const q = filter;
    const qRegex = q ? new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') : null;
    const acc: LogEntry[] = [];
    for (const log of state.logs) {
      if (levelFilter !== "all" && log.level !== levelFilter) continue;
      if (qRegex && !qRegex.test(log.message)) continue;
      acc.push(log);
    }
    return acc;
  }, [state.logs, filter, levelFilter]);

  const levelCounts = useMemo(() => {
    const acc = { info: 0, warn: 0, error: 0, success: 0 };
    for (const l of state.logs) {
      acc[l.level]++;
    }
    return acc;
  }, [state.logs]);

  const { lastError, lastSuccess } = useMemo(() => {
    let lastError = "None";
    let lastSuccess = "None";
    for (let i = state.logs.length - 1; i >= 0; i--) {
      const l = state.logs[i];
      if (lastError === "None" && l.level === "error") {
        lastError = l.message;
      }
      if (lastSuccess === "None" && l.level === "success") {
        lastSuccess = l.message;
      }
      if (lastError !== "None" && lastSuccess !== "None") {
        break;
      }
    }
    return { lastError, lastSuccess };
  }, [state.logs]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full flex flex-col p-lg"
    >
      <div className="max-w-dashboard mx-auto w-full flex flex-col flex-1 min-h-0 space-y-lg">
        {/* Header */}
        <div className="flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-h2 text-text-primary mb-[2px]">System Logs</h2>
            <p className="text-body text-text-secondary">
              {state.logs.length} entries · Single source of truth for all activity.
            </p>
          </div>
          <div className="flex items-center gap-sm">
            <button className="btn-secondary btn-sm" onClick={() => setAutoScroll(!autoScroll)}>
              {autoScroll ? "Pause" : "Resume"} Scroll
            </button>
            <button
              className="btn-secondary btn-sm"
              disabled={state.logs.length === 0}
              onClick={() => {
                const text = state.logs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join("\n");
                downloadFile(`james_logs_${Date.now()}.log`, text, "text/plain");
              }}
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>
        </div>

        {/* Summary Widgets */}
        <div className="grid grid-cols-3 gap-md flex-shrink-0">
          <SummaryWidget
            label="Current Task"
            value={
              state.scanning
                ? "Area reconnaissance active"
                : state.attack.stage === "capturing"
                  ? state.attack.stage_name || "Capturing handshake"
                  : state.attack.stage === "cracking"
                    ? state.attack.stage_name || "Cracking password"
                    : "Idle"
            }
            variant="cyan"
          />
          <SummaryWidget
            label="Last Error"
            value={
              lastError
            }
            variant="danger"
          />
          <SummaryWidget
            label="Last Success"
            value={
              lastSuccess
            }
            variant="success"
          />
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-sm flex-shrink-0">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-[10px] top-1/2 -translate-y-1/2" />
            <input
              type="text"
              ref={searchInputRef}
              placeholder="Search logs… (Ctrl+F)"
              className="w-full h-9 pl-8 pr-md text-body bg-bg-elevated border border-border rounded-tag text-text-primary placeholder:text-text-muted focus:border-border-hover focus:outline-none transition-colors"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          {(["all", "info", "warn", "error", "success"] as const).map(
            (lvl) => (
              <button
                key={lvl}
                className={cn(
                  "btn-sm",
                  levelFilter === lvl ? "btn-primary" : "btn-ghost"
                )}
                onClick={() => setLevelFilter(lvl)}
              >
                {lvl === "all" ? `All (${state.logs.length})` : `${lvl} (${levelCounts[lvl]})`}
              </button>
            )
          )}
        </div>

        {/* Log Console Card */}
        <div className="card flex-1 min-h-0 !p-0 flex flex-col">
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-md"
            onScroll={() => {
              if (!scrollRef.current) return;
              const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
              setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
            }}
          >
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-text-muted">
                <ScrollText className="w-10 h-10 opacity-30 mb-md" />
                <p className="text-body">No log entries match your filter.</p>
              </div>
            ) : (
              <div className="space-y-[1px]">
                {filtered.map((log) => (
                  <LogRow key={log.id} log={log} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function SummaryWidget({
  label,
  value,
  variant,
}: {
  label: string;
  value: string;
  variant: "cyan" | "danger" | "success";
}) {
  const colors = {
    cyan: "border-accent-cyan/20 bg-accent-cyan/5",
    danger: "border-danger/20 bg-danger/5",
    success: "border-success/20 bg-success/5",
  };
  const textColor = {
    cyan: "text-accent-cyan",
    danger: "text-danger",
    success: "text-success",
  };

  return (
    <div className={cn("rounded-btn border p-md", colors[variant])}>
      <span className={cn("text-[10px] font-bold uppercase tracking-wider block", textColor[variant])}>
        {label}
      </span>
      <span className="text-small text-text-primary font-mono truncate block mt-[2px]">
        {value}
      </span>
    </div>
  );
}
