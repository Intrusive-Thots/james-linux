import { utf8, toHex, fromHex } from "./bytes";
import {
  canonicalJson,
  exportJwk,
  generateOperatorKey,
  importPrivateJwk,
  importPublicJwk,
  sha256Hex,
  signBytes,
  verifyBytes,
} from "./crypto";
import { LAB_SCOPE_BSSIDS, LAB_SCOPE_SSIDS } from "./environment";
import { macMatches, ssidMatches } from "./bytes";
import type { AccessPoint, RulesOfEngagement, SignedPoA } from "./types";

const KEY_STORE = "phantom.operator.keys";

interface StoredKeys {
  publicJwk: JsonWebKey;
  privateJwk: JsonWebKey;
}

export function makeEngagementId(now = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const r = Math.floor(Math.random() * 0xffff)
    .toString(16)
    .toUpperCase()
    .padStart(4, "0");
  return `PH-${y}${m}${d}-${r}`;
}

export function labRoeTemplate(operator = "ops"): RulesOfEngagement {
  const now = new Date();
  const until = new Date(now.getTime() + 8 * 3600_000);
  return {
    engagementId: makeEngagementId(now),
    operator,
    organization: "Hopper Industries Security",
    authorizationRef: "LAB-ROE-2026-081",
    validFrom: now.toISOString(),
    validUntil: until.toISOString(),
    ssids: [...LAB_SCOPE_SSIDS],
    bssids: [...LAB_SCOPE_BSSIDS],
    notes:
      "Authorized Hopper RF training range. Neighboring SSIDs are out of scope unless added. Injection limited to listed BSSID/SSID patterns.",
    certified: true,
  };
}

export async function loadOrCreateKeys(): Promise<{ pub: CryptoKey; priv: CryptoKey; publicJwk: JsonWebKey }> {
  if (typeof localStorage !== "undefined") {
    const raw = localStorage.getItem(KEY_STORE);
    if (raw) {
      try {
        const stored = JSON.parse(raw) as StoredKeys;
        const pub = await importPublicJwk(stored.publicJwk);
        const priv = await importPrivateJwk(stored.privateJwk);
        return { pub, priv, publicJwk: stored.publicJwk };
      } catch {
        /* regenerate */
      }
    }
  }
  const pair = await generateOperatorKey();
  const publicJwk = await exportJwk(pair.publicKey);
  const privateJwk = await exportJwk(pair.privateKey);
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(KEY_STORE, JSON.stringify({ publicJwk, privateJwk } satisfies StoredKeys));
  }
  return { pub: pair.publicKey, priv: pair.privateKey, publicJwk };
}

export async function signRoe(roe: RulesOfEngagement): Promise<SignedPoA> {
  if (!roe.certified) throw new Error("RoE certification required");
  if (!roe.operator.trim()) throw new Error("operator required");
  if (!roe.organization.trim()) throw new Error("organization required");
  if (!roe.authorizationRef.trim()) throw new Error("authorization reference required");
  if (roe.ssids.length + roe.bssids.length === 0) throw new Error("scope is empty");
  const from = Date.parse(roe.validFrom);
  const until = Date.parse(roe.validUntil);
  if (!Number.isFinite(from) || !Number.isFinite(until) || until <= from) {
    throw new Error("validity window invalid");
  }
  const { priv, publicJwk } = await loadOrCreateKeys();
  const canonical = canonicalJson(roe);
  const hashSha256 = await sha256Hex(canonical);
  const signature = await signBytes(priv, utf8(canonical));
  return {
    roe,
    canonical,
    hashSha256,
    signatureDerHex: toHex(signature),
    publicJwk,
    signedAt: Date.now(),
  };
}

export async function verifyPoA(poa: SignedPoA): Promise<boolean> {
  try {
    const pub = await importPublicJwk(poa.publicJwk);
    const ok = await verifyBytes(pub, utf8(poa.canonical), fromHex(poa.signatureDerHex));
    if (!ok) return false;
    const hash = await sha256Hex(poa.canonical);
    if (hash !== poa.hashSha256) return false;
    const until = Date.parse(poa.roe.validUntil);
    const from = Date.parse(poa.roe.validFrom);
    const now = Date.now();
    if (!Number.isFinite(until) || !Number.isFinite(from)) return false;
    if (now > until || now < from - 60_000) return false;
    return poa.roe.certified;
  } catch {
    return false;
  }
}

export function poaValid(poa: SignedPoA | null, now = Date.now()): boolean {
  if (!poa) return false;
  const until = Date.parse(poa.roe.validUntil);
  const from = Date.parse(poa.roe.validFrom);
  return Number.isFinite(until) && Number.isFinite(from) && now >= from - 60_000 && now <= until && poa.roe.certified;
}

export function apInScope(ap: AccessPoint, poa: SignedPoA | null): boolean {
  if (!poa || !poaValid(poa)) return false;
  if (poa.roe.ssids.some((p) => ssidMatches(p, ap.ssid) || (ap.hidden && ssidMatches(p, ap.ssid)))) return true;
  if (poa.roe.bssids.some((p) => macMatches(p, ap.bssid))) return true;
  return false;
}

export function macInScope(mac: string, poa: SignedPoA | null): boolean {
  if (!poa || !poaValid(poa)) return false;
  return poa.roe.bssids.some((p) => macMatches(p, mac));
}
