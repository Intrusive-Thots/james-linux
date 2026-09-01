import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { getLab } from "../lib/rf-lab";
import { usePhantom } from "../lib/store";
import type { AccessPoint, Band, Encryption } from "../lib/types";
import { cn } from "../../lib/utils";
import { StatusBadge } from "./StatusBadge";

type EncFilter = "all" | "open" | "psk" | "ent" | "legacy";

export function TargetList() {
  const tick = usePhantom((s) => s.tick);
  const target = usePhantom((s) => s.targetBssid);
  const setTarget = usePhantom((s) => s.setTarget);
  const density = usePhantom((s) => s.density);
  const [q, setQ] = useState("");
  const [band, setBand] = useState<"all" | Band>("all");
  const [enc, setEnc] = useState<EncFilter>("all");
  const [signal, setSignal] = useState<"all" | "strong" | "weak">("all");
  const [filters, setFilters] = useState(false);
  const [details, setDetails] = useState(false);
  void tick;

  const lab = getLab();
  const aps = lab.visibleAps();
  const selected = aps.find((a) => a.bssid === target) ?? null;

  const filtered = useMemo(() => {
    return [...aps]
      .filter((a) => {
        const ssid = a.hidden && !a.revealedSsid ? "<hidden>" : a.ssid;
        if (
          q &&
          !ssid.toLowerCase().includes(q.toLowerCase()) &&
          !a.bssid.toLowerCase().includes(q.toLowerCase()) &&
          !a.vendor.toLowerCase().includes(q.toLowerCase())
        ) {
          return false;
        }
        if (band !== "all" && a.band !== band) return false;
        if (enc !== "all" && !encMatch(enc, a.encryption)) return false;
        if (signal === "strong" && a.rssi < -60) return false;
        if (signal === "weak" && a.rssi > -75) return false;
        return true;
      })
      .sort((a, b) => {
        if (a.inScope !== b.inScope) return a.inScope ? -1 : 1;
        return b.risk - a.risk;
      });
  }, [aps, q, band, enc, signal]);

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col bg-panel">
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-medium text-fg">Targets</h2>
          <span className="text-2xs text-muted tabular-nums">{filtered.length}</span>
        </div>
        <label className="relative mt-3 block">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search SSID or vendor"
            className="h-11 w-full rounded-md bg-raised pr-3 pl-10 text-sm text-fg placeholder:text-muted"
          />
        </label>
        <button type="button" className="quiet-link mt-1 text-xs" onClick={() => setFilters((f) => !f)}>
          {filters ? "Hide filters" : "Filters"}
        </button>
        {filters ? (
          <div className="mt-2 grid grid-cols-1 gap-2">
            <FilterSelect
              label="Band"
              value={band}
              onChange={(v) => setBand(v as "all" | Band)}
              options={[
                ["all", "All bands"],
                ["2.4", "2.4 GHz"],
                ["5", "5 GHz"],
                ["6", "6 GHz"],
              ]}
            />
            <FilterSelect
              label="Security"
              value={enc}
              onChange={(v) => setEnc(v as EncFilter)}
              options={[
                ["all", "All security"],
                ["open", "Open"],
                ["psk", "PSK / SAE"],
                ["ent", "Enterprise"],
                ["legacy", "Legacy"],
              ]}
            />
            <FilterSelect
              label="Signal"
              value={signal}
              onChange={(v) => setSignal(v as "all" | "strong" | "weak")}
              options={[
                ["all", "Any signal"],
                ["strong", "Strong"],
                ["weak", "Weak"],
              ]}
            />
          </div>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-2 pb-3">
        {filtered.length === 0 ? (
          <p className="px-3 py-8 text-sm text-pretty text-muted">
            {aps.length === 0
              ? "No targets yet. Start recon to populate this list."
              : "No targets match the current filters."}
          </p>
        ) : (
          <ul className="flex flex-col">
            {filtered.map((ap) => (
              <TargetRow
                key={ap.bssid}
                ap={ap}
                selected={ap.bssid === target}
                compact={density === "compact"}
                onSelect={() => setTarget(ap.bssid)}
              />
            ))}
          </ul>
        )}
      </div>

      {selected ? (
        <div className="border-t border-line px-4 py-2">
          <button
            type="button"
            onClick={() => setDetails((d) => !d)}
            className="flex min-h-11 w-full items-center justify-between text-left text-sm text-muted hover:text-fg"
          >
            Target details
            <span>{details ? "Hide" : "Show"}</span>
          </button>
          {details ? (
            <dl className="grid grid-cols-2 gap-x-3 gap-y-2 pb-3 text-xs">
              <Row k="BSSID" v={selected.bssid} mono />
              <Row k="Vendor" v={selected.vendor} />
              <Row k="Channel" v={`${selected.band} / ${selected.channel}`} />
              <Row k="PMF" v={selected.pmf} />
              <Row k="Clients" v={String(selected.clientCount)} />
              <Row k="Risk" v={String(selected.risk)} />
              <div className="col-span-2 text-pretty text-muted">{selected.notes}</div>
            </dl>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

function TargetRow({
  ap,
  selected,
  compact,
  onSelect,
}: {
  ap: AccessPoint;
  selected: boolean;
  compact: boolean;
  onSelect: () => void;
}) {
  const ssid = ap.hidden && !ap.revealedSsid ? "Hidden SSID" : ap.ssid;
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        disabled={!ap.inScope}
        className={cn(
          "flex w-full items-center gap-3 px-3 text-left transition-colors duration-150",
          compact ? "min-h-12 py-1.5" : "min-h-14 py-2",
          selected ? "bg-raised shadow-select" : "hover:bg-raised/40",
          !ap.inScope && "opacity-50",
        )}
      >
        <SignalBars rssi={ap.rssi} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm text-fg">{ssid}</div>
          <div className="truncate text-xs text-muted">
            {ap.vendor}
            <span className="mx-1 text-line">·</span>
            ch {ap.channel}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-2xs text-muted">{ap.encryption}</div>
          {ap.rogue ? <StatusBadge label="Rogue" tone="danger" className="mt-1" /> : null}
        </div>
      </button>
    </li>
  );
}

function SignalBars({ rssi }: { rssi: number }) {
  const n = rssi > -55 ? 4 : rssi > -65 ? 3 : rssi > -75 ? 2 : rssi > -85 ? 1 : 0;
  const heights = ["h-1.5", "h-2.5", "h-3.5", "h-4"] as const;
  return (
    <div className="flex h-4 items-end gap-0.5" aria-label={`${rssi} dBm`}>
      {heights.map((h, i) => (
        <span key={h} className={cn("w-1 rounded-sm", h, i < n ? "bg-accent" : "bg-line")} />
      ))}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full rounded-md bg-raised px-2 text-xs text-fg"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-muted">{k}</dt>
      <dd className={cn("truncate text-fg", mono && "font-mono text-2xs")}>{v}</dd>
    </div>
  );
}

function encMatch(f: EncFilter, e: Encryption): boolean {
  if (f === "open") return e === "OPEN" || e === "OWE";
  if (f === "psk") return e === "WPA2-PSK" || e === "WPA3-SAE" || e === "WPA3-TRANS";
  if (f === "ent") return e === "WPA2-ENT" || e === "WPA3-ENT";
  if (f === "legacy") return e === "WEP" || e === "WPA-TKIP";
  return true;
}
