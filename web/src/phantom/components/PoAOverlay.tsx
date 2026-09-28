import { useEffect, useState } from "react";
import { labRoeTemplate, makeEngagementId } from "../lib/poa";
import { usePhantom } from "../lib/store";
import type { RulesOfEngagement } from "../lib/types";
import { PrimaryAction } from "./PrimaryAction";

export function PoAOverlay() {
  const open = usePhantom((s) => s.poaOpen);
  const poa = usePhantom((s) => s.poa);
  const poaOk = usePhantom((s) => s.poaOk);
  const close = usePhantom((s) => s.openPoA);
  const signLab = usePhantom((s) => s.signLabPoA);
  const signCustom = usePhantom((s) => s.signCustomPoA);
  const revoke = usePhantom((s) => s.revokePoA);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<RulesOfEngagement>(() => labRoeTemplate("ops"));

  useEffect(() => {
    if (open && !poa) setForm(labRoeTemplate("ops"));
  }, [open, poa]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open) return null;

  const set = (k: keyof RulesOfEngagement, v: string | boolean | string[]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      await signCustom(form);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-auto bg-canvas/80 p-4"
      onClick={() => close(false)}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="poa-title"
        className="max-h-svh w-full max-w-xl overflow-auto rounded-xl bg-panel p-6 shadow-border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="poa-title" className="text-lg font-medium text-fg">
              Proof of Authorization
            </h2>
            <p className="mt-1 text-sm text-pretty text-muted">
              ECDSA P-256 signature over a canonical Rules of Engagement. Active scan and injection stay locked
              without a valid window and a non-empty scope.
            </p>
          </div>
          <button type="button" className="min-h-11 shrink-0 text-sm text-muted hover:text-fg" onClick={() => close(false)}>
            Dismiss
          </button>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <PrimaryAction disabled={busy} onClick={() => void signLab(form.operator || "ops")}>
            Sign lab range
          </PrimaryAction>
          <p className="text-xs text-muted">Hopper-* · OUI 00:1A:8C:* · planted rogue</p>
        </div>

        {poaOk && poa ? (
          <div className="mt-4 rounded-md bg-raised p-4 text-sm">
            <div className="text-fg">Active {poa.roe.engagementId}</div>
            <div className="mt-1 break-all font-mono text-2xs text-muted">sha256 {poa.hashSha256}</div>
            <PrimaryAction quiet className="mt-2" onClick={revoke}>
              Revoke signature
            </PrimaryAction>
          </div>
        ) : null}

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Field label="Engagement ID" value={form.engagementId} onChange={(v) => set("engagementId", v || makeEngagementId())} />
          <Field label="Operator" value={form.operator} onChange={(v) => set("operator", v)} />
          <Field label="Organization" value={form.organization} onChange={(v) => set("organization", v)} />
          <Field label="Authorization ref" value={form.authorizationRef} onChange={(v) => set("authorizationRef", v)} />
          <Field label="Valid from" value={form.validFrom} onChange={(v) => set("validFrom", v)} />
          <Field label="Valid until" value={form.validUntil} onChange={(v) => set("validUntil", v)} />
          <Field
            label="SSID patterns"
            value={form.ssids.join(", ")}
            onChange={(v) => set("ssids", v.split(",").map((s) => s.trim()).filter(Boolean))}
          />
          <Field
            label="BSSID patterns"
            value={form.bssids.join(", ")}
            onChange={(v) => set("bssids", v.split(",").map((s) => s.trim()).filter(Boolean))}
          />
        </div>
        <label className="mt-4 block text-xs text-muted">
          Notes
          <textarea
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
            className="mt-1 min-h-20 w-full rounded-md bg-raised px-3 py-2 text-sm text-fg"
          />
        </label>
        <label className="mt-4 flex min-h-11 items-center gap-2 text-sm text-fg">
          <input
            type="checkbox"
            checked={form.certified}
            onChange={(e) => set("certified", e.target.checked)}
            className="size-4 accent-accent"
          />
          I certify written authorization for the listed identifiers.
        </label>
        {err ? <p className="mt-2 text-sm text-danger">{err}</p> : null}
        <div className="mt-4">
          <PrimaryAction quiet disabled={busy} onClick={() => void submit()}>
            Sign custom RoE
          </PrimaryAction>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block text-xs text-muted">
      {label}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 h-11 w-full rounded-md bg-raised px-3 text-sm text-fg"
      />
    </label>
  );
}
