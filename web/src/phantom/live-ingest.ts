import { getLab } from "./lib/rf-lab";
import { usePhantom } from "./lib/store";
import type { Encryption } from "./lib/types";

export interface JamesApIn {
  bssid: string;
  essid: string;
  channel: number;
  privacy: string;
  power: number;
  clients: number;
  vendor: string;
  wps?: boolean;
}

export interface JamesHandshakeIn {
  id?: string;
  essid?: string;
  bssid?: string;
  captured_at?: string;
  file_path?: string;
  cracked?: boolean;
  key?: string;
}

export function ingestJamesAps(aps: JamesApIn[]) {
  const lab = getLab();
  lab.ingestLive(
    aps.map((a) => ({
      bssid: a.bssid,
      ssid: a.essid,
      channel: a.channel,
      encryption: mapEnc(a.privacy),
      rssi: a.power,
      vendor: a.vendor || "Unknown",
      clientCount: a.clients || 0,
      wps: Boolean(a.wps),
    })),
  );
  usePhantom.setState({ tick: Date.now() });
  usePhantom.getState().log("info", "LIVE_SCAN", `${aps.length} live BSSID(s) from JAMES radios`);
}

export function ingestJamesHandshake(data: JamesHandshakeIn) {
  const s = usePhantom.getState();
  const bssid = data.bssid || s.targetBssid;
  if (!bssid) return;
  const ssid = data.essid || "unknown";
  if (data.cracked && data.key) {
    s.log("crit", "PSK_RECOVERED", `${ssid}  ${bssid}  live radio  ${data.key}`);
    s.setStage("VERIFY");
    usePhantom.setState({
      tick: Date.now(),
      verify: {
        captureId: data.id || `live-${bssid}`,
        running: false,
        tried: 1,
        total: 1,
        hps: 0,
        elapsedMs: 0,
        status: "hit",
        passphrase: data.key,
      },
      captures: [
        {
          id: data.id || `live-${bssid}`,
          bssid,
          ssid,
          staMac: "ff:ff:ff:ff:ff:ff",
          encryption: "WPA2-PSK",
          capturedAt: Date.now(),
          method: "EAPOL-4WAY",
          pmkidHex: "",
          anonceHex: "",
          snonceHex: "",
          micHex: "",
          eapol2: new Uint8Array(),
          frame: new Uint8Array(),
          hc22000: data.file_path || "",
          complete: true,
          verified: true,
          passphrase: data.key,
        },
        ...s.captures.filter((c) => c.bssid !== bssid),
      ],
    });
    return;
  }
  s.log("info", "HANDSHAKE_CAPTURED", `${ssid}  ${bssid}  live capture ${data.file_path || ""}`.trim());
  s.setStage("CAPTURE");
  usePhantom.setState({ tick: Date.now() });
}

function mapEnc(privacy: string): Encryption {
  const u = (privacy || "").toUpperCase();
  if (u.includes("WPA3") && u.includes("ENT")) return "WPA3-ENT";
  if (u.includes("TRANS")) return "WPA3-TRANS";
  if (u.includes("SAE") || u.includes("WPA3")) return "WPA3-SAE";
  if (u.includes("WPA2") && (u.includes("ENT") || u.includes("802.1X") || u.includes("EAP"))) return "WPA2-ENT";
  if (u.includes("TKIP")) return "WPA-TKIP";
  if (u.includes("WEP")) return "WEP";
  if (u.includes("OWE")) return "OWE";
  if (u.includes("OPN") || u.includes("OPEN")) return "OPEN";
  if (u.includes("WPA2") || u.includes("WPA")) return "WPA2-PSK";
  return "WPA2-PSK";
}
