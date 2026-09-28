import { useEffect } from "react";
import { getLab } from "../lib/rf-lab";
import { downloadText, reportMarkdown } from "../lib/reports";
import { usePhantom } from "../lib/store";
import type { Band } from "../lib/types";
import { cn } from "../../lib/utils";
import { PrimaryAction } from "./PrimaryAction";
import { StatusBadge } from "./StatusBadge";

export function OverlayModals() {
  const overlay = usePhantom((s) => s.overlay);
  const setOverlay = usePhantom((s) => s.setOverlay);

  useEffect(() => {
    if (!overlay) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOverlay(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [overlay, setOverlay]);

  if (!overlay) return null;

  const title =
    overlay === "telemetry"
      ? "Telemetry"
      : overlay === "events"
        ? "Audit log"
        : overlay === "report"
          ? "Engagement report"
          : "Radios";

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center overflow-auto bg-canvas/80 p-4"
      onClick={() => setOverlay(null)}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="overlay-title"
        className="max-h-svh w-full max-w-2xl overflow-auto rounded-xl bg-panel p-6 shadow-border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="overlay-title" className="text-lg font-medium text-fg">
            {title}
          </h2>
          <button type="button" className="min-h-11 text-sm text-muted hover:text-fg" onClick={() => setOverlay(null)}>
            Close
          </button>
        </div>
        {overlay === "telemetry" && <TelemetryBody />}
        {overlay === "events" && <EventsBody />}
        {overlay === "report" && <ReportBody />}
        {overlay === "adapters" && <AdaptersBody />}
      </div>
    </div>
  );
}

function TelemetryBody() {
  const telemetry = usePhantom((s) => s.telemetry);
  const tick = usePhantom((s) => s.tick);
  void tick;
  const lab = getLab();
  if (lab.adapters.length === 0) {
    return <p className="mt-4 text-sm text-muted">Telemetry unavailable.</p>;
  }
  return (
    <div className="mt-4 space-y-6">
      <p className="text-sm text-muted">{telemetry.backend}</p>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <Stat k="CPU" v={`${telemetry.cpuPct.toFixed(0)}%`} />
        <Stat k="Hashrate" v={`${telemetry.gpuHashrate.toFixed(1)} H/s`} />
        <Stat k="Inject" v={`${telemetry.injectPps.toFixed(2)} pps`} />
        <Stat k="Drop rate" v={`${(telemetry.dropRate * 100).toFixed(2)}%`} />
        <Stat k="Hop" v={`${telemetry.hopBand} / ch ${telemetry.hopChannel}`} />
        <Stat k="Capture ratio" v={`${(telemetry.captureRatio * 100).toFixed(0)}%`} />
      </dl>
      <div className="grid gap-4 sm:grid-cols-2">
        <Spectrum band="2.4" />
        <Spectrum band="5" />
      </div>
      <ul className="space-y-2 text-sm">
        {lab.adapters.map((a) => (
          <li key={a.phy} className="flex justify-between gap-3 text-muted">
            <span className="font-mono text-fg">
              {a.iface} {a.band}/{a.channel}
            </span>
            {a.state} · rx {a.rxPackets} · tx {a.txPackets}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Spectrum({ band }: { band: Band }) {
  const tick = usePhantom((s) => s.tick);
  void tick;
  const data = getLab().spectrum(band);
  const hop = getLab().adapters.find((a) => a.band === band);
  return (
    <div>
      <div className="mb-2 flex justify-between text-xs text-muted">
        <span>{band} GHz</span>
        <span>{hop ? `ch ${hop.channel}` : ""}</span>
      </div>
      <div className="flex h-16 items-end gap-px">
        {data.map((d) => (
          <div key={d.channel} className="flex min-w-0 flex-1 flex-col items-center justify-end">
            <div
              className={cn("w-full rounded-sm", hop?.channel === d.channel ? "bg-accent" : "bg-accent/40")}
              style={{ height: `${Math.max(8, d.energy * 100)}%` }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function EventsBody() {
  const logs = usePhantom((s) => s.logs);
  if (!logs.length) return <p className="mt-4 text-sm text-muted">No events recorded.</p>;
  return (
    <ul className="mt-4 max-h-96 space-y-3 overflow-auto">
      {logs
        .slice()
        .reverse()
        .map((e) => (
          <li key={e.id} className="text-sm">
            <span className="font-mono text-2xs text-muted tabular-nums">{new Date(e.ts).toISOString().slice(11, 19)}</span>
            <span className="ml-2 text-muted">{e.code}</span>
            <p className="text-pretty text-fg">{e.message}</p>
          </li>
        ))}
    </ul>
  );
}

function ReportBody() {
  const report = usePhantom((s) => s.activeReport);
  const generateReport = usePhantom((s) => s.generateReport);
  if (!report) {
    return (
      <div className="mt-4">
        <p className="text-sm text-muted">No report generated yet.</p>
        <PrimaryAction className="mt-4" onClick={() => generateReport()}>
          Generate report
        </PrimaryAction>
      </div>
    );
  }
  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-pretty text-fg">{report.executiveSummary}</p>
      <ul className="max-h-64 space-y-2 overflow-auto">
        {report.findings.map((f) => (
          <li key={f.id} className="text-sm">
            <StatusBadge
              label={f.severity}
              tone={f.severity === "critical" || f.severity === "high" ? "danger" : f.severity === "medium" ? "warning" : "neutral"}
            />
            <span className="ml-2 text-fg">{f.title}</span>
            <p className="mt-1 text-xs text-pretty text-muted">{f.remediation}</p>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <PrimaryAction onClick={() => downloadText(`phantom-${report.engagementId}.md`, reportMarkdown(report), "text/markdown")}>
          Export Markdown
        </PrimaryAction>
        <PrimaryAction
          quiet
          onClick={() =>
            downloadText(`phantom-${report.engagementId}.json`, JSON.stringify(report, jsonReplacer, 2), "application/json")
          }
        >
          Export JSON
        </PrimaryAction>
      </div>
    </div>
  );
}

function AdaptersBody() {
  const tick = usePhantom((s) => s.tick);
  void tick;
  const adapters = getLab().adapters;
  if (!adapters.length) return <p className="mt-4 text-sm text-muted">No radios available.</p>;
  return (
    <ul className="mt-4 space-y-3 text-sm">
      {adapters.map((a) => (
        <li key={a.phy} className="rounded-md bg-raised p-3">
          <div className="font-medium text-fg">
            {a.phy} · {a.iface}
          </div>
          <div className="mt-1 font-mono text-xs text-muted">
            {a.band} ch{a.channel} · {a.state} · rx {a.rxPackets} tx {a.txPackets} drop {a.drops}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-md bg-raised p-3">
      <dt className="text-xs text-muted">{k}</dt>
      <dd className="mt-1 text-base tabular-nums text-fg">{v}</dd>
    </div>
  );
}

function jsonReplacer(_k: string, v: unknown) {
  if (v instanceof Uint8Array) return Array.from(v);
  return v;
}
