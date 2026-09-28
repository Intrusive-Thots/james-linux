import { getLab } from "../lib/rf-lab";
import { usePhantom } from "../lib/store";
import { StatusBadge } from "./StatusBadge";

export function StatusPanel() {
  const tick = usePhantom((s) => s.tick);
  const poaOk = usePhantom((s) => s.poaOk);
  const poa = usePhantom((s) => s.poa);
  const telemetry = usePhantom((s) => s.telemetry);
  const logs = usePhantom((s) => s.logs);
  const setOverlay = usePhantom((s) => s.setOverlay);
  const openPoA = usePhantom((s) => s.openPoA);
  void tick;
  const lab = getLab();
  const rx = lab.adapters.reduce((n, a) => n + a.rxPackets, 0);
  const recent = logs.slice(-5).reverse();

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col gap-8 overflow-auto bg-panel px-4 py-4">
      <section>
        <h2 className="kicker">Status</h2>
        <div className="mt-3 flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted">Authorization</span>
            <button type="button" onClick={() => openPoA(true)} className="min-h-11">
              <StatusBadge label={poaOk ? "Authorized" : "Locked"} tone={poaOk ? "success" : "warning"} />
            </button>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted">Radios</span>
            <StatusBadge label={lab.scanning ? "Scanning" : "Ready"} tone={lab.scanning ? "accent" : "neutral"} />
          </div>
          {poa ? <p className="truncate font-mono text-2xs text-muted">{poa.roe.engagementId}</p> : null}
        </div>
      </section>

      <section>
        <h2 className="kicker">Telemetry</h2>
        {lab.adapters.length === 0 ? (
          <p className="mt-3 text-sm text-muted">Telemetry unavailable.</p>
        ) : (
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Hashrate</dt>
              <dd className="tabular-nums text-fg">{telemetry.gpuHashrate.toFixed(1)} H/s</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Packets</dt>
              <dd className="tabular-nums text-fg">{rx.toLocaleString()}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Drops</dt>
              <dd className="tabular-nums text-fg">{(telemetry.dropRate * 100).toFixed(2)}%</dd>
            </div>
          </dl>
        )}
        <button type="button" className="quiet-link mt-1" onClick={() => setOverlay("telemetry")}>
          View telemetry
        </button>
      </section>

      <section className="min-h-0 flex-1">
        <h2 className="kicker">Recent activity</h2>
        {recent.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No events yet.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {recent.map((e) => (
              <li key={e.id} className="text-sm">
                <div className="flex items-start gap-2">
                  <span
                    className={
                      e.level === "crit"
                        ? "mt-1.5 size-1.5 shrink-0 rounded-full bg-danger"
                        : e.level === "warn"
                          ? "mt-1.5 size-1.5 shrink-0 rounded-full bg-warning"
                          : "mt-1.5 size-1.5 shrink-0 rounded-full bg-accent"
                    }
                  />
                  <div className="min-w-0">
                    <div className="text-fg">{labelFor(e.code)}</div>
                    <div className="truncate text-xs text-muted">{e.message}</div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
        <button type="button" className="quiet-link mt-1" onClick={() => setOverlay("events")}>
          View all events
        </button>
      </section>
    </aside>
  );
}

function labelFor(code: string): string {
  const map: Record<string, string> = {
    BOOT: "Console ready",
    POA_OK: "Authorization verified",
    POA_SIGNED: "Authorization signed",
    POA_MISSING: "Authorization missing",
    POA_REVOKED: "Authorization revoked",
    SCAN_START: "Recon started",
    SCAN_STOP: "Recon stopped",
    TARGET: "Target selected",
    HANDSHAKE_CAPTURED: "Capture complete",
    PSK_RECOVERED: "Passphrase recovered",
    VERIFY_START: "Analysis started",
    VERIFY_EXHAUSTED: "Dictionary exhausted",
    REPORT: "Report generated",
    WF_START: "Playbook started",
    WF_DONE: "Playbook complete",
    ROGUE: "Rogue detected",
    SCOPE_BLOCK: "Out of scope",
    DEAUTH: "Reauth injected",
  };
  return map[code] ?? code.replaceAll("_", " ").toLowerCase();
}
