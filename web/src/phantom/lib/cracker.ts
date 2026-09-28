import { yieldMain } from "./bytes";
import { analyzePassphrase, verifyPmkid } from "./crypto";
import { buildAttackList, APPROVED_DICTIONARY } from "./wordlist";
import type { CaptureRecord, ComplexityReport, VerifyJob } from "./types";

export interface CrackProgress {
  tried: number;
  total: number;
  hps: number;
  current: string;
  elapsedMs: number;
}

export async function runDictionary(
  capture: CaptureRecord,
  opts: {
    signal: AbortSignal;
    onProgress: (p: CrackProgress) => void;
    wordlist?: string[];
  },
): Promise<{ status: VerifyJob["status"]; passphrase?: string; complexity?: ComplexityReport; tried: number; elapsedMs: number }> {
  if (capture.encryption === "WPA3-SAE" || capture.encryption === "WPA2-ENT" || capture.encryption === "WPA3-ENT") {
    return { status: "unsupported", tried: 0, elapsedMs: 0 };
  }
  const words = opts.wordlist ?? buildAttackList();
  const started = performance.now();
  let tried = 0;
  for (const word of words) {
    if (opts.signal.aborted) {
      return { status: "aborted", tried, elapsedMs: performance.now() - started };
    }
    const { hit } = await verifyPmkid(word, capture.ssid, capture.bssid, capture.staMac, capture.pmkidHex);
    tried += 1;
    const elapsedMs = performance.now() - started;
    const hps = elapsedMs > 0 ? (tried / elapsedMs) * 1000 : 0;
    if (tried % 1 === 0) {
      opts.onProgress({ tried, total: words.length, hps, current: word, elapsedMs });
      await yieldMain();
    }
    if (hit) {
      const complexity = analyzePassphrase(word, APPROVED_DICTIONARY);
      return { status: "hit", passphrase: word, complexity, tried, elapsedMs };
    }
  }
  return { status: "exhausted", tried, elapsedMs: performance.now() - started };
}
