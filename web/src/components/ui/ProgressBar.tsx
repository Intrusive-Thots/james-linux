import { cn } from "../../lib/utils";

interface ProgressBarProps {
  value: number; // 0-100
  variant?: "cyan" | "danger" | "success" | "warning";
  className?: string;
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
}

export function ProgressBar({
  value,
  variant = "cyan",
  className,
  showLabel = false,
  label,
  animated = false,
}: ProgressBarProps) {
  const colors = {
    cyan: "bg-accent-cyan",
    danger: "bg-danger",
    success: "bg-success",
    warning: "bg-warning",
  };

  const glows = {
    cyan: "shadow-[0_0_12px_rgba(34,211,238,0.4)]",
    danger: "shadow-[0_0_12px_rgba(239,68,68,0.4)]",
    success: "shadow-[0_0_12px_rgba(16,185,129,0.4)]",
    warning: "shadow-[0_0_12px_rgba(245,158,11,0.4)]",
  };

  return (
    <div className={cn("w-full", className)}>
      {(showLabel || label) && (
        <div className="flex justify-between mb-[6px]">
          {label && (
            <span className="text-small text-text-secondary">{label}</span>
          )}
          {showLabel && (
            <span className="text-small text-text-muted font-mono">
              {Math.round(value)}%
            </span>
          )}
        </div>
      )}
      <div className="w-full h-[6px] bg-bg-elevated rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            colors[variant],
            animated && glows[variant]
          )}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}
