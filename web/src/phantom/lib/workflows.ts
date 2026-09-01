import type { WorkflowDef, WorkflowId } from "./types";

export const WORKFLOWS: Record<WorkflowId, WorkflowDef> = {
  "wpa3-ent": {
    id: "wpa3-ent",
    name: "WPA3-Enterprise Audit",
    blurb: "Inventory 802.1X radios, PMF, transition mode, and EAP identity leakage.",
    requiresPoA: true,
    activeRf: false,
  },
  guest: {
    id: "guest",
    name: "Guest Network Assessment",
    blurb: "Guest/open SSIDs, isolation, captive vs PSK, and weak-secret verification.",
    requiresPoA: true,
    activeRf: true,
  },
  spectrum: {
    id: "spectrum",
    name: "Full Spectrum Sweep",
    blurb: "Multi-band hop across 2.4 / 5 / 6 GHz. Build a complete BSSID inventory.",
    requiresPoA: false,
    activeRf: false,
  },
  "psk-hunt": {
    id: "psk-hunt",
    name: "Weak PSK Hunt",
    blurb: "In-scope WPA2-PSK radios: PMKID extract + approved-dictionary verification.",
    requiresPoA: true,
    activeRf: true,
  },
  rogue: {
    id: "rogue",
    name: "Rogue AP Detection",
    blurb: "SSID clones, OUI mismatch, open twins sitting on corporate names.",
    requiresPoA: false,
    activeRf: false,
  },
};

export const WORKFLOW_ORDER: WorkflowId[] = ["spectrum", "rogue", "guest", "psk-hunt", "wpa3-ent"];
