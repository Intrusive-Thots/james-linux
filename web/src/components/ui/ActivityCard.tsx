import { memo } from "react";
import { Activity, Crosshair, AlertCircle, CheckCircle2 } from "lucide-react";
import type { AppState } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface ActivityCardProps {
  state: AppState;
  className?: string;
}

const ActivityCardComponent = ({ state, className }: ActivityCardProps) => {
  const recentLogs = state.logs.slice(-3);

  // Derive agent status
  const isScanning = state.scanning;
  const isAttacking =
    state.attack.stage === "capturing" || state.attack.stage === "cracking";
  const agentStatus = isAttacking
    ? "ATTACKING"
    : isScanning
      ? "SCANNING"
      : state.attack.stage === "complete"
        ? "COMPLETE"
        : "IDLE";

  const statusColor = {
    ATTACKING: "text-danger",
    SCANNING: "text-accent-cyan",
    COMPLETE: "text-success",
    IDLE: "text-text-muted",
  }[agentStatus];

  const statusDot = {
    ATTACKING: "status-dot-danger",
    SCANNING: "status-dot-active",
    COMPLETE: "status-dot-success",
    IDLE: "status-dot-idle",
  }[agentStatus];

  // Current task
  const currentTask = isAttacking
    ? `${state.attack.stage_name || state.attack.stage} — ${state.attack.progress}%`
    : isScanning
      ? "Area reconnaissance active"
      : "No active task";

  return (
    <div
      className={cn(
        "bg-bg-panel/80 border border-border rounded-card p-md space-y-sm",
        "max-h-[220px] overflow-hidden",
        className
      )}
      style={{
        boxShadow: "0 0 0 1px rgba(255,255,255,0.02), 0 4px 16px rgba(0,0,0,0.3)",
      }}
    >
      {/* Agent Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-sm">
          <Crosshair className={cn("w-4 h-4", statusColor)} />
          <span className="text-xs font-bold uppercase tracking-wider text-text-secondary">
            Agent Status
          </span>
        </div>
        <div className="flex items-center gap-[6px]">
          <span className={statusDot} />
          <span
            className={cn(
              "text-[10px] font-bold uppercase tracking-wider font-mono",
              statusColor,
              (isAttacking || isScanning) && "scanning-pulse"
            )}
          >
            {agentStatus}
          </span>
        </div>
      </div>

      {/* Current Task */}
      <div className="bg-bg-elevated/60 border border-border-subtle rounded-tag px-sm py-[6px]">
        <span className="text-[10px] text-text-muted font-semibold uppercase block">
          Current Task
        </span>
        <span className="text-small text-text-primary font-mono truncate block">
          {currentTask}
        </span>
      </div>

      {/* Recent Events */}
      <div>
        <span className="text-[10px] text-text-muted font-semibold uppercase block mb-[4px]">
          Recent Events
        </span>
        <div className="space-y-[2px]">
          {recentLogs.length === 0 ? (
            <span className="text-xs text-text-muted font-mono">No events</span>
          ) : (
            recentLogs.map((log) => (
              <div
                key={log.id}
                className="flex items-start gap-[4px] text-[10px] font-mono leading-tight"
              >
                {log.level === "error" ? (
                  <AlertCircle className="w-3 h-3 text-danger flex-shrink-0 mt-[1px]" />
                ) : log.level === "success" ? (
                  <CheckCircle2 className="w-3 h-3 text-success flex-shrink-0 mt-[1px]" />
                ) : (
                  <Activity className="w-3 h-3 text-text-muted flex-shrink-0 mt-[1px]" />
                )}
                <span className="text-text-secondary truncate">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export const ActivityCard = memo(ActivityCardComponent, (prev, next) => {
  return (
    prev.className === next.className &&
    prev.state.scanning === next.state.scanning &&
    prev.state.attack.stage === next.state.attack.stage &&
    prev.state.attack.progress === next.state.attack.progress &&
    prev.state.attack.stage_name === next.state.attack.stage_name &&
    prev.state.logs.length === next.state.logs.length &&
    prev.state.logs[prev.state.logs.length - 1]?.id === next.state.logs[next.state.logs.length - 1]?.id
  );
});
