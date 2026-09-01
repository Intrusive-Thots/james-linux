const enc = new TextEncoder();

export function utf8(s: string): Uint8Array {
  return enc.encode(s);
}

export function concat(...parts: Uint8Array[]): Uint8Array {
  const len = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(len);
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

export function bytesEq(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i]! ^ b[i]!;
  return d === 0;
}

export function toHex(bytes: ArrayBuffer | Uint8Array, sep = ""): string {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = "";
  for (let i = 0; i < u8.length; i++) {
    if (sep && i) s += sep;
    s += u8[i]!.toString(16).padStart(2, "0");
  }
  return s;
}

export function fromHex(hex: string): Uint8Array {
  const clean = hex.replace(/[^0-9a-f]/gi, "");
  if (clean.length % 2) throw new Error("odd hex length");
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

export function randomBytes(n: number): Uint8Array {
  const out = new Uint8Array(n);
  crypto.getRandomValues(out);
  return out;
}

export function macToBytes(mac: string): Uint8Array {
  const parts = mac.split(/[:\-]/);
  if (parts.length !== 6) throw new Error(`invalid MAC ${mac}`);
  const out = new Uint8Array(6);
  for (let i = 0; i < 6; i++) out[i] = Number.parseInt(parts[i]!, 16);
  return out;
}

export function bytesToMac(bytes: Uint8Array): string {
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join(":").toUpperCase();
}

export function normalizeMac(mac: string): string {
  return bytesToMac(macToBytes(mac));
}

export function macOUI(mac: string): string {
  return normalizeMac(mac).split(":").slice(0, 3).join(":");
}

export function isLocallyAdministered(mac: string): boolean {
  return (macToBytes(mac)[0]! & 0x02) !== 0;
}

export function parseMacPattern(pattern: string): { kind: "exact" | "oui" | "wild"; value: string } {
  const p = pattern.trim().toUpperCase().replace(/-/g, ":");
  if (p.endsWith(":*") || p.endsWith(":*:*:*") || /^[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:\*$/.test(p)) {
    const oui = p.split(":").slice(0, 3).join(":");
    return { kind: "oui", value: oui };
  }
  if (p.includes("*")) return { kind: "wild", value: p };
  return { kind: "exact", value: normalizeMac(p) };
}

export function macMatches(pattern: string, mac: string): boolean {
  const n = normalizeMac(mac);
  const p = parseMacPattern(pattern);
  if (p.kind === "exact") return n === p.value;
  if (p.kind === "oui") return macOUI(n) === p.value;
  const re = new RegExp("^" + p.value.replace(/\*/g, "[0-9A-F]{2}") + "$");
  return re.test(n);
}

export function ssidMatches(pattern: string, ssid: string): boolean {
  const p = pattern.trim();
  if (p === "*") return true;
  if (!p.includes("*") && !p.includes("?")) return p.toLowerCase() === ssid.toLowerCase();
  const re = new RegExp(
    "^" +
      p
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*/g, ".*")
        .replace(/\?/g, ".") +
      "$",
    "i",
  );
  return re.test(ssid);
}

export function yieldMain(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0));
}

export function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

export function seeded(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function hexDumpLines(
  bytes: Uint8Array,
  bytesPerLine = 16,
): { offset: string; hex: string; ascii: string; idx: number }[] {
  const lines = [];
  for (let i = 0; i < bytes.length; i += bytesPerLine) {
    const slice = bytes.subarray(i, Math.min(i + bytesPerLine, bytes.length));
    const hexParts: string[] = [];
    let ascii = "";
    for (let j = 0; j < bytesPerLine; j++) {
      if (j === 8) hexParts.push("");
      if (j < slice.length) {
        const b = slice[j]!;
        hexParts.push(b.toString(16).padStart(2, "0"));
        ascii += b >= 32 && b < 127 ? String.fromCharCode(b) : ".";
      } else {
        hexParts.push("  ");
        ascii += " ";
      }
    }
    lines.push({
      offset: i.toString(16).padStart(4, "0"),
      hex: hexParts.join(" "),
      ascii,
      idx: i,
    });
  }
  return lines;
}
