import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils";

export function CollapsibleDrawer({
  title,
  meta,
  open,
  onToggle,
  children,
  className,
}: {
  title: string;
  meta?: string;
  open: boolean;
  onToggle: () => void;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex min-h-11 w-full items-center gap-2 text-left text-sm text-muted hover:text-fg"
      >
        <ChevronRight
          className={cn("size-4 shrink-0 transition-transform duration-150 ease-out", open && "rotate-90")}
        />
        <span>{title}</span>
        {meta ? <span className="ml-auto truncate font-mono text-2xs text-muted tabular-nums">{meta}</span> : null}
      </button>
      {open ? children : null}
    </div>
  );
}
