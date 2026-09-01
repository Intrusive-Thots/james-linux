import { clamp, isLocallyAdministered, seeded, toHex } from "./bytes";
import { buildSignedHandshake, EAPOL_MIC_OFFSET } from "./crypto";
import { CHANNELS, instantiateAps, instantiateStas } from "./environment";
import { buildBeacon, buildDeauth, buildEapolFrame, buildProbe, captureHashes } from "./frames";
import { scoreAp } from "./scoring";
import { apInScope, poaValid } from "./poa";
import type {
  AccessPoint,
  Band,
  CaptureRecord,
  Encryption,
  FrameRecord,
  HandshakeProgress,
  RadioAdapter,
  SignedPoA,
  Station,
  Vec2,
} from "./types";

export interface LabSnapshot {
  t: number;
  operator: Vec2;
  aps: AccessPoint[];
  stas: Station[];
  adapters: RadioAdapter[];
  frames: FrameRecord[];
  scanning: boolean;
  scanMode: "off" | "passive" | "active";
}

function pathLoss(distM: number, freqMhz: number): number {
  const d = Math.max(distM, 0.5);
  const n = freqMhz > 5000 ? 2.8 : 2.4;
  const fspl1m = 20 * Math.log10(freqMhz) - 28;
  const walls = Math.min(18, Math.floor(d / 12) * 4);
  return fspl1m + 10 * n * Math.log10(d) + walls;
}

function freqMhz(band: Band, channel: number): number {
  if (band === "2.4") return 2407 + channel * 5;
  if (band === "5") return 5000 + channel * 5;
  return 5955 + channel * 5;
}

function dist(a: Vec2, b: Vec2): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

const FRAME_CAP = 48;

export class RfLab {
  operator: Vec2 = { x: 60, y: 42 };
  aps: AccessPoint[];
  stas: Station[];
  adapters: RadioAdapter[];
  frames: FrameRecord[] = [];
  scanning = false;
  scanMode: "off" | "passive" | "active" = "off";
  t = 0;
  poa: SignedPoA | null = null;
  private rng: () => number;
  private hopIdx0 = 0;
  private hopIdx1 = 0;
  private dwell0 = 0;
  private dwell1 = 0;
  private seq = 1;
  private listeners = new Set<() => void>();

  constructor(seed = 0x50484e54) {
    this.rng = seeded(seed);
    this.aps = instantiateAps();
    this.stas = instantiateStas();
    this.adapters = [
      {
        phy: "phy0",
        iface: "wlan0mon",
        bands: ["2.4", "5"],
        state: "MONITOR",
        channel: 1,
        band: "2.4",
        hopHz: 5,
        rxPackets: 0,
        txPackets: 0,
        drops: 0,
      },
      {
        phy: "phy1",
        iface: "wlan1mon",
        bands: ["5", "6"],
        state: "MONITOR",
        channel: 36,
        band: "5",
        hopHz: 5,
        rxPackets: 0,
        txPackets: 0,
        drops: 0,
      },
    ];
    this.refreshRf(0);
  }

