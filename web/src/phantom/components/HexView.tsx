import { hexDumpLines } from "../lib/bytes";
import type { FrameRecord } from "../lib/types";
import { cn } from "../../lib/utils";

export function HexView({ frame }: { frame: FrameRecord | null }) {
  if (!frame) {
    return <div className="flex h-full items-center justify-center px-4 text-sm text-muted">No packets captured yet.</div>;
  }
  const lines = hexDumpLines(frame.bytes);
  const spans = frame.highlight;
  const isHi = (idx: number, j: number) => {
    const abs = idx + j;
    return spans.some((h) => abs >= h.start && abs < h.end);
  };
  return (
    <div className="h-full overflow-auto px-4 py-3 font-mono text-2xs leading-5">
      <div className="mb-2 text-xs text-muted">
        {frame.kind}
        {frame.eapolMsg ? ` M${frame.eapolMsg}` : ""} {frame.src} → {frame.dst} · ch{frame.channel} · {frame.bytes.length}B
      </div>
      {lines.map((ln) => (
        <div key={ln.offset} className="flex gap-3">
          <span className="w-8 shrink-0 text-muted">{ln.offset}</span>
          <span className="min-w-0 flex-1">
            {ln.hex.split(" ").map((tok, j) => {
              if (!tok) return <span key={j} className="inline-block w-2" />;
              const hi = tok !== "  " && isHi(ln.idx, j > 8 ? j - 1 : j);
              return (
                <span key={j} className={cn("mr-1", hi ? "text-accent" : "text-fg")}>
                  {tok}
                </span>
              );
            })}
          </span>
          <span className="hidden w-32 shrink-0 text-muted lg:block">{ln.ascii}</span>
        </div>
      ))}
    </div>
  );
}
