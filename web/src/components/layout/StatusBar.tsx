import { memo } from "react";
import {
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

const StatusBarComponent = ({ state }: StatusBarProps) => {
  const lastLog = state.logs[state.logs.length - 1];

  return (
    <footer className="h-[28px] flex items-center px-md border-t border-border bg-bg-panel/80 flex-shrink-0 gap-md text-[11px]">
      {/* Last Log Entry — takes priority */}
      <div className="flex-1 min-w-0 flex items-center gap-sm">
        <Clock className="w-3 h-3 text-text-muted flex-shrink-0" />
        {lastLog ? (
          <span className={cn("truncate font-mono text-[10px]", LEVEL_COLORS[lastLog.level])}>
            [{lastLog.timestamp}] {lastLog.message}
          </span>
        ) : (
          <span className="text-text-muted font-mono text-[10px]">Ready</span>
        )}
      </div>

      <div className="h-2.5 w-px bg-border" />

      {/* Scan Status */}
      <div className="flex items-center gap-[4px]">
        <Activity
          className={cn(
            "w-3 h-3",
            state.scanning ? "text-accent-cyan" : "text-text-muted"
          )}
        />
        <span
          className={cn(
            "font-mono",
            state.scanning
              ? "text-accent-cyan font-medium"
              : "text-text-muted"
          )}
        >
          {state.scanning ? "SCAN" : "IDLE"}
        </span>
      </div>

      <div className="h-2.5 w-px bg-border" />

      {/* APs */}
      <div className="flex items-center gap-[4px]">
        <HardDrive className="w-3 h-3 text-text-muted" />
        <span className="text-text-secondary font-mono">{state.aps.length}</span>
      </div>
    </footer>
  );
};

export const StatusBar = memo(StatusBarComponent, (prev, next) => {
  const prevLastLog = prev.state.logs[prev.state.logs.length - 1];
  const nextLastLog = next.state.logs[next.state.logs.length - 1];
  return (
    prev.state.scanning === next.state.scanning &&
    prev.state.aps.length === next.state.aps.length &&
    prevLastLog?.id === nextLastLog?.id
  );
});
