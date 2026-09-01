import { concat, fromHex, toHex, utf8, bytesEq, macToBytes, randomBytes } from "./bytes";
import type { ComplexityReport } from "./types";

const PMK_NAME = utf8("PMK Name");
const PAIRWISE = "Pairwise key expansion";

function asBuf(u: Uint8Array): ArrayBuffer {
  return u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) as ArrayBuffer;
}

async function hmacSha1(key: Uint8Array, data: Uint8Array): Promise<Uint8Array> {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    asBuf(key),
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", cryptoKey, asBuf(data));
  return new Uint8Array(sig);
}

export async function sha256Hex(data: Uint8Array | string): Promise<string> {
  const bytes = typeof data === "string" ? utf8(data) : data;
  const digest = await crypto.subtle.digest("SHA-256", asBuf(bytes));
  return toHex(digest);
}

export async function pbkdf2Pmk(passphrase: string, ssid: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", asBuf(utf8(passphrase)), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-1", salt: asBuf(utf8(ssid)), iterations: 4096 },
    key,
    256,
  );
  return new Uint8Array(bits);
}

export async function pmkidOf(pmk: Uint8Array, apMac: Uint8Array, staMac: Uint8Array): Promise<Uint8Array> {
  const msg = concat(PMK_NAME, apMac, staMac);
  const mac = await hmacSha1(pmk, msg);
  return mac.subarray(0, 16);
}

async function prf(key: Uint8Array, label: string, data: Uint8Array, nbytes: number): Promise<Uint8Array> {
  const A = utf8(label);
  const out = new Uint8Array(nbytes);
  let offset = 0;
  let i = 0;
  while (offset < nbytes) {
    const block = await hmacSha1(key, concat(A, Uint8Array.of(0x00), data, Uint8Array.of(i)));
    const n = Math.min(20, nbytes - offset);
    out.set(block.subarray(0, n), offset);
    offset += n;
    i += 1;
  }
  return out;
}

function minMax(a: Uint8Array, b: Uint8Array): [Uint8Array, Uint8Array] {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i]! < b[i]!) return [a, b];
    if (a[i]! > b[i]!) return [b, a];
  }
  return a.length <= b.length ? [a, b] : [b, a];
}

export async function ptkOf(
  pmk: Uint8Array,
  apMac: Uint8Array,
  staMac: Uint8Array,
  anonce: Uint8Array,
  snonce: Uint8Array,
): Promise<Uint8Array> {
  const [minMac, maxMac] = minMax(apMac, staMac);
  const [minN, maxN] = minMax(anonce, snonce);
  return prf(pmk, PAIRWISE, concat(minMac, maxMac, minN, maxN), 64);
}

export const EAPOL_MIC_OFFSET = 81;

export async function eapolMic(kck: Uint8Array, eapolWithZeroMic: Uint8Array): Promise<Uint8Array> {
  const full = await hmacSha1(kck, eapolWithZeroMic);
  return full.subarray(0, 16);
}

export async function verifyPmkid(
  passphrase: string,
  ssid: string,
  apMacHex: string,
  staMacHex: string,
  pmkidHex: string,
): Promise<{ hit: boolean; pmk: Uint8Array }> {
  const pmk = await pbkdf2Pmk(passphrase, ssid);
  const computed = await pmkidOf(pmk, macToBytes(apMacHex), macToBytes(staMacHex));
  return { hit: bytesEq(computed, fromHex(pmkidHex)), pmk };
}

export async function verifyEapolMic(
  passphrase: string,
  ssid: string,
  apMac: string,
  staMac: string,
  anonce: Uint8Array,
  snonce: Uint8Array,
  eapol2: Uint8Array,
): Promise<boolean> {
  const pmk = await pbkdf2Pmk(passphrase, ssid);
  const ptk = await ptkOf(pmk, macToBytes(apMac), macToBytes(staMac), anonce, snonce);
  const kck = ptk.subarray(0, 16);
  const zeroed = new Uint8Array(eapol2);
  zeroed.fill(0, EAPOL_MIC_OFFSET, EAPOL_MIC_OFFSET + 16);
  const mic = await eapolMic(kck, zeroed);
  return bytesEq(mic, eapol2.subarray(EAPOL_MIC_OFFSET, EAPOL_MIC_OFFSET + 16));
}

export function canonicalJson(value: unknown): string {
  const walk = (v: unknown): unknown => {
    if (v === null || typeof v !== "object") return v;
    if (Array.isArray(v)) return v.map(walk);
    const obj = v as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(obj).sort()) out[k] = walk(obj[k]);
    return out;
  };
  return JSON.stringify(walk(value));
}

