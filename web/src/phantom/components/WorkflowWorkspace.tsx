import { getLab } from "../lib/rf-lab";
import { findingsFor } from "../lib/scoring";
import { usePhantom } from "../lib/store";
import { nextStep, STAGE_FLOW, visualStage } from "../lib/ui-flow";
import { cn } from "../../lib/utils";
import { PacketDrawer } from "./PacketDrawer";
import { PrimaryAction } from "./PrimaryAction";
import { StatusBadge } from "./StatusBadge";
import type { BadgeTone } from "./StatusBadge";

export function WorkflowWorkspace() {
  const tick = usePhantom((s) => s.tick);
  const stage = usePhantom((s) => s.stage);
  const poaOk = usePhantom((s) => s.poaOk);
  const targetBssid = usePhantom((s) => s.targetBssid);
  const captures = usePhantom((s) => s.captures);
  const verify = usePhantom((s) => s.verify);
  const handshake = usePhantom((s) => s.handshake);
  const workflow = usePhantom((s) => s.workflow);
  const workflowStep = usePhantom((s) => s.workflowStep);
  const reports = usePhantom((s) => s.reports);
  const activeReport = usePhantom((s) => s.activeReport);
  const openPoA = usePhantom((s) => s.openPoA);
  const startScan = usePhantom((s) => s.startScan);
  const stopScan = usePhantom((s) => s.stopScan);
  const capture = usePhantom((s) => s.capture);
  const verifyTarget = usePhantom((s) => s.verifyTarget);
  const generateReport = usePhantom((s) => s.generateReport);
  const setOverlay = usePhantom((s) => s.setOverlay);
  const cancelWorkflow = usePhantom((s) => s.cancelWorkflow);
  const deauth = usePhantom((s) => s.deauth);
  void tick;

  const lab = getLab();
  const ap = lab.aps.find((a) => a.bssid === targetBssid) ?? null;
  const cap = captures.find((c) => c.bssid === targetBssid);
  const current = visualStage(stage);
  const step = nextStep({
    poaOk,
    scanning: lab.scanning,
    apCount: lab.visibleAps().length,
    target: ap,
    capture: cap,
    verify,
    hasReport: Boolean(activeReport || reports[0]),
    workflow,
  });

  const findings = ap ? findingsFor(ap, cap?.passphrase ?? verify?.passphrase) : [];
  const topFinding = [...findings].sort((a, b) => sevRank(a.severity) - sevRank(b.severity))[0];
  const showPrimary = step.kind !== "target" && step.kind !== "idle";

  const runPrimary = () => {
    switch (step.kind) {
      case "poa":
        openPoA(true);
        return;
      case "scan":
        startScan("passive");
        return;
      case "stop":
        stopScan();
        return;
      case "capture":
        void capture(false);
        return;
      case "analyze":
        void verifyTarget();
        return;
      case "report":
        if (!activeReport) generateReport();
        setOverlay("report");
        return;
      default:
        return;
    }
  };

  return (
    <main className="workspace">
      <div className="workspace-inner">
        <ol className="hidden flex-wrap items-center gap-2 text-xs lg:flex" aria-label="Current workflow">
          {STAGE_FLOW.map((s, i) => (
            <li key={s.id} className="flex items-center gap-2">
              <span
                className={cn(
                  s.id === current ? "font-medium text-fg" : i < STAGE_FLOW.findIndex((x) => x.id === current) ? "text-muted" : "text-muted/50",
                )}
              >
                {s.label}
              </span>
              {i < STAGE_FLOW.length - 1 ? <span className="text-line">→</span> : null}
            </li>
          ))}
        </ol>

        <section className="workflow-card">
          {ap ? (
            <div className="mb-6">
              <p className="kicker">Target status</p>
              <h1 className="mt-2 truncate text-xl font-semibold tracking-tight text-fg">
                {ap.hidden && !ap.revealedSsid ? "Hidden SSID" : ap.ssid}
              </h1>
              <p className="mt-1 font-mono text-xs text-muted">{ap.bssid}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusBadge
                  label={poaOk && ap.inScope ? "Authorized" : "Out of scope"}
                  tone={ap.inScope && poaOk ? "success" : "warning"}
                />
                <StatusBadge label={ap.encryption} tone={encTone(ap.encryption)} />
                <StatusBadge label={`${ap.rssi} dBm`} tone={ap.rssi < -75 ? "warning" : "neutral"} />
              </div>
            </div>
          ) : (
            <div className="mb-6">
              <p className="kicker">Target status</p>
              <h1 className="mt-2 text-xl font-semibold tracking-tight text-fg">No target selected</h1>
            </div>
          )}

          <p className="kicker">{workflow ? `Playbook · ${workflowStep || "running"}` : "Current workflow"}</p>
          <h2 className="mt-2 text-lg font-medium text-fg">{headline(step.kind, ap?.ssid)}</h2>
          <p className="mt-2 max-w-prose text-sm text-pretty text-muted">{step.hint}</p>
          {lab.scanning ? (
            <p className="mt-2 text-sm text-muted tabular-nums">{lab.visibleAps().length} access points discovered</p>
          ) : null}

          {topFinding ? (
            <div className="mt-6">
              <p className="kicker">Finding</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <h3 className="text-base font-medium text-fg">{topFinding.title}</h3>
                <StatusBadge label={topFinding.severity} tone={sevTone(topFinding.severity)} />
              </div>
              <p className="mt-2 hidden text-sm text-pretty text-muted sm:block">{topFinding.detail}</p>
            </div>
          ) : null}

          {verify?.running ? (
            <div className="mt-6">
              <div className="flex justify-between gap-3 text-xs text-muted">
                <span className="truncate font-mono">{verify.current ?? "Dictionary"}</span>
                <span className="shrink-0 tabular-nums">
                  {verify.tried}/{verify.total || "—"} · {verify.hps.toFixed(1)} H/s
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-sm bg-raised">
                <div
                  className="h-full bg-accent transition-[width] duration-150 ease-out"
                  style={{ width: `${verify.total ? Math.min(100, (verify.tried / verify.total) * 100) : 8}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {showPrimary ? (
              <PrimaryAction onClick={runPrimary}>{step.label}</PrimaryAction>
            ) : (
              <p className="text-sm text-muted">
                {step.kind === "target" ? "Select an access point from the target list." : step.hint}
              </p>
            )}
            {ap && step.kind === "capture" ? (
              <PrimaryAction quiet onClick={deauth}>
                Force reauth
              </PrimaryAction>
            ) : null}
            {workflow ? (
              <PrimaryAction quiet onClick={cancelWorkflow}>
                Cancel playbook
              </PrimaryAction>
            ) : null}
            {lab.scanning && step.kind !== "stop" ? (
              <PrimaryAction quiet onClick={stopScan}>
                Stop recon
              </PrimaryAction>
            ) : null}
            {activeReport && stage === "REPORT" ? (
              <PrimaryAction quiet onClick={() => setOverlay("report")}>
                Open full report
              </PrimaryAction>
            ) : null}
          </div>

          {verify?.status === "hit" && (verify.passphrase || cap?.passphrase) ? (
            <div className="mt-6">
              <p className="kicker">Result</p>
              <p className="mt-2 text-base font-medium text-fg">Passphrase recovered</p>
              <p className="mt-1 font-mono text-sm text-danger">{verify.passphrase ?? cap?.passphrase}</p>
              <p className="mt-2 text-sm text-pretty text-muted">
                Rotate the PSK for {cap?.ssid ?? ap?.ssid ?? "this network"} and revoke reused credentials.
              </p>
            </div>
          ) : null}

          {activeReport && stage === "REPORT" ? (
            <div className="mt-6">
              <p className="kicker">Result</p>
              <p className="mt-2 text-sm text-pretty text-fg">{activeReport.executiveSummary}</p>
            </div>
          ) : null}

          {cap ? (
            <div className="mt-6">
              <p className="kicker">Capture</p>
              <p className="mt-2 text-sm text-fg">
                {cap.method}
                <span className="mx-2 text-muted">·</span>
                <span className="font-mono text-xs text-muted">
                  M1{handshake.m1 ? "●" : "○"} M2{handshake.m2 ? "●" : "○"} M3{handshake.m3 ? "●" : "○"} M4
                  {handshake.m4 ? "●" : "○"}
                </span>
              </p>
            </div>
          ) : null}
        </section>

        <PacketDrawer />
      </div>
    </main>
  );
}

function headline(kind: string, ssid?: string) {
  switch (kind) {
    case "poa":
      return "Authorization required";
    case "scan":
      return "Ready to survey the spectrum";
    case "stop":
      return "Recon in progress";
    case "target":
      return "Inventory available";
    case "capture":
      return `Triage ${ssid ?? "target"}`;
    case "analyze":
      return "Cryptographic material captured";
    case "report":
      return "Ready to report";
    default:
      return "Working";
  }
}

function encTone(enc: string): BadgeTone {
  if (enc === "OPEN" || enc === "WEP" || enc === "WPA-TKIP") return "danger";
  if (enc.startsWith("WPA2-PSK")) return "warning";
  if (enc.includes("ENT") || enc === "WPA3-SAE") return "success";
  return "neutral";
}

function sevTone(s: string): BadgeTone {
  if (s === "critical" || s === "high") return "danger";
  if (s === "medium") return "warning";
  return "neutral";
}

function sevRank(s: string): number {
  if (s === "critical") return 0;
  if (s === "high") return 1;
  if (s === "medium") return 2;
  if (s === "low") return 3;
  return 4;
}
