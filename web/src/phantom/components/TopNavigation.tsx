import type { ReactNode } from "react";
import { List, Activity } from "lucide-react";
import { getLab } from "../lib/rf-lab";
import { usePhantom } from "../lib/store";
import type { Stage } from "../lib/types";
import { STAGE_FLOW, visualStage } from "../lib/ui-flow";
import { cn } from "../../lib/utils";
import { AppMenu } from "./AppMenu";
import { StatusBadge } from "./StatusBadge";

export function TopNavigation({
  showTargetToggle,
  showStatusToggle,
  targetsOpen,
  statusOpen,
  onTargets,
  onStatus,
}: {
  showTargetToggle: boolean;
  showStatusToggle: boolean;
  targetsOpen: boolean;
  statusOpen: boolean;
  onTargets: () => void;
  onStatus: () => void;
}) {
  const stage = usePhantom((s) => s.stage);
  const poaOk = usePhantom((s) => s.poaOk);
  const setStage = usePhantom((s) => s.setStage);
  const openPoA = usePhantom((s) => s.openPoA);
  const current = visualStage(stage);
  const scanning = getLab().scanning;

  return (
    <header className="flex min-h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-4">
      <div className="min-w-0 shrink-0 pr-2">
        <div className="text-sm font-semibold tracking-tight text-fg">Phantom</div>
        <div className="hidden text-2xs text-muted sm:block">Wireless security</div>
      </div>

      <nav className="ml-1 hidden min-w-0 flex-1 items-center gap-1 lg:flex" aria-label="Workflow stages">
        {STAGE_FLOW.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStage(s.id)}
            aria-current={current === s.id ? "step" : undefined}
            className={cn(
              "min-h-11 rounded-md px-3 text-sm transition-colors duration-150",
              current === s.id ? "bg-raised text-fg" : "text-muted hover:bg-raised/60 hover:text-fg",
            )}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <div className="ml-auto flex shrink-0 items-center gap-1">
        {scanning ? <span className="hidden pr-2 text-xs text-muted sm:inline">Scanning</span> : null}
        <button type="button" onClick={() => openPoA(true)} className="min-h-11 px-1" aria-label="Authorization">
          <StatusBadge label={poaOk ? "Authorized" : "Locked"} tone={poaOk ? "success" : "warning"} />
        </button>
        {showTargetToggle ? (
          <IconToggle label="Targets" pressed={targetsOpen} onClick={onTargets}>
            <List className="size-5" />
          </IconToggle>
        ) : null}
        {showStatusToggle ? (
          <IconToggle label="Status" pressed={statusOpen} onClick={onStatus}>
            <Activity className="size-5" />
          </IconToggle>
        ) : null}
        <AppMenu />
      </div>
    </header>
  );
}

function IconToggle({
  label,
  pressed,
  onClick,
  children,
}: {
  label: string;
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        "inline-flex size-11 items-center justify-center rounded-md",
        pressed ? "bg-raised text-fg" : "text-muted hover:bg-raised hover:text-fg",
      )}
    >
      {children}
    </button>
  );
}

export function MobileStageNav({ stage, onStage }: { stage: Stage; onStage: (s: Stage) => void }) {
  const current = visualStage(stage);
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-line px-3 py-1 lg:hidden" aria-label="Workflow stages">
      {STAGE_FLOW.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onStage(s.id)}
          aria-current={current === s.id ? "step" : undefined}
          className={cn(
            "min-h-11 shrink-0 rounded-md px-3 text-sm",
            current === s.id ? "bg-raised text-fg" : "text-muted",
          )}
        >
          {s.label}
        </button>
      ))}
    </nav>
  );
}
