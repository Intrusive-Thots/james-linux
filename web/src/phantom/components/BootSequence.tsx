import { useEffect } from "react";
import { PrimaryAction } from "./PrimaryAction";

export function BootSequence({ onDone }: { onDone: () => void }) {
  useEffect(() => {
    const skip = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") onDone();
    };
    window.addEventListener("keydown", skip);
    const t = window.setTimeout(onDone, 2200);
    return () => {
      window.removeEventListener("keydown", skip);
      window.clearTimeout(t);
    };
  }, [onDone]);

  return (
    <div className="flex min-h-dvh flex-col items-start justify-center bg-canvas px-8 text-fg md:px-16">
      <p className="kicker">Hopper Industries</p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Phantom</h1>
      <p className="mt-2 max-w-md text-base text-pretty text-muted">
        Wireless security orchestrator. Authorized engagements only.
      </p>
      <PrimaryAction className="mt-8" onClick={onDone}>
        Continue
      </PrimaryAction>
    </div>
  );
}
