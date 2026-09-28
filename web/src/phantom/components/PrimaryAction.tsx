import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function PrimaryAction({
  className,
  children,
  quiet,
  danger,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { quiet?: boolean; danger?: boolean }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex min-h-11 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors duration-150 ease-out active:scale-95 disabled:pointer-events-none disabled:opacity-40",
        quiet
          ? "bg-transparent text-muted hover:bg-raised hover:text-fg"
          : danger
            ? "bg-danger text-fg hover:opacity-90"
            : "bg-accent text-accent-fg hover:opacity-90",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