  subscribe(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit() {
    for (const fn of this.listeners) fn();
  }

  setPoA(poa: SignedPoA | null) {
    this.poa = poa;
    this.applyScope();
    this.lockTx();
    this.emit();
  }

  private lockTx() {
    const unlocked = poaValid(this.poa);
    for (const a of this.adapters) {
      if (a.state === "DOWN") continue;
      a.state = unlocked ? "MONITOR" : "TX_LOCKED";
    }
  }

  applyScope() {
    for (const ap of this.aps) {
      ap.inScope = apInScope(ap, this.poa);
      const s = scoreAp(ap);
      ap.risk = s.risk;
      ap.riskReasons = s.reasons;
    }
  }

  snapshot(): LabSnapshot {
    return {
      t: this.t,
      operator: { ...this.operator },
      aps: this.aps,
      stas: this.stas,
      adapters: this.adapters,
      frames: this.frames,
      scanning: this.scanning,
      scanMode: this.scanMode,
    };
  }

  startScan(mode: "passive" | "active") {
    if (mode === "active" && !poaValid(this.poa)) {
      throw new Error("active scan requires a valid PoA signature");
    }
    this.scanning = true;
    this.scanMode = mode;
    this.lockTx();
    this.emit();
  }

  stopScan() {
    this.scanning = false;
    this.scanMode = "off";
    this.emit();
  }

  approach(bssid: string) {
    const ap = this.aps.find((a) => a.bssid === bssid);
    if (!ap) return;
    const d = dist(this.operator, ap.position);
    if (d < 2) return;
    const step = Math.min(10, d - 1.5);
    const ux = (ap.position.x - this.operator.x) / d;
    const uy = (ap.position.y - this.operator.y) / d;
    this.operator.x += ux * step;
    this.operator.y += uy * step;
    this.refreshRf(0);
    this.emit();
  }

  private noiseFloor(band: Band): number {
    return band === "2.4" ? -92 : band === "5" ? -95 : -97;
  }

  private rssiOf(ap: AccessPoint): number {
    const f = freqMhz(ap.band, ap.channel);
    const pl = pathLoss(dist(this.operator, ap.position), f);
    const fade = Math.sin(this.t / 700 + ap.channel) * 2.2 + (this.rng() - 0.5) * 1.4;
    return clamp(Math.round(ap.txPowerDbm - pl + fade), -98, -18);
  }

  refreshRf(dt: number) {
    this.t += dt;
    const hop0 = this.adapters[0]!;
    const hop1 = this.adapters[1]!;
    for (const ap of this.aps) {
      const rssi = this.rssiOf(ap);
      ap.noise = this.noiseFloor(ap.band);
      ap.rssi = rssi;
      ap.snr = rssi - ap.noise;
      ap.clientCount = this.stas.filter((s) => s.associatedBssid === ap.bssid).length;
      const onHop =
        (ap.band === hop0.band && ap.channel === hop0.channel) || (ap.band === hop1.band && ap.channel === hop1.channel);
      if (this.scanning && onHop && rssi > ap.noise + 4) {
        ap.lastSeen = this.t;
        ap.packetCount += 1;
      }
    }
    for (const sta of this.stas) {
      const fade = (this.rng() - 0.5) * 3;
      sta.rssi = clamp(Math.round(-45 - dist(this.operator, sta.position) * 0.7 + fade), -95, -20);
      if (this.scanning) sta.lastSeen = this.t;
    }
    this.applyScope();
  }

  private hopRadio(radio: RadioAdapter, which: 0 | 1, dt: number) {
    const dwell = which === 0 ? (this.dwell0 += dt) : (this.dwell1 += dt);
    const period = 1000 / radio.hopHz;
    if (dwell < period) return;
    if (which === 0) this.dwell0 = 0;
    else this.dwell1 = 0;
    const bands = radio.bands;
    const pool: { band: Band; ch: number }[] = [];
    for (const b of bands) for (const ch of CHANNELS[b]) pool.push({ band: b, ch });
    const idx = which === 0 ? (this.hopIdx0 = (this.hopIdx0 + 1) % pool.length) : (this.hopIdx1 = (this.hopIdx1 + 1) % pool.length);
    const next = pool[idx]!;
    radio.band = next.band;
    radio.channel = next.ch;
  }

  private pushFrame(frame: FrameRecord) {
    this.frames.push(frame);
    if (this.frames.length > FRAME_CAP) this.frames.splice(0, this.frames.length - FRAME_CAP);
    const radio = this.adapters.find((a) => a.iface === frame.radio);
    if (radio) radio.rxPackets += 1;
    if (this.frames.length === FRAME_CAP) {
      const dropRadio = this.adapters[0]!;
      if (this.rng() < 0.04) dropRadio.drops += 1;
    }
  }

  tick(dt: number) {
    if (this.scanning) {
      this.hopRadio(this.adapters[0]!, 0, dt);
      this.hopRadio(this.adapters[1]!, 1, dt);
    }
    this.refreshRf(dt);
    if (this.scanning) this.emitBeacons();
    this.emit();
  }

  private emitBeacons() {
    const radios = this.adapters;
    for (const ap of this.aps) {
      const on = radios.some((r) => r.band === ap.band && r.channel === ap.channel);
      if (!on) continue;
      if (ap.rssi < ap.noise + 3) continue;
      if (this.rng() > 0.45) continue;
      const beacon = buildBeacon(ap, this.seq++, ap.rssi);
      this.pushFrame(beacon);
      if (this.scanMode === "active" && poaValid(this.poa) && this.rng() < 0.15) {
        for (const sta of this.stas) {
          if (this.rng() > 0.3) continue;
          if (!sta.probes.length) continue;
          const probeSsid = sta.probes[Math.floor(this.rng() * sta.probes.length)]!;
          this.pushFrame(buildProbe(sta.mac, probeSsid, ap.bssid, ap.channel, ap.band, sta.rssi, this.seq++));
          if (ap.hidden && probeSsid === ap.ssid) ap.revealedSsid = true;
        }
      } else if (ap.hidden) {
        for (const sta of this.stas) {
          if (sta.associatedBssid === ap.bssid || sta.probes.includes(ap.ssid)) {
            if (this.rng() < 0.25) {
              ap.revealedSsid = true;
              this.pushFrame(buildProbe(sta.mac, ap.ssid, ap.bssid, ap.channel, ap.band, sta.rssi, this.seq++));
            }
          }
        }
      }
    }
  }

  ingestLive(
    rows: {
      bssid: string;
      ssid: string;
      channel: number;
      encryption: Encryption;
      rssi: number;
      vendor: string;
      clientCount: number;
      wps: boolean;
    }[],
  ) {
    const now = Date.now();
    for (const row of rows) {
      const key = row.bssid.toLowerCase();
      const existing = this.aps.find((a) => a.bssid.toLowerCase() === key);
      if (existing) {
        existing.lastSeen = now;
        existing.rssi = row.rssi;
        existing.clientCount = row.clientCount;
        existing.packetCount += 1;
        existing.snr = row.rssi - existing.noise;
        existing.vendor = row.vendor || existing.vendor;
        if (this.poa) existing.inScope = apInScope(existing, this.poa);
        const scored = scoreAp(existing);
        existing.risk = scored.risk;
        existing.riskReasons = scored.reasons;
        continue;
      }
      const band: Band = row.channel <= 14 ? "2.4" : "5";
      const ap: AccessPoint = {
        id: `live-${key}`,
        ssid: row.ssid || "<hidden>",
        bssid: row.bssid,
        vendor: row.vendor,
        band,
        channel: row.channel,
        widthMhz: 20,
        encryption: row.encryption,
        cipher: "CCMP",
        akm: "PSK",
        pmf: "off",
        wps: row.wps,
        hidden: !row.ssid,
        revealedSsid: Boolean(row.ssid),
        txPowerDbm: 20,
        position: { x: 60, y: 40 },
        role: "live",
        notes: "Ingested from JAMES live radios.",
        beaconIntervalMs: 102,
        lastSeen: now,
        rssi: row.rssi,
        noise: -95,
        snr: row.rssi + 95,
        packetCount: 1,
        clientCount: row.clientCount,
        pmkidExposed: false,
        rogue: false,
        inScope: this.poa ? false : true,
        risk: 0,
        riskReasons: [],
      };
      if (this.poa) ap.inScope = apInScope(ap, this.poa);
      const scored = scoreAp(ap);
      ap.risk = scored.risk;
      ap.riskReasons = scored.reasons;
      this.aps.push(ap);
    }
  }

  visibleAps(): AccessPoint[] {
    return this.aps.filter((a) => a.lastSeen > 0);
  }

  lockChannel(bssid: string): boolean {
    const ap = this.aps.find((a) => a.bssid === bssid);
    if (!ap) return false;
    const radio = ap.band === "6" ? this.adapters[1]! : ap.band === "2.4" ? this.adapters[0]! : this.adapters[ap.channel >= 149 ? 1 : 0]!;
    radio.band = ap.band;
    radio.channel = ap.channel;
    radio.hopHz = 0;
    return true;
  }

  resumeHop() {
    this.adapters[0]!.hopHz = 5;
    this.adapters[1]!.hopHz = 5;
  }

  injectionAllowed(bssid: string): { ok: boolean; reason?: string } {
    if (!poaValid(this.poa)) return { ok: false, reason: "injection locked — no valid PoA" };
    const ap = this.aps.find((a) => a.bssid === bssid);
    if (!ap) return { ok: false, reason: "unknown BSSID" };
    if (!ap.inScope) return { ok: false, reason: "target is out of PoA scope" };
    return { ok: true };
  }

  injectDeauth(bssid: string, staMac?: string): FrameRecord[] {
    const gate = this.injectionAllowed(bssid);
    if (!gate.ok) throw new Error(gate.reason);
    const ap = this.aps.find((a) => a.bssid === bssid)!;
    const stas = this.stas.filter((s) => (staMac ? s.mac === staMac : s.associatedBssid === bssid));
    const targets = stas.length ? stas : [{ mac: staMac ?? "FF:FF:FF:FF:FF:FF", rssi: ap.rssi } as Station];
    const out: FrameRecord[] = [];
    for (const sta of targets) {
      const frame = buildDeauth(ap.bssid, sta.mac, ap.channel, ap.band, ap.rssi, this.seq++);
      this.pushFrame(frame);
      const radio = this.adapters.find((a) => a.iface === frame.radio);
      if (radio) radio.txPackets += 1;
      out.push(frame);
    }
    return out;
  }

  pickStation(ap: AccessPoint): Station {
    const assoc = this.stas.find((s) => s.associatedBssid === ap.bssid);
    if (assoc) return assoc;
    return {
      id: "synth",
      mac: "02:00:00:00:00:10",
      randomized: true,
      manufacturer: "Phantom STA",
      associatedBssid: ap.bssid,
      probes: [ap.ssid],
      position: ap.position,
      lastSeen: this.t,
      rssi: ap.rssi,
      seq: this.seq,
    };
  }

  async captureTarget(bssid: string, forceReauth: boolean): Promise<{
    capture: CaptureRecord | null;
    progress: HandshakeProgress;
    frames: FrameRecord[];
    error?: string;
  }> {
    const ap = this.aps.find((a) => a.bssid === bssid);
    if (!ap) return { capture: null, progress: emptyProgress(), frames: [], error: "unknown BSSID" };
    if (!ap.inScope) return { capture: null, progress: emptyProgress(), frames: [], error: "target is out of PoA scope" };

    this.lockChannel(bssid);

    if (forceReauth) {
      const gate = this.injectionAllowed(bssid);
      if (!gate.ok) return { capture: null, progress: emptyProgress(), frames: [], error: gate.reason };
      this.injectDeauth(bssid);
    }

    const pskCapable = ap.encryption === "WPA2-PSK" || ap.encryption === "WPA-TKIP" || ap.encryption === "WPA3-SAE";
    if (ap.encryption === "WPA3-SAE") {
      return {
        capture: null,
        progress: emptyProgress(),
        frames: [],
        error: "WPA3-SAE has no offline PSK hash. Configuration audit only.",
      };
    }
    if (ap.encryption === "WPA2-ENT" || ap.encryption === "WPA3-ENT") {
      return {
        capture: null,
        progress: emptyProgress(),
        frames: this.frames.slice(-6),
        error: "Enterprise AKM — no PSK material. Capture EAP identity in logs; skip dictionary stage.",
      };
    }
    if (ap.encryption === "OPEN" || ap.encryption === "OWE") {
      return {
        capture: null,
        progress: emptyProgress(),
        frames: [],
        error: "No pairwise handshake on an open BSS.",
      };
    }
    if (ap.encryption === "WEP") {
      return {
        capture: null,
        progress: emptyProgress(),
        frames: [],
        error: "WEP is a protocol finding — no WPA handshake to capture.",
      };
    }
    if (!pskCapable || !ap.psk) {
      return { capture: null, progress: emptyProgress(), frames: [], error: "no PSK material on this BSS" };
    }

    const sta = this.pickStation(ap);
    const material = await buildSignedHandshake({
      passphrase: ap.psk,
      ssid: ap.ssid,
      apMac: ap.bssid,
      staMac: sta.mac,
    });

    const frames: FrameRecord[] = [];
    const m1 = await buildEapolFrame({
      ap,
      staMac: sta.mac,
      msg: 1,
      anonce: material.anonce,
      snonce: material.snonce,
      pmkid: material.pmkid,
      rssi: ap.rssi,
      seq: this.seq++,
    });
    this.pushFrame(m1);
    frames.push(m1);

    const m2 = await buildEapolFrame({
      ap,
      staMac: sta.mac,
      msg: 2,
      anonce: material.anonce,
      snonce: material.snonce,
      kck: material.kck,
      rssi: ap.rssi,
      seq: this.seq++,
    });
    this.pushFrame(m2);
    frames.push(m2);

    const m3 = await buildEapolFrame({
      ap,
      staMac: sta.mac,
      msg: 3,
      anonce: material.anonce,
      snonce: material.snonce,
      kck: material.kck,
      rssi: ap.rssi,
      seq: this.seq++,
    });
    this.pushFrame(m3);
    frames.push(m3);

    const m4 = await buildEapolFrame({
      ap,
      staMac: sta.mac,
      msg: 4,
      anonce: material.anonce,
      snonce: material.snonce,
      kck: material.kck,
      rssi: ap.rssi,
      seq: this.seq++,
    });
    this.pushFrame(m4);
    frames.push(m4);

    const eapolOffset = findEapol(m2.bytes);
    const eapol2 = m2.bytes.subarray(eapolOffset);
    const hashes = captureHashes({
      ssid: ap.ssid,
      apMac: ap.bssid,
      staMac: sta.mac,
      pmkid: material.pmkid,
      anonce: material.anonce,
      eapol2,
    });

    const method = ap.pmkidExposed ? "PMKID" : "EAPOL-4WAY";
    const capture: CaptureRecord = {
      id: `cap-${Date.now().toString(36)}-${toHex(material.pmkid).slice(0, 6)}`,
      bssid: ap.bssid,
      ssid: ap.ssid,
      staMac: sta.mac,
      encryption: ap.encryption,
      capturedAt: Date.now(),
      method,
      pmkidHex: toHex(material.pmkid),
      anonceHex: toHex(material.anonce),
      snonceHex: toHex(material.snonce),
      micHex: toHex(eapol2.subarray(EAPOL_MIC_OFFSET, EAPOL_MIC_OFFSET + 16)),
      eapol2,
      frame: m2.bytes,
      hc22000: method === "PMKID" ? hashes.pmkidLine : hashes.eapolLine,
      complete: true,
      verified: false,
    };

    return {
      capture,
      progress: { m1: true, m2: true, m3: true, m4: true, pmkid: ap.pmkidExposed },
      frames,
    };
  }

  spectrum(band: Band): { channel: number; energy: number }[] {
    const channels = CHANNELS[band];
    return channels.map((ch) => {
      const energy = this.aps
        .filter((a) => a.band === band && a.channel === ch && a.lastSeen > 0)
        .reduce((m, a) => Math.max(m, clamp((a.rssi + 95) / 75, 0, 1)), 0);
      return { channel: ch, energy };
    });
  }
}

function emptyProgress(): HandshakeProgress {
  return { m1: false, m2: false, m3: false, m4: false, pmkid: false };
}

function findEapol(bytes: Uint8Array): number {
  for (let i = 0; i < bytes.length - 3; i++) {
    if (bytes[i] === 0x88 && bytes[i + 1] === 0x8e) return i + 2;
  }
  return Math.max(0, bytes.length - 99);
}

export function isRandomMac(mac: string): boolean {
  return isLocallyAdministered(mac);
}

let singleton: RfLab | null = null;

export function getLab(): RfLab {
  if (!singleton) singleton = new RfLab();
  return singleton;
}

export function resetLab(): RfLab {
  singleton = new RfLab();
  return singleton;
}
