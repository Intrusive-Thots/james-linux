import type { AccessPoint, Finding } from "./types";
import { clamp } from "./bytes";

export function scoreAp(ap: AccessPoint): { risk: number; reasons: string[] } {
  const reasons: string[] = [];
  let s = 0;
  switch (ap.encryption) {
    case "OPEN":
      s += ap.rogue ? 96 : 88;
      reasons.push(ap.rogue ? "Open evil-twin of a corporate SSID" : "Open authentication");
      break;
    case "WEP":
      s += 94;
      reasons.push("WEP is cryptographically broken");
      break;
    case "WPA-TKIP":
      s += 82;
      reasons.push("Deprecated WPA-TKIP");
      break;
    case "WPA2-PSK":
      s += 48;
      reasons.push("WPA2-PSK (offline dictionary feasible)");
      if (ap.pmkidExposed) {
        s += 14;
        reasons.push("PMKID exposed in EAPOL M1");
      }
      if (ap.pmf === "off") {
        s += 8;
        reasons.push("802.11w / PMF disabled");
      }
      break;
    case "WPA2-ENT":
      s += 22;
      if (ap.pmf !== "required") {
        s += 16;
        reasons.push("Enterprise without mandatory PMF");
      }
      break;
    case "WPA3-TRANS":
      s += 28;
      reasons.push("WPA3 transition mode allows downgrade");
      break;
    case "WPA3-SAE":
      s += 8;
      break;
    case "WPA3-ENT":
      s += 5;
      break;
    case "OWE":
      s += 18;
      reasons.push("Opportunistic wireless encryption only");
      break;
  }
  if (ap.wps) {
    s += 12;
    reasons.push("WPS enabled");
  }
  if (ap.hidden) {
    s += 4;
    reasons.push("Hidden SSID (security by obscurity)");
  }
  if (ap.rssi > -50) {
    s += 4;
    reasons.push("High proximity (RSSI > -50 dBm)");
  }
  if (ap.clientCount > 4) s += 3;
  return { risk: clamp(Math.round(s), 0, 99), reasons };
}

export function findingsFor(ap: AccessPoint, recovered?: string): Finding[] {
  const out: Finding[] = [];
  const base = { bssid: ap.bssid, ssid: ap.ssid };
  if (ap.rogue) {
    out.push({
      id: `rogue-${ap.bssid}`,
      severity: "critical",
      title: "Rogue / evil-twin access point",
      ...base,
      detail: `${ap.ssid} advertised from ${ap.bssid} (${ap.vendor}) with ${ap.encryption}. Corporate OUI does not match Hopper Networks.`,
      remediation: `Deauthenticate clients from ${ap.bssid}, locate the transmitter, and add a rogue-AP rule on the WLC for SSID Hopper-Corp with non-Hopper OUIs.`,
    });
  }
  if (ap.encryption === "WEP") {
    out.push({
      id: `wep-${ap.bssid}`,
      severity: "critical",
      title: "WEP in use",
      ...base,
      detail: "WEP key recovery is trivial. This radio must not carry any operational traffic.",
      remediation: `Retire AP ${ap.bssid}. Migrate the printer/IoT endpoint to Hopper-IoT with WPA3-SAE or a wired drop.`,
    });
  }
  if (ap.encryption === "OPEN" && !ap.rogue) {
    out.push({
      id: `open-${ap.bssid}`,
      severity: "high",
      title: "Open SSID",
      ...base,
      detail: "No link-layer authentication or encryption.",
      remediation: "Move to OWE (enhanced open) or WPA3-SAE with a published guest onboarding flow.",
    });
  }
  if (ap.encryption === "WPA-TKIP") {
    out.push({
      id: `tkip-${ap.bssid}`,
      severity: "high",
      title: "WPA-TKIP",
      ...base,
      detail: "TKIP is deprecated and MIC attacks remain practical.",
      remediation: `Reconfigure ${ap.ssid} to CCMP-only or WPA3-SAE. Disable TKIP on the SSID profile.`,
    });
  }
  if (ap.encryption === "WPA2-PSK" && ap.pmf !== "required") {
    out.push({
      id: `pmf-${ap.bssid}`,
      severity: "medium",
      title: "Protected Management Frames disabled",
      ...base,
      detail: "Deauthentication and disassociation frames are not protected.",
      remediation: "Set 802.11w to Required on this SSID (clients permitting) or migrate to WPA3-SAE.",
    });
  }
  if (ap.wps) {
    out.push({
      id: `wps-${ap.bssid}`,
      severity: "high",
      title: "WPS enabled",
      ...base,
      detail: "WPS PIN/PBC exposes an additional offline attack surface.",
      remediation: "Disable WPS on the AP and block WPS IEs at the controller.",
    });
  }
  if (ap.encryption === "WPA2-ENT" && ap.pmf !== "required") {
    out.push({
      id: `ent-pmf-${ap.bssid}`,
      severity: "medium",
      title: "Enterprise PMF not required",
      ...base,
      detail: ap.notes,
      remediation: "Force 802.11w required and disable the WPA2 transition radio once clients are inventoried.",
    });
  }
  if (recovered) {
    out.push({
      id: `psk-${ap.bssid}`,
      severity: "critical",
      title: "PSK recovered against approved dictionary",
      ...base,
      detail: `Passphrase recovered for ${ap.ssid} (${ap.bssid}). Complexity fails organizational baseline.`,
      remediation: `Revoke and rotate PSK for SSID ${ap.ssid}. Migrate AP ${ap.bssid} to WPA3-SAE or WPA3-Enterprise. Do not reuse the recovered secret.`,
    });
  }
  if (ap.hidden) {
    out.push({
      id: `hidden-${ap.bssid}`,
      severity: "low",
      title: "Hidden SSID",
      ...base,
      detail: "SSID hidden in beacons; recovered via client probe correlation.",
      remediation: "Broadcast the SSID. Hiding it does not prevent discovery and complicates legitimate ops.",
    });
  }
  return out;
}

export function prioritize(aps: AccessPoint[]): AccessPoint[] {
  return [...aps].sort((a, b) => {
    if (a.inScope !== b.inScope) return a.inScope ? -1 : 1;
    return b.risk - a.risk || b.rssi - a.rssi;
  });
}
