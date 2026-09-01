import { create } from "zustand";
import { getLab, resetLab } from "./rf-lab";
import { labRoeTemplate, poaValid, signRoe, verifyPoA } from "./poa";
import { runDictionary } from "./cracker";
import { buildReport, downloadText, reportMarkdown } from "./reports";
import { WORKFLOWS } from "./workflows";
import { jamesAdapter, jamesOnline, jamesSend } from "../james-bridge";
import type {
  CaptureRecord,
  CommandResult,
  EngagementReport,
  HandshakeProgress,
  LogEntry,
  LogLevel,
  RulesOfEngagement,
  SignedPoA,
  Stage,
  Telemetry,
  VerifyJob,
  WorkflowId,
  Density,
  OverlayKind,
} from "./types";

const POA_KEY = "phantom.poa";
const REPORTS_KEY = "phantom.reports";
const AUDIT_KEY = "phantom.audit";

let logSeq = 1;
let engineTimer: number | null = null;
let abortVerify: AbortController | null = null;
let workflowToken = 0;
let sessionStarted = Date.now();

function loadPoA(): SignedPoA | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(POA_KEY);
    return raw ? (JSON.parse(raw) as SignedPoA) : null;
  } catch {
    return null;
  }
}

function loadReports(): EngagementReport[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(REPORTS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as EngagementReport[];
  } catch {
    return [];
  }
}

function persistReports(reports: EngagementReport[]) {
  try {
    const slim = reports.slice(0, 8).map((r) => ({
      ...r,
      captures: r.captures.map((c) => ({ ...c, eapol2: [], frame: [] })),
      inventory: r.inventory.map((a) => ({ ...a, psk: undefined })),
    }));
    localStorage.setItem(REPORTS_KEY, JSON.stringify(slim));
  } catch {
    /* quota */
  }
}

export interface PhantomState {
  booted: boolean;
  stage: Stage;
  glitch: number;
  flash: number;
  poa: SignedPoA | null;
  poaOk: boolean;
  logs: LogEntry[];
  cmdHistory: string[];
  cmdOutput: string[];
  targetBssid: string | null;
  handshake: HandshakeProgress;
  captures: CaptureRecord[];
  verify: VerifyJob | null;
  reports: EngagementReport[];
  activeReport: EngagementReport | null;
  workflow: WorkflowId | null;
  workflowStep: string;
  telemetry: Telemetry;
  mobileTab: "recon" | "ops" | "tel";
  poaOpen: boolean;
  helpOpen: boolean;
  tick: number;
  density: Density;
  consoleOpen: boolean;
  overlay: OverlayKind;
  log: (level: LogLevel, code: string, message: string) => void;
  boot: () => Promise<void>;
  setStage: (s: Stage) => void;
  openPoA: (open: boolean) => void;
  signLabPoA: (operator: string) => Promise<void>;
  signCustomPoA: (roe: RulesOfEngagement) => Promise<void>;
  revokePoA: () => void;
  startScan: (mode: "passive" | "active") => void;
  stopScan: () => void;
  setTarget: (bssid: string | null) => void;
  capture: (force: boolean) => Promise<void>;
  deauth: () => void;
  verifyTarget: () => Promise<void>;
  abortVerify: () => void;
  runWorkflow: (id: WorkflowId) => Promise<void>;
  cancelWorkflow: () => void;
  generateReport: () => EngagementReport;
  exec: (line: string) => Promise<CommandResult>;
  setMobileTab: (t: "recon" | "ops" | "tel") => void;
  setHelpOpen: (v: boolean) => void;
  setDensity: (d: Density) => void;
  setConsoleOpen: (open: boolean) => void;
  setOverlay: (overlay: OverlayKind) => void;
  approach: () => void;
}

function emptyHandshake(): HandshakeProgress {
  return { m1: false, m2: false, m3: false, m4: false, pmkid: false };
}

