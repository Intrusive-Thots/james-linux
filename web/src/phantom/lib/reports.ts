import { findingsFor } from "./scoring";
import type { AccessPoint, CaptureRecord, EngagementReport, Finding, SignedPoA } from "./types";

export function buildReport(opts: {
  poa: SignedPoA | null;
  aps: AccessPoint[];
  captures: CaptureRecord[];
  startedAt: number;
  operator: string;
}): EngagementReport {
  const visible = opts.aps.filter((a) => a.lastSeen > 0);
  const inScope = visible.filter((a) => a.inScope);
  const findings: Finding[] = [];
  const seen = new Set<string>();
  const recoveredByBssid = new Map(opts.captures.filter((c) => c.passphrase).map((c) => [c.bssid, c.passphrase!]));

  for (const ap of inScope.length ? inScope : visible.filter((a) => a.rogue || a.encryption === "WEP")) {
    for (const f of findingsFor(ap, recoveredByBssid.get(ap.bssid))) {
      if (seen.has(f.id)) continue;
      seen.add(f.id);
      findings.push(f);
    }
  }

  findings.sort((a, b) => rank(a.severity) - rank(b.severity));

  const recovered = opts.captures.filter((c) => c.passphrase).length;
  const crit = findings.filter((f) => f.severity === "critical").length;
  const high = findings.filter((f) => f.severity === "high").length;
  const executiveSummary = composeSummary({ visible, inScope, recovered, crit, high, poa: opts.poa });

  return {
    id: `RPT-${Date.now().toString(36).toUpperCase()}`,
    generatedAt: Date.now(),
    engagementId: opts.poa?.roe.engagementId ?? "UNSCOPED",
    poaHash: opts.poa?.hashSha256 ?? null,
    operator: opts.poa?.roe.operator ?? opts.operator,
    inventory: visible.map(stripSecret),
    captures: opts.captures.map((c) => ({ ...c, eapol2: new Uint8Array(c.eapol2), frame: new Uint8Array(c.frame) })),
    findings,
    metrics: {
      apsDiscovered: visible.length,
      inScope: inScope.length,
      captures: opts.captures.length,
      recovered,
      durationMs: Date.now() - opts.startedAt,
    },
    executiveSummary,
  };
}

function stripSecret(ap: AccessPoint): AccessPoint {
  const copy = { ...ap };
  delete copy.psk;
  return copy;
}

function rank(s: Finding["severity"]): number {
  return { critical: 0, high: 1, medium: 2, low: 3, info: 4 }[s];
}

function composeSummary(s: {
  visible: AccessPoint[];
  inScope: AccessPoint[];
  recovered: number;
  crit: number;
  high: number;
  poa: SignedPoA | null;
}): string {
  const ent = s.inScope.filter((a) => a.encryption === "WPA3-ENT" || a.encryption === "WPA2-ENT").length;
  const open = s.inScope.filter((a) => a.encryption === "OPEN").length;
  const rogue = s.visible.filter((a) => a.rogue).length;
  const parts = [
    `Engagement ${s.poa?.roe.engagementId ?? "UNSCOPED"} surveyed ${s.visible.length} BSSIDs (${s.inScope.length} in-scope).`,
    `${s.crit} critical and ${s.high} high findings.`,
    s.recovered
      ? `${s.recovered} PSK(s) recovered against the approved dictionary — rotate immediately.`
      : "No in-scope PSKs recovered from the approved dictionary.",
    ent ? `${ent} enterprise radio(s) observed.` : "",
    open ? `${open} open BSS(s) in-scope.` : "",
    rogue ? `${rogue} rogue/evil-twin transmitter(s) present.` : "",
  ];
  return parts.filter(Boolean).join(" ");
}

export function reportMarkdown(r: EngagementReport): string {
  const lines: string[] = [
    `# Phantom Wireless Security Report`,
    ``,
    `- Engagement: ${r.engagementId}`,
    `- Operator: ${r.operator}`,
    `- Generated: ${new Date(r.generatedAt).toISOString()}`,
    `- PoA SHA-256: ${r.poaHash ?? "unsigned"}`,
    ``,
    `## Executive summary`,
    r.executiveSummary,
    ``,
    `## Metrics`,
    `- APs discovered: ${r.metrics.apsDiscovered}`,
    `- In-scope: ${r.metrics.inScope}`,
    `- Captures: ${r.metrics.captures}`,
    `- Passphrases recovered: ${r.metrics.recovered}`,
    `- Duration: ${Math.round(r.metrics.durationMs / 1000)}s`,
    ``,
    `## Findings`,
  ];
  if (!r.findings.length) lines.push("_No findings._");
  for (const f of r.findings) {
    lines.push(`### [${f.severity.toUpperCase()}] ${f.title}`);
    lines.push(`- Target: ${f.ssid ?? "—"} (${f.bssid ?? "—"})`);
    lines.push(`- ${f.detail}`);
    lines.push(`- Remediation: ${f.remediation}`);
    lines.push("");
  }
  lines.push(`## Inventory`);
  lines.push(`| SSID | BSSID | Enc | Ch | RSSI | Risk | Scope |`);
  lines.push(`|---|---|---|---|---|---|---|`);
  for (const ap of r.inventory) {
    const ssid = ap.hidden && !ap.revealedSsid ? "<hidden>" : ap.ssid;
    lines.push(
      `| ${ssid} | ${ap.bssid} | ${ap.encryption} | ${ap.channel} | ${ap.rssi} | ${ap.risk} | ${ap.inScope ? "in" : "out"} |`,
    );
  }
  lines.push("");
  lines.push(`## Captures`);
  for (const c of r.captures) {
    lines.push(`- ${c.ssid} ${c.bssid} ${c.method} ${c.complete ? "complete" : "partial"} ${c.passphrase ? "RECOVERED" : "unverified"}`);
    lines.push(`  \`${c.hc22000}\``);
  }
  return lines.join("\n");
}

export function downloadText(filename: string, text: string, mime = "text/plain") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