export async function generateOperatorKey(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
}

export async function exportJwk(key: CryptoKey): Promise<JsonWebKey> {
  return crypto.subtle.exportKey("jwk", key);
}

export async function importPublicJwk(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, true, ["verify"]);
}

export async function importPrivateJwk(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, true, ["sign"]);
}

export async function signBytes(privateKey: CryptoKey, data: Uint8Array): Promise<Uint8Array> {
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, privateKey, asBuf(data));
  return new Uint8Array(sig);
}

export async function verifyBytes(publicKey: CryptoKey, data: Uint8Array, sig: Uint8Array): Promise<boolean> {
  return crypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" },
    publicKey,
    asBuf(sig),
    asBuf(data),
  );
}

export function analyzePassphrase(pw: string, dictionary: string[]): ComplexityReport {
  const classes = {
    lower: /[a-z]/.test(pw),
    upper: /[A-Z]/.test(pw),
    digit: /\d/.test(pw),
    symbol: /[^A-Za-z0-9]/.test(pw),
  };
  const classCount = Object.values(classes).filter(Boolean).length;
  const charsetSize =
    (classes.lower ? 26 : 0) + (classes.upper ? 26 : 0) + (classes.digit ? 10 : 0) + (classes.symbol ? 33 : 0);
  const entropyBits = pw.length * Math.log2(Math.max(charsetSize, 2));
  const lower = pw.toLowerCase();
  const dictionaryHit = dictionary.some((w) => w.length >= 4 && (lower === w.toLowerCase() || lower.includes(w.toLowerCase())));
  const notes: string[] = [];
  if (pw.length < 8) notes.push("Below WPA2 minimum length.");
  if (pw.length < 14) notes.push("Shorter than 14-character organizational baseline.");
  if (classCount < 3) notes.push("Uses fewer than 3 character classes.");
  if (dictionaryHit) notes.push("Matches or contains an approved-dictionary token.");
  if (/^[A-Za-z]+\d+$/.test(pw)) notes.push("Alphabetic stem with trailing digits — common mutation.");
  if (/20(2[0-9]|1[0-9])/.test(pw)) notes.push("Contains a calendar year.");
  const policyPass = pw.length >= 14 && classCount >= 3 && !dictionaryHit && entropyBits >= 60;
  let verdict: ComplexityReport["verdict"] = "strong";
  if (!policyPass && (dictionaryHit || pw.length < 10 || entropyBits < 40)) verdict = "fail";
  else if (!policyPass && entropyBits < 50) verdict = "weak";
  else if (!policyPass) verdict = "adequate";
  if (policyPass) notes.push("Meets Hopper baseline (14+, 3 classes, non-dictionary).");
  return {
    length: pw.length,
    classes,
    charsetSize,
    entropyBits: Math.round(entropyBits * 10) / 10,
    dictionaryHit,
    policyPass,
    verdict,
    notes,
  };
}

export function formatHc22000Pmkid(pmkid: Uint8Array, apMac: Uint8Array, staMac: Uint8Array, ssid: string): string {
  return ["WPA", "01", toHex(pmkid), toHex(apMac), toHex(staMac), toHex(utf8(ssid))].join("*");
}

export function formatHc22000Eapol(
  mic: Uint8Array,
  apMac: Uint8Array,
  staMac: Uint8Array,
  ssid: string,
  anonce: Uint8Array,
  eapol: Uint8Array,
  messagePair = "02",
): string {
  return ["WPA", "02", toHex(mic), toHex(apMac), toHex(staMac), toHex(utf8(ssid)), toHex(anonce), toHex(eapol), messagePair].join(
    "*",
  );
}

export async function buildSignedHandshake(opts: {
  passphrase: string;
  ssid: string;
  apMac: string;
  staMac: string;
}): Promise<{
  pmk: Uint8Array;
  pmkid: Uint8Array;
  anonce: Uint8Array;
  snonce: Uint8Array;
  ptk: Uint8Array;
  kck: Uint8Array;
}> {
  const pmk = await pbkdf2Pmk(opts.passphrase, opts.ssid);
  const ap = macToBytes(opts.apMac);
  const sta = macToBytes(opts.staMac);
  const pmkid = await pmkidOf(pmk, ap, sta);
  const anonce = randomBytes(32);
  const snonce = randomBytes(32);
  const ptk = await ptkOf(pmk, ap, sta, anonce, snonce);
  return { pmk, pmkid, anonce, snonce, ptk, kck: ptk.subarray(0, 16) };
}