export const usePhantom = create<PhantomState>((set, get) => ({
  booted: false,
  stage: "BOOT",
  glitch: 0,
  flash: 0,
  poa: null,
  poaOk: false,
  logs: [],
  cmdHistory: [],
  cmdOutput: [
    "Phantom SDR lab online.",
    "poa lab     sign Hopper training range",
    "scan        dual-radio hop  2.4/5/6",
    "workflow psk-hunt | help",
  ],
  targetBssid: null,
  handshake: emptyHandshake(),
  captures: [],
  verify: null,
  reports: [],
  activeReport: null,
  workflow: null,
  workflowStep: "",
  telemetry: {
    cpuPct: 4,
    gpuHashrate: 0,
    backend: "WebCrypto PBKDF2-HMAC-SHA1",
    injectPps: 0,
    dropRate: 0,
    captureRatio: 0,
    hopChannel: 1,
    hopBand: "2.4",
  },
  mobileTab: "ops",
  poaOpen: false,
  helpOpen: false,
  tick: 0,
  density: "comfortable",
  consoleOpen: false,
  overlay: null,

  log: (level, code, message) => {
    const entry: LogEntry = { id: logSeq++, ts: Date.now(), level, code, message };
    set((s) => ({ logs: [...s.logs.slice(-240), entry] }));
    if (typeof localStorage !== "undefined") {
      try {
        const prev = JSON.parse(localStorage.getItem(AUDIT_KEY) ?? "[]") as LogEntry[];
        localStorage.setItem(AUDIT_KEY, JSON.stringify([...prev.slice(-400), entry]));
      } catch {
        /* ignore */
      }
    }
    if (code === "HANDSHAKE_CAPTURED") {
      set({ flash: Date.now() });
    }
  },

  setStage: (stage) => {
    set({ stage, glitch: Date.now() });
  },

  boot: async () => {
    if (get().booted) return;
    sessionStarted = Date.now();
    const stored = loadPoA();
    let poa: SignedPoA | null = null;
    if (stored) {
      const ok = await verifyPoA(stored);
      poa = ok ? stored : null;
      if (!ok) localStorage.removeItem(POA_KEY);
    }
    const lab = getLab();
    lab.setPoA(poa);
    set({
      poa,
      poaOk: poaValid(poa),
      reports: loadReports(),
      booted: true,
      stage: "IDLE",
      poaOpen: !poa,
    });
    get().log("info", "BOOT", "Phantom v1.0.0 — SDR lab radios online");
    if (poa) get().log("info", "POA_OK", `RoE ${poa.roe.engagementId}  sha256 ${poa.hashSha256.slice(0, 16)}…`);
    else get().log("warn", "POA_MISSING", "Injection locked. Sign a Rules of Engagement to unlock active RF.");
    startEngine(set, get);
  },

  openPoA: (poaOpen) => set({ poaOpen }),
  setMobileTab: (mobileTab) => set({ mobileTab }),
  setHelpOpen: (helpOpen) => set({ helpOpen }),
  setDensity: (density) => set({ density }),
  setConsoleOpen: (consoleOpen) => set({ consoleOpen }),
  setOverlay: (overlay) => set({ overlay }),

  signLabPoA: async (operator) => {
    const roe = labRoeTemplate(operator || "ops");
    await get().signCustomPoA(roe);
  },

  signCustomPoA: async (roe) => {
    const poa = await signRoe(roe);
    localStorage.setItem(POA_KEY, JSON.stringify(poa));
    getLab().setPoA(poa);
    set({ poa, poaOk: true, poaOpen: false });
    get().log("info", "POA_SIGNED", `ECDSA P-256  ${poa.hashSha256.slice(0, 16)}…  scope ${roe.ssids.join(",")} ${roe.bssids.join(",")}`);
    get().setStage("IDLE");
  },

  revokePoA: () => {
    localStorage.removeItem(POA_KEY);
    getLab().setPoA(null);
    set({ poa: null, poaOk: false, targetBssid: null });
    get().log("warn", "POA_REVOKED", "Injection locked.");
  },

  startScan: (mode) => {
    try {
      if (jamesOnline()) {
        jamesSend("scan_aps", { interface: jamesAdapter(), duration: 20 });
        getLab().scanning = true;
        getLab().scanMode = mode;
        get().setStage("RECON");
        get().log("info", "SCAN_START", `JAMES live sweep on ${jamesAdapter()} (${mode})`);
        return;
      }
      getLab().startScan(mode);
      get().setStage("RECON");
      get().log("info", "SCAN_START", `${mode} sweep  dual-radio hop 2.4/5/6 GHz`);
    } catch (err) {
      get().log("crit", "SCAN_DENIED", err instanceof Error ? err.message : String(err));
      set({ poaOpen: true });
    }
  },

  stopScan: () => {
    if (jamesOnline()) jamesSend("stop_monitor", { interface: jamesAdapter() });
    getLab().stopScan();
    getLab().resumeHop();
    if (get().stage === "RECON") get().setStage("IDLE");
    get().log("info", "SCAN_STOP", "channel hop paused");
  },

  setTarget: (bssid) => {
    if (!bssid) {
      set({ targetBssid: null, handshake: emptyHandshake() });
      return;
    }
    const lab = getLab();
    const ap = lab.aps.find((a) => a.bssid === bssid);
    if (!ap) return;
    if (!ap.inScope) {
      get().log("warn", "SCOPE_BLOCK", `${bssid} is out of PoA scope`);
      return;
    }
    lab.lockChannel(bssid);
    set({ targetBssid: bssid, handshake: emptyHandshake(), mobileTab: "ops" });
    get().setStage("TRIAGE");
    get().log("info", "TARGET", `${ap.ssid}  ${ap.bssid}  ${ap.encryption}  ch${ap.channel}  risk ${ap.risk}`);
  },

  capture: async (force) => {
    const bssid = get().targetBssid;
    if (!bssid) {
      get().log("warn", "CAPTURE_NO_TARGET", "no target selected");
      return;
    }
    if (force && !get().poaOk) {
      set({ poaOpen: true });
      get().log("crit", "INJECT_LOCKED", "deauth requires a valid PoA");
      return;
    }
    get().setStage("CAPTURE");
    get().log("info", "CAPTURE_START", `${force ? "active" : "passive"} intercept  ${bssid}`);
    const live = getLab().aps.find((a) => a.bssid === bssid);
    if (jamesOnline() && live?.role === "live") {
      jamesSend(force ? "capture_handshake" : "capture_pmkid", {
        interface: jamesAdapter(),
        bssid,
        channel: live.channel,
        essid: live.ssid,
      });
      get().log("info", "CAPTURE_START", `JAMES live ${force ? "handshake" : "PMKID"}  ${bssid}`);
      return;
    }
    try {
      const result = await getLab().captureTarget(bssid, force);
      set({ handshake: result.progress });
      if (result.error) {
        get().log("warn", "CAPTURE_NOTE", result.error);
        return;
      }
      if (result.capture) {
        set((s) => ({
          captures: [result.capture!, ...s.captures.filter((c) => c.bssid !== result.capture!.bssid)],
        }));
        get().log(
          "crit",
          "HANDSHAKE_CAPTURED",
          `${result.capture.ssid}  ${result.capture.method}  PMKID ${result.capture.pmkidHex.slice(0, 8)}…  STA ${result.capture.staMac}`,
        );
      }
    } catch (err) {
      get().log("crit", "CAPTURE_FAIL", err instanceof Error ? err.message : String(err));
    }
  },

  deauth: () => {
    const bssid = get().targetBssid;
    if (!bssid) return;
    const live = getLab().aps.find((a) => a.bssid === bssid);
    if (jamesOnline() && live?.role === "live") {
      jamesSend("capture_handshake", {
        interface: jamesAdapter(),
        bssid,
        channel: live.channel,
        essid: live.ssid,
      });
      get().log("warn", "DEAUTH", `JAMES live handshake capture (reauth) → ${bssid}`);
      return;
    }
    try {
      const frames = getLab().injectDeauth(bssid);
      get().log("warn", "DEAUTH", `injected ${frames.length} deauth frame(s) → ${bssid}`);
      void get().capture(false);
    } catch (err) {
      get().log("crit", "INJECT_LOCKED", err instanceof Error ? err.message : String(err));
      set({ poaOpen: true });
    }
  },

  abortVerify: () => {
    abortVerify?.abort();
    abortVerify = null;
  },

  verifyTarget: async () => {
    const bssid = get().targetBssid;
    const cap = get().captures.find((c) => c.bssid === bssid) ?? get().captures[0];
    if (!cap) {
      get().log("warn", "VERIFY_NO_CAP", "no capture on target — run capture first");
      return;
    }
    abortVerify?.abort();
    abortVerify = new AbortController();
    const signal = abortVerify.signal;
    set({
      verify: {
        captureId: cap.id,
        running: true,
        tried: 0,
        total: 0,
        hps: 0,
        elapsedMs: 0,
        status: "running",
      },
    });
    get().setStage("VERIFY");
    get().log("info", "VERIFY_START", `dictionary  ${cap.ssid}  ${cap.hc22000.slice(0, 48)}…`);
    const result = await runDictionary(cap, {
      signal,
      onProgress: (p) => {
        set({
          verify: {
            captureId: cap.id,
            running: true,
            tried: p.tried,
            total: p.total,
            hps: p.hps,
            elapsedMs: p.elapsedMs,
            current: p.current,
            status: "running",
          },
          telemetry: { ...get().telemetry, gpuHashrate: p.hps, cpuPct: 72 },
        });
      },
    });
    const job: VerifyJob = {
      captureId: cap.id,
      running: false,
      tried: result.tried,
      total: get().verify?.total ?? result.tried,
      hps: get().verify?.hps ?? 0,
      elapsedMs: result.elapsedMs,
      status: result.status,
      passphrase: result.passphrase,
      complexity: result.complexity,
    };
    set({ verify: job, telemetry: { ...get().telemetry, gpuHashrate: 0, cpuPct: 8 } });
    if (result.status === "hit" && result.passphrase) {
      set((s) => ({
        captures: s.captures.map((c) =>
          c.id === cap.id ? { ...c, verified: true, passphrase: result.passphrase } : c,
        ),
      }));
      const cpx = result.complexity;
      get().log(
        "crit",
        "PSK_RECOVERED",
        `${cap.ssid}  passphrase recovered  entropy ${cpx?.entropyBits ?? "?"}b  verdict ${cpx?.verdict ?? "?"}`,
      );
    } else if (result.status === "exhausted") {
      get().log("info", "VERIFY_EXHAUSTED", `${cap.ssid}  approved dictionary exhausted — PSK not in wordlist`);
    } else if (result.status === "aborted") {
      get().log("warn", "VERIFY_ABORT", "verification aborted");
    } else if (result.status === "unsupported") {
      get().log("warn", "VERIFY_SKIP", "AKM does not yield an offline PSK hash");
    }
  },

  runWorkflow: async (id) => {
    const wf = WORKFLOWS[id];
    const token = ++workflowToken;
    if (wf.requiresPoA && !get().poaOk) {
      set({ poaOpen: true });
      get().log("crit", "WF_LOCKED", `${wf.name} requires a signed PoA`);
      return;
    }
    set({ workflow: id, workflowStep: "init" });
    get().log("info", "WF_START", wf.name);
    const still = () => token === workflowToken;

    get().startScan(wf.activeRf ? "active" : "passive");
    set({ workflowStep: "recon  dual-radio hop" });
    await wait(2600);
    if (!still()) return;

    const lab = getLab();
    const visible = lab.visibleAps();

    if (id === "spectrum") {
      set({ workflowStep: "inventory" });
      get().log("info", "WF_INV", `${visible.length} BSSID(s) across 2.4/5/6 GHz`);
    }

    if (id === "rogue") {
      set({ workflowStep: "oui / ssid clone analysis" });
      const rogues = visible.filter((a) => a.rogue || (a.ssid === "Hopper-Corp" && !a.bssid.startsWith("00:1A:8C")));
      for (const r of rogues) get().log("crit", "ROGUE", `${r.ssid}  ${r.bssid}  ${r.vendor}  ${r.encryption}`);
      if (!rogues.length) get().log("info", "ROGUE_NONE", "no SSID clones with OUI mismatch");
    }

    if (id === "wpa3-ent") {
      set({ workflowStep: "enterprise config audit" });
      const ents = visible.filter((a) => a.encryption === "WPA3-ENT" || a.encryption === "WPA2-ENT" || a.encryption === "WPA3-TRANS");
      for (const a of ents) {
        get().log(
          a.pmf === "required" ? "info" : "warn",
          "ENT_CFG",
          `${a.ssid}  ${a.bssid}  ${a.encryption}  PMF=${a.pmf}  ${a.akm}`,
        );
      }
    }

    if (id === "guest" || id === "psk-hunt") {
      const psks = visible.filter((a) => a.inScope && (a.encryption === "WPA2-PSK" || a.encryption === "WPA-TKIP"));
      const guests = visible.filter(
        (a) => a.inScope && (a.role === "guest" || a.encryption === "OPEN" || /guest/i.test(a.ssid)),
      );
      const queue = id === "guest" ? [...guests, ...psks.filter((p) => !guests.includes(p))] : psks;
      const uniq = [...new Map(queue.map((a) => [a.bssid, a])).values()].sort((a, b) => b.risk - a.risk);
      for (const ap of uniq) {
        if (!still()) return;
        if (!ap.inScope) continue;
        set({ workflowStep: `capture ${ap.ssid}`, targetBssid: ap.bssid, handshake: emptyHandshake() });
        get().log("info", "WF_TARGET", `${ap.ssid}  ${ap.bssid}  risk ${ap.risk}`);
        if (ap.encryption === "OPEN") {
          get().log("warn", "OPEN_BSS", `${ap.ssid} open authentication — no handshake`);
          continue;
        }
        try {
          const result = await lab.captureTarget(ap.bssid, wf.activeRf);
          set({ handshake: result.progress });
          if (result.capture) {
            set((s) => ({ captures: [result.capture!, ...s.captures.filter((c) => c.bssid !== ap.bssid)] }));
            get().log("crit", "HANDSHAKE_CAPTURED", `${ap.ssid}  ${result.capture.method}`);
            set({ targetBssid: ap.bssid });
            await get().verifyTarget();
          } else if (result.error) {
            get().log("warn", "WF_SKIP", result.error);
          }
        } catch (err) {
          get().log("warn", "WF_SKIP", err instanceof Error ? err.message : String(err));
        }
      }
    }

    if (!still()) return;
    get().stopScan();
    set({ workflowStep: "report" });
    const report = get().generateReport();
    get().log("info", "WF_DONE", `${wf.name} complete  report ${report.id}`);
    set({ workflow: null, workflowStep: "", stage: "REPORT" });
  },

  cancelWorkflow: () => {
    workflowToken += 1;
    set({ workflow: null, workflowStep: "" });
    get().log("warn", "WF_CANCEL", "workflow cancelled");
  },

  generateReport: () => {
    const lab = getLab();
    const report = buildReport({
      poa: get().poa,
      aps: lab.aps,
      captures: get().captures,
      startedAt: sessionStarted,
      operator: get().poa?.roe.operator ?? "ops",
    });
    set((s) => {
      const reports = [report, ...s.reports].slice(0, 8);
      persistReports(reports);
      return { reports, activeReport: report, stage: "REPORT" };
    });
    get().log("info", "REPORT", `${report.id}  ${report.findings.length} finding(s)`);
    return report;
  },

  approach: () => {
    const t = get().targetBssid;
    if (!t) return;
    getLab().approach(t);
    get().log("info", "APPROACH", `moved toward ${t}`);
  },

  exec: async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return { ok: true, lines: [] };
    set((s) => ({ cmdHistory: [...s.cmdHistory.slice(-80), trimmed] }));
    const result = await dispatch(trimmed, get);
    set({ cmdOutput: [...result.lines] });
    for (const l of result.lines) {
      if (l.startsWith("err:")) get().log("warn", "CLI", l);
    }
    return result;
  },
}));

