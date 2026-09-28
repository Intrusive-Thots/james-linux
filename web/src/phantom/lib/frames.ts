import { concat, macToBytes, utf8, toHex, randomBytes } from "./bytes";
import { EAPOL_MIC_OFFSET, eapolMic, formatHc22000Eapol, formatHc22000Pmkid } from "./crypto";
import type { AccessPoint, Band, FrameRecord } from "./types";

function u16le(n: number): Uint8Array {
  return Uint8Array.of(n & 0xff, (n >> 8) & 0xff);
}

function radiotap(rssi: number, channel: number, band: Band): Uint8Array {
  const freq = band === "2.4" ? 2407 + channel * 5 : band === "5" ? 5000 + channel * 5 : 5950 + channel * 5;
  const hdr = new Uint8Array(16);
  hdr[2] = 16;
  hdr[4] = 0x2e;
  hdr[8] = rssi & 0xff;
  hdr[10] = freq & 0xff;
  hdr[11] = (freq >> 8) & 0xff;
  return hdr;
}

function dot11Header(fc: number, dur: number, a1: string, a2: string, a3: string, seq: number): Uint8Array {
  return concat(u16le(fc), u16le(dur), macToBytes(a1), macToBytes(a2), macToBytes(a3), u16le(seq << 4));
}

function tagged(id: number, data: Uint8Array): Uint8Array {
  return concat(Uint8Array.of(id, data.length), data);
}

export function buildBeacon(ap: AccessPoint, seq: number, rssi: number): FrameRecord {
  const ssidBytes = ap.hidden && !ap.revealedSsid ? new Uint8Array(0) : utf8(ap.ssid);
  const body = concat(
    new Uint8Array(8),
    u16le(ap.beaconIntervalMs),
    u16le(ap.encryption === "OPEN" ? 0x0411 : 0x0431),
    tagged(0, ssidBytes),
    tagged(1, Uint8Array.of(0x82, 0x84, 0x8b, 0x96, 0x0c, 0x12, 0x18, 0x24)),
    tagged(3, Uint8Array.of(ap.channel)),
  );
  const mac = dot11Header(0x0080, 0, "FF:FF:FF:FF:FF:FF", ap.bssid, ap.bssid, seq);
  const bytes = concat(radiotap(rssi, ap.channel, ap.band), mac, body);
  return {
    ts: Date.now(),
    radio: ap.band === "6" ? "wlan1mon" : "wlan0mon",
    channel: ap.channel,
    band: ap.band,
    rssi,
    kind: "BEACON",
    src: ap.bssid,
    dst: "FF:FF:FF:FF:FF:FF",
    bssid: ap.bssid,
    bytes,
    highlight: [],
  };
}

export function buildProbe(sta: string, ssid: string, bssid: string, channel: number, band: Band, rssi: number, seq: number): FrameRecord {
  const body = tagged(0, utf8(ssid));
  const mac = dot11Header(0x0040, 0, "FF:FF:FF:FF:FF:FF", sta, bssid, seq);
  const bytes = concat(radiotap(rssi, channel, band), mac, body);
  return {
    ts: Date.now(),
    radio: band === "6" ? "wlan1mon" : "wlan0mon",
    channel,
    band,
    rssi,
    kind: "PROBE",
    src: sta,
    dst: "FF:FF:FF:FF:FF:FF",
    bssid,
    bytes,
    highlight: [],
  };
}

export function buildDeauth(ap: string, sta: string, channel: number, band: Band, rssi: number, seq: number): FrameRecord {
  const mac = dot11Header(0x00c0, 0x013a, sta, ap, ap, seq);
  const reason = u16le(7);
  const bytes = concat(radiotap(rssi, channel, band), mac, reason);
  return {
    ts: Date.now(),
    radio: band === "6" ? "wlan1mon" : "wlan0mon",
    channel,
    band,
    rssi,
    kind: "DEAUTH",
    src: ap,
    dst: sta,
    bssid: ap,
    bytes,
    highlight: [],
  };
}

export function buildEapolKey(opts: {
  version?: number;
  keyInfo: number;
  keyLen: number;
  replay: number;
  nonce: Uint8Array;
  mic: Uint8Array;
  keyData?: Uint8Array;
}): Uint8Array {
  const keyData = opts.keyData ?? new Uint8Array(0);
  const bodyLen = 95 + keyData.length;
  const buf = new Uint8Array(4 + bodyLen);
  buf[0] = opts.version ?? 2;
  buf[1] = 3;
  buf[2] = (bodyLen >> 8) & 0xff;
  buf[3] = bodyLen & 0xff;
  buf[4] = 2;
  buf[5] = (opts.keyInfo >> 8) & 0xff;
  buf[6] = opts.keyInfo & 0xff;
  buf[7] = (opts.keyLen >> 8) & 0xff;
  buf[8] = opts.keyLen & 0xff;
  for (let i = 0; i < 8; i++) buf[9 + i] = 0;
  buf[16] = opts.replay & 0xff;
  buf.set(opts.nonce.subarray(0, 32), 17);
  buf.set(opts.mic.subarray(0, 16), 81);
  buf[97] = (keyData.length >> 8) & 0xff;
  buf[98] = keyData.length & 0xff;
  if (keyData.length) buf.set(keyData, 99);
  return buf;
}

