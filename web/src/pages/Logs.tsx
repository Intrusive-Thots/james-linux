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

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.logs.length, autoScroll]);

  const filtered = useMemo(() => {
    const q = filter.toLowerCase();
    return state.logs.reduce((acc, log) => {
      if (levelFilter !== "all" && log.level !== levelFilter) return acc;
      if (q && !log.message.toLowerCase().includes(q)) return acc;
      acc.push(log);
      return acc;
    }, [] as LogEntry[]);
  }, [state.logs, filter, levelFilter]);

  const levelCounts = useMemo(() => {
    return state.logs.reduce(
      (acc, l) => {
        acc[l.level]++;
        return acc;
      },
      { info: 0, warn: 0, error: 0, success: 0 }
    );
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
              {state.logs.length} entries · Auto-scroll{" "}
              {autoScroll ? "ON" : "OFF"}
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

        {/* Filter Bar */}
        <div className="flex items-center gap-sm flex-shrink-0">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-[10px] top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search logs…"
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
