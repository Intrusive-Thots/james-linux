import { useEffect, useRef } from "react";
import {
  Wifi,
  Activity,
  HardDrive,
  Clock,
} from "lucide-react";
import type { LogEntry, AppState } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface StatusBarProps {
  state: AppState;
}

const LEVEL_COLORS: Record<LogEntry["level"], string> = {
  info: "text-accent-cyan",
  warn: "text-warning",
  error: "text-danger",
  success: "text-success",
};

export function StatusBar({ state }: StatusBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.logs.length]);

  const lastLog = state.logs[state.logs.length - 1];

  return (
    <footer className="h-[36px] flex items-center px-md border-t border-border bg-bg-panel/80 flex-shrink-0 gap-lg text-small">
      {/* Adapter Status */}
      <div className="flex items-center gap-sm">
        <Wifi className="w-3.5 h-3.5 text-text-muted" />
        <span className="text-text-secondary">
          {state.adapter ? (
            <>
              {state.adapter}
              <span className="text-text-muted ml-1">
                ({state.adapterMode || "–"})
              </span>
            </>
          ) : (
            "No adapter"
          )}
        </span>
      </div>

      <div className="h-3 w-px bg-border" />

      {/* Scan Status */}
      <div className="flex items-center gap-sm">
        <Activity
          className={cn(
            "w-3.5 h-3.5",
            state.scanning ? "text-accent-cyan" : "text-text-muted"
          )}
        />
        <span
          className={cn(
            state.scanning
              ? "text-accent-cyan font-medium"
              : "text-text-secondary"
          )}
        >
          {state.scanning ? "Scanning" : "Idle"}
        </span>
      </div>

      <div className="h-3 w-px bg-border" />

      {/* APs Found */}
      <div className="flex items-center gap-sm">
        <HardDrive className="w-3.5 h-3.5 text-text-muted" />
        <span className="text-text-secondary">{state.aps.length} APs</span>
      </div>

      <div className="h-3 w-px bg-border" />

      {/* Last Log Entry */}
      <div className="flex-1 min-w-0 flex items-center gap-sm">
        <Clock className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
        {lastLog ? (
          <span className={cn("truncate font-mono text-xs", LEVEL_COLORS[lastLog.level])}>
            [{lastLog.timestamp}] {lastLog.message}
          </span>
        ) : (
          <span className="text-text-muted font-mono text-xs">No log entries</span>
        )}
      </div>
    </footer>
  );
}
