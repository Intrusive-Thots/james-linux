import { useState } from "react";
import { getLab } from "../lib/rf-lab";
import { usePhantom } from "../lib/store";
import { cn } from "../../lib/utils";
import { CollapsibleDrawer } from "./CollapsibleDrawer";
import { HexView } from "./HexView";

export function PacketDrawer() {
  const tick = usePhantom((s) => s.tick);
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState(0);
  void tick;
  const frames = getLab().frames;
  const recent = frames.slice(-24).reverse();
  const frame = recent[sel] ?? recent[0] ?? null;

  return (
    <CollapsibleDrawer
      title="Raw data"
      meta={`${frames.length} frames`}
      open={open}
      onToggle={() => setOpen((o) => !o)}
    >
      {frames.length === 0 ? (
        <p className="pb-4 text-sm text-muted">No packets captured yet.</p>
      ) : (
        <div className="grid min-h-0 gap-3 pb-4 lg:grid-cols-[12rem_minmax(0,1fr)]">
          <ul className="max-h-56 overflow-auto">
            {recent.map((f, i) => (
              <li key={`${f.ts}-${i}`}>
                <button
                  type="button"
                  onClick={() => setSel(i)}
                  className={cn(
                    "flex min-h-11 w-full items-center justify-between gap-2 rounded-md px-2 text-left text-xs",
                    i === sel ? "bg-raised text-fg" : "text-muted hover:text-fg",
                  )}
                >
                  <span>{f.kind}{f.eapolMsg ? ` M${f.eapolMsg}` : ""}</span>
                  <span className="font-mono text-2xs">ch{f.channel}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="h-56 overflow-hidden rounded-md bg-canvas">
            <HexView frame={frame} />
          </div>
        </div>
      )}
    </CollapsibleDrawer>
  );
}
