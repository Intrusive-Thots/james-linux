export type Band = "2.4" | "5" | "6";

export type Encryption =
  | "OPEN"
  | "OWE"
  | "WEP"
  | "WPA-TKIP"
  | "WPA2-PSK"
  | "WPA2-ENT"
  | "WPA3-SAE"
  | "WPA3-ENT"
  | "WPA3-TRANS";

export type PmfMode = "off" | "optional" | "required";

export type Density = "comfortable" | "compact" | "focus";

export type OverlayKind = null | "telemetry" | "events" | "report" | "adapters";

export type Stage =
  | "BOOT"
  | "IDLE"
  | "RECON"
  | "TRIAGE"
  | "CAPTURE"
  | "VERIFY"
  | "REPORT";

export type LogLevel = "info" | "warn" | "crit";

export type AdapterState = "DOWN" | "UP" | "MONITOR" | "TX_LOCKED";

export interface Vec2 {
  x: number;
  y: number;
}

export interface AccessPoint {
  id: string;
  ssid: string;
  bssid: string;
  vendor: string;
  band: Band;
  channel: number;
  widthMhz: number;
  encryption: Encryption;
  cipher: string;
  akm: string;
  pmf: PmfMode;
  wps: boolean;
  hidden: boolean;
  revealedSsid: boolean;
  txPowerDbm: number;
  position: Vec2;
  role: string;
  notes: string;
  psk?: string;
  beaconIntervalMs: number;
  lastSeen: number;
  rssi: number;
  noise: number;
  snr: number;
  packetCount: number;
  clientCount: number;
  pmkidExposed: boolean;
  rogue: boolean;
  inScope: boolean;
  risk: number;
  riskReasons: string[];
}

export interface Station {
  id: string;
  mac: string;
  randomized: boolean;
  manufacturer: string;
  associatedBssid: string | null;
  probes: string[];
  position: Vec2;
  lastSeen: number;
  rssi: number;
  seq: number;
}

export interface RadioAdapter {
  phy: string;
  iface: string;
  bands: Band[];
  state: AdapterState;
  channel: number;
  band: Band;
  hopHz: number;
  rxPackets: number;
  txPackets: number;
  drops: number;
}

export interface FrameRecord {
  ts: number;
  radio: string;
  channel: number;
  band: Band;
  rssi: number;
  kind: "BEACON" | "PROBE" | "DATA" | "EAPOL" | "DEAUTH" | "DISASSOC";
  src: string;
  dst: string;
  bssid: string;
  bytes: Uint8Array;
  eapolMsg?: 1 | 2 | 3 | 4;
  highlight: { start: number; end: number }[];
}

export interface HandshakeProgress {
  m1: boolean;
  m2: boolean;
  m3: boolean;
  m4: boolean;
  pmkid: boolean;
}

export interface CaptureRecord {
  id: string;
  bssid: string;
  ssid: string;
  staMac: string;
  encryption: Encryption;
  capturedAt: number;
  method: "PMKID" | "EAPOL-4WAY" | "EAPOL-M1M2";
  pmkidHex: string;
  anonceHex: string;
  snonceHex: string;
  micHex: string;
  eapol2: Uint8Array;
  frame: Uint8Array;
  hc22000: string;
  complete: boolean;
  verified: boolean;
  passphrase?: string;
  pmkHex?: string;
}

export interface VerifyJob {
  captureId: string;
  running: boolean;
  tried: number;
  total: number;
  hps: number;
  elapsedMs: number;
  current?: string;
  status: "idle" | "running" | "hit" | "exhausted" | "aborted" | "unsupported";
  passphrase?: string;
  complexity?: ComplexityReport;
}

export interface ComplexityReport {
  length: number;
  classes: { lower: boolean; upper: boolean; digit: boolean; symbol: boolean };
  charsetSize: number;
  entropyBits: number;
  dictionaryHit: boolean;
  policyPass: boolean;
  verdict: "fail" | "weak" | "adequate" | "strong";
  notes: string[];
}

export interface LogEntry {
  id: number;
  ts: number;
  level: LogLevel;
  code: string;
  message: string;
}

export interface RulesOfEngagement {
  engagementId: string;
  operator: string;
  organization: string;
  authorizationRef: string;
  validFrom: string;
  validUntil: string;
  ssids: string[];
  bssids: string[];
  notes: string;
  certified: boolean;
}

export interface SignedPoA {
  roe: RulesOfEngagement;
  canonical: string;
  hashSha256: string;
  signatureDerHex: string;
  publicJwk: JsonWebKey;
  signedAt: number;
}

export interface Finding {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  bssid?: string;
  ssid?: string;
  detail: string;
  remediation: string;
}

export interface EngagementReport {
  id: string;
  generatedAt: number;
  engagementId: string;
  poaHash: string | null;
  operator: string;
  inventory: AccessPoint[];
  captures: CaptureRecord[];
  findings: Finding[];
  metrics: {
    apsDiscovered: number;
    inScope: number;
    captures: number;
    recovered: number;
    durationMs: number;
  };
  executiveSummary: string;
}

export interface WorkflowDef {
  id: string;
  name: string;
  blurb: string;
  requiresPoA: boolean;
  activeRf: boolean;
}

export type WorkflowId =
  | "wpa3-ent"
  | "guest"
  | "spectrum"
  | "psk-hunt"
  | "rogue";

export interface CommandResult {
  ok: boolean;
  lines: string[];
}

export interface Telemetry {
  cpuPct: number;
  gpuHashrate: number;
  backend: string;
  injectPps: number;
  dropRate: number;
  captureRatio: number;
  hopChannel: number;
  hopBand: Band;
}