function wait(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function startEngine(set: (p: Partial<PhantomState> | ((s: PhantomState) => Partial<PhantomState>)) => void, get: () => PhantomState) {
  if (engineTimer != null) return;
  const lab = getLab();
  engineTimer = window.setInterval(() => {
    lab.tick(120);
    const snap = lab.snapshot();
    const radio = snap.adapters[0]!;
    const radio1 = snap.adapters[1]!;
    const rx = radio.rxPackets + radio1.rxPackets;
    const drops = radio.drops + radio1.drops;
    const caps = get().captures;
    set({
      tick: snap.t,
      telemetry: {
        ...get().telemetry,
        cpuPct: snap.scanning ? 18 + (rx % 7) : get().verify?.running ? 70 : 5,
        injectPps: radio.txPackets ? Number((radio.txPackets / Math.max(1, snap.t / 1000)).toFixed(2)) : 0,
        dropRate: rx ? drops / rx : 0,
        captureRatio: caps.length ? caps.filter((c) => c.complete).length / caps.length : 0,
        hopChannel: radio.channel,
        hopBand: radio.band,
      },
    });
  }, 120) as unknown as number;
}

async function dispatch(line: string, get: () => PhantomState): Promise<CommandResult> {
  const [cmd, ...rest] = tokenize(line);
  const arg = rest.join(" ");
  switch ((cmd ?? "").toLowerCase()) {
    case "help":
      return { ok: true, lines: HELP };
    case "clear":
      return { ok: true, lines: [""] };
    case "status": {
      const lab = getLab();
      const s = get();
      return {
        ok: true,
        lines: [
          `stage     ${s.stage}`,
          `poa       ${s.poaOk ? s.poa?.roe.engagementId : "LOCKED"}`,
          `scan      ${lab.scanMode}`,
          `target    ${s.targetBssid ?? "none"}`,
          `captures  ${s.captures.length}`,
          `aps       ${lab.visibleAps().length} visible / ${lab.aps.length} in range`,
        ],
      };
    }
    case "poa":
      if (rest[0] === "revoke") {
        get().revokePoA();
        return { ok: true, lines: ["PoA revoked"] };
      }
      if (rest[0] === "lab") {
        await get().signLabPoA(rest.slice(1).join(" ") || "ops");
        return { ok: true, lines: ["lab RoE signed"] };
      }
      get().openPoA(true);
      return { ok: true, lines: ["opening PoA desk"] };
    case "scan": {
      const mode = rest[0] === "active" ? "active" : "passive";
      get().startScan(mode);
      return { ok: true, lines: [`${mode} scan started`] };
    }
    case "stop":
      get().stopScan();
      get().abortVerify();
      get().cancelWorkflow();
      return { ok: true, lines: ["halted"] };
    case "scope": {
      const poa = get().poa;
      if (!poa) return { ok: false, lines: ["err: no PoA"] };
      return {
        ok: true,
        lines: [`ssids  ${poa.roe.ssids.join(", ")}`, `bssids ${poa.roe.bssids.join(", ")}`],
      };
    }
    case "target": {
      if (!arg) return { ok: false, lines: ["err: target <bssid|ssid>"] };
      const lab = getLab();
      const ap =
        lab.aps.find((a) => a.bssid.replace(/:/g, "").toLowerCase() === arg.replace(/[:.-]/g, "").toLowerCase()) ||
        lab.aps.find((a) => a.ssid.toLowerCase() === arg.toLowerCase() && a.inScope) ||
        lab.aps.find((a) => a.ssid.toLowerCase().includes(arg.toLowerCase()));
      if (!ap) return { ok: false, lines: [`err: no AP matching ${arg}`] };
      get().setTarget(ap.bssid);
      return { ok: true, lines: [`target ${ap.ssid} ${ap.bssid}`] };
    }
    case "capture":
      await get().capture(rest[0] === "active" || rest[0] === "force");
      return { ok: true, lines: ["capture issued"] };
    case "deauth":
      get().deauth();
      return { ok: true, lines: ["deauth issued"] };
    case "verify":
    case "crack":
      await get().verifyTarget();
      return { ok: true, lines: ["verify issued"] };
    case "report": {
      const r = get().generateReport();
      if (rest[0] === "export") {
        downloadText(`phantom-${r.engagementId}.md`, reportMarkdown(r), "text/markdown");
        downloadText(`phantom-${r.engagementId}.json`, JSON.stringify({ ...r, captures: r.captures.map((c) => ({ ...c, hc22000: c.hc22000 })) }, null, 2), "application/json");
        return { ok: true, lines: [`exported ${r.id}`] };
      }
      return { ok: true, lines: [r.executiveSummary] };
    }
    case "workflow": {
      const id = rest[0] as WorkflowId;
      if (!WORKFLOWS[id]) return { ok: false, lines: ["err: workflow <wpa3-ent|guest|spectrum|psk-hunt|rogue>"] };
      void get().runWorkflow(id);
      return { ok: true, lines: [`workflow ${WORKFLOWS[id].name}`] };
    }
    case "adapters": {
      const lines = getLab().adapters.map(
        (a) => `${a.phy}  ${a.iface}  ${a.band} ch${a.channel}  ${a.state}  rx ${a.rxPackets} tx ${a.txPackets} drop ${a.drops}`,
      );
      return { ok: true, lines };
    }
    case "approach":
      get().approach();
      return { ok: true, lines: ["operator relocated"] };
    case "reset": {
      resetLab();
      getLab().setPoA(get().poa);
      return { ok: true, lines: ["lab environment reset"] };
    }
    default:
      return { ok: false, lines: [`err: unknown command '${cmd}'  (help)`] };
  }
}

function tokenize(line: string): string[] {
  const out: string[] = [];
  const re = /"([^"]*)"|(\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line))) out.push(m[1] ?? m[2] ?? "");
  return out;
}

export const COMMANDS = [
  "help",
  "status",
  "poa",
  "poa lab",
  "poa revoke",
  "scan",
  "scan active",
  "stop",
  "scope",
  "target",
  "capture",
  "capture active",
  "deauth",
  "verify",
  "report",
  "report export",
  "workflow spectrum",
  "workflow rogue",
  "workflow guest",
  "workflow psk-hunt",
  "workflow wpa3-ent",
  "adapters",
  "approach",
  "clear",
  "reset",
];

const HELP = [
  "commands",
  "  help                   this list",
  "  poa | poa lab | poa revoke",
  "  scan [passive|active]  dual-radio hop",
  "  stop                   halt scan / verify / workflow",
  "  target <bssid|ssid>    lock radio to in-scope AP",
  "  capture [active]       intercept EAPOL / PMKID",
  "  deauth                 in-scope injection (PoA)",
  "  verify                 approved-dictionary PBKDF2",
  "  workflow <id>          spectrum|rogue|guest|psk-hunt|wpa3-ent",
  "  report [export]        telemetry + remediations",
  "  adapters | scope | status | approach | clear",
];