const LLC_SNAP_EAPOL = Uint8Array.of(0xaa, 0xaa, 0x03, 0x00, 0x00, 0x00, 0x88, 0x8e);

export async function buildEapolFrame(opts: {
  ap: AccessPoint;
  staMac: string;
  msg: 1 | 2 | 3 | 4;
  anonce: Uint8Array;
  snonce: Uint8Array;
  kck?: Uint8Array;
  pmkid?: Uint8Array;
  rssi: number;
  seq: number;
}): Promise<FrameRecord> {
  const zeros16 = new Uint8Array(16);
  const zeros32 = new Uint8Array(32);
  let keyInfo = 0x008a;
  let nonce = zeros32;
  let keyData = new Uint8Array(0);
  if (opts.msg === 1) {
    keyInfo = 0x008a;
    nonce = new Uint8Array(opts.anonce);
    if (opts.pmkid) {
      keyData = new Uint8Array(concat(Uint8Array.of(0xdd, 0x14, 0x00, 0x0f, 0xac, 0x04), opts.pmkid));
    }
  } else if (opts.msg === 2) {
    keyInfo = 0x010a;
    nonce = new Uint8Array(opts.snonce);
  } else if (opts.msg === 3) {
    keyInfo = 0x13ca;
    nonce = new Uint8Array(opts.anonce);
  } else {
    keyInfo = 0x030a;
    nonce = zeros32;
  }

  let eapol = buildEapolKey({
    keyInfo,
    keyLen: 16,
    replay: opts.msg,
    nonce,
    mic: zeros16,
    keyData,
  });

  if (opts.kck && opts.msg !== 1) {
    const mic = await eapolMic(opts.kck, eapol);
    eapol = new Uint8Array(eapol);
    eapol.set(mic, EAPOL_MIC_OFFSET);
  }

  const qos = u16le(0);
  const mac = concat(
    dot11Header(0x0088, 0, opts.msg % 2 === 1 ? opts.staMac : opts.ap.bssid, opts.msg % 2 === 1 ? opts.ap.bssid : opts.staMac, opts.ap.bssid, opts.seq),
    qos,
  );
  const payload = concat(LLC_SNAP_EAPOL, eapol);
  const bytes = concat(radiotap(opts.rssi, opts.ap.channel, opts.ap.band), mac, payload);
  const eapolStart = bytes.length - eapol.length;
  return {
    ts: Date.now(),
    radio: opts.ap.band === "6" ? "wlan1mon" : "wlan0mon",
    channel: opts.ap.channel,
    band: opts.ap.band,
    rssi: opts.rssi,
    kind: "EAPOL",
    src: opts.msg % 2 === 1 ? opts.ap.bssid : opts.staMac,
    dst: opts.msg % 2 === 1 ? opts.staMac : opts.ap.bssid,
    bssid: opts.ap.bssid,
    bytes,
    eapolMsg: opts.msg,
    highlight: [{ start: eapolStart, end: bytes.length }],
  };
}

export function captureHashes(opts: {
  ssid: string;
  apMac: string;
  staMac: string;
  pmkid: Uint8Array;
  anonce: Uint8Array;
  eapol2: Uint8Array;
}): { pmkidLine: string; eapolLine: string } {
  const ap = macToBytes(opts.apMac);
  const sta = macToBytes(opts.staMac);
  const mic = opts.eapol2.subarray(EAPOL_MIC_OFFSET, EAPOL_MIC_OFFSET + 16);
  return {
    pmkidLine: formatHc22000Pmkid(opts.pmkid, ap, sta, opts.ssid),
    eapolLine: formatHc22000Eapol(mic, ap, sta, opts.ssid, opts.anonce, opts.eapol2),
  };
}

export function randomNonce(): Uint8Array {
  return randomBytes(32);
}

export function describeFrame(frame: FrameRecord): string {
  const n = frame.bytes.length;
  if (frame.kind === "EAPOL") {
    return `${frame.kind} M${frame.eapolMsg ?? "?"} ${frame.src} → ${frame.dst} ch${frame.channel} ${n}B RSSI ${frame.rssi}`;
  }
  return `${frame.kind} ${frame.src} → ${frame.dst} ch${frame.channel} ${n}B RSSI ${frame.rssi}`;
}

export { toHex };
