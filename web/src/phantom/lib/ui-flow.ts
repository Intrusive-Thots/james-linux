import type { AccessPoint, CaptureRecord, Stage, VerifyJob } from "./types";

export const STAGE_FLOW: { id: Stage; label: string }[] = [
  { id: "RECON", label: "Recon" },
  { id: "TRIAGE", label: "Triage" },
  { id: "CAPTURE", label: "Capture" },
  { id: "VERIFY", label: "Analysis" },
  { id: "REPORT", label: "Report" },
];

export function visualStage(stage: Stage): Stage {
  if (stage === "BOOT" || stage === "IDLE") return "RECON";
  return stage;
}

export function stageIndex(stage: Stage): number {
  const id = visualStage(stage);
  const i = STAGE_FLOW.findIndex((s) => s.id === id);
  return i < 0 ? 0 : i;
}

export interface NextStep {
  label: string;
  hint: string;
  kind: "poa" | "scan" | "stop" | "target" | "capture" | "analyze" | "report" | "idle";
}

export function nextStep(opts: {
  poaOk: boolean;
  scanning: boolean;
  apCount: number;
  target: AccessPoint | null;
  capture: CaptureRecord | undefined;
  verify: VerifyJob | null;
  hasReport: boolean;
  workflow: string | null;
}): NextStep {
  if (!opts.poaOk) {
    return {
      kind: "poa",
      label: "Authorize engagement",
      hint: "Sign a Rules of Engagement to unlock active scanning and injection.",
    };
  }
  if (opts.workflow) {
    return {
      kind: "idle",
      label: "Workflow running",
      hint: opts.workflow,
    };
  }
  if (opts.scanning && opts.apCount === 0) {
    return {
      kind: "stop",
      label: "Stop recon",
      hint: "Sweeping 2.4 / 5 / 6 GHz. Access points will appear in the target list.",
    };
  }
  if (opts.apCount === 0) {
    return {
      kind: "scan",
      label: "Start recon",
      hint: "Run a passive spectrum sweep to inventory nearby BSSIDs.",
    };
  }
  if (!opts.target) {
    return {
      kind: "target",
      label: "Select a target",
      hint: "Choose an in-scope access point from the list to continue triage.",
    };
  }
  if (!opts.capture) {
    return {
      kind: "capture",
      label: "Begin capture",
      hint: "Intercept EAPOL / PMKID material from the selected radio.",
    };
  }
  if (!opts.verify || opts.verify.status === "idle") {
    return {
      kind: "analyze",
      label: "Begin analysis",
      hint: "Verify captured material against the approved dictionary.",
    };
  }
  if (opts.verify.running) {
    return {
      kind: "idle",
      label: "Analyzing",
      hint: `Dictionary verification in progress (${opts.verify.tried} tried).`,
    };
  }
  if (!opts.hasReport) {
    return {
      kind: "report",
      label: "Generate report",
      hint: "Compile findings, captures, and remediations for this engagement.",
    };
  }
  return {
    kind: "report",
    label: "View report",
    hint: "Engagement report is ready to export.",
  };
}

export function severityLabel(s: "critical" | "high" | "medium" | "low" | "info"): string {
  return s[0]!.toUpperCase() + s.slice(1);
}
