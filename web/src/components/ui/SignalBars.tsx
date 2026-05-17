import { cn } from "../../lib/utils";

interface SignalBarsProps {
  power: number; // dBm, e.g. -42
  className?: string;
}

export function SignalBars({ power, className }: SignalBarsProps) {
  // -30 = excellent, -90 = terrible
  const normalized = Math.max(0, Math.min(100, ((power + 90) / 60) * 100));
  const bars = normalized > 80 ? 4 : normalized > 55 ? 3 : normalized > 30 ? 2 : 1;

  const barColor =
    bars >= 4
      ? "bg-success"
      : bars >= 3
        ? "bg-accent-cyan"
        : bars >= 2
          ? "bg-warning"
          : "bg-danger";

  return (
    <div className={cn("flex items-end gap-[2px] h-4", className)}>
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={cn(
            "signal-bar w-[3px] rounded-full transition-all duration-200",
            i <= bars ? barColor : "bg-bg-elevated"
          )}
          style={{ height: `${25 * i}%` }}
        />
      ))}
    </div>
  );
}
