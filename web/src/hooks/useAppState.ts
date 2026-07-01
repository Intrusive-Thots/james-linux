import { useState, useCallback } from "react";

export interface LogEntry {
  id: number;
  timestamp: string;
  level: "info" | "warn" | "error" | "success";
  message: string;
}

export interface AP {
  bssid: string;
  essid: string;
  channel: number;
  privacy: string;
  power: number;
  clients: number;
  vendor: string;
  wps?: boolean;
}

export interface AttackState {
  stage: "idle" | "selecting" | "capturing" | "cracking" | "complete";
  progress: number;
  status: string;
  result?: { found: boolean; key?: string };
}

export type PageId =
  | "dashboard"
  | "recon"
  | "attacks"
  | "handshakes"
  | "agent"
  | "logs"
  | "settings";

export interface AppState {
  currentPage: PageId;
  adapter: string | null;
  adapterMode: "managed" | "monitor" | null;
  scanning: boolean;
  aps: AP[];
  selectedAP: AP | null;
  attack: AttackState;
  logs: LogEntry[];
  handshakes: HandshakeFile[];
}

export interface HandshakeFile {
  id: string;
  essid: string;
  bssid: string;
  capturedAt: string;
  filePath: string;
  cracked: boolean;
  key?: string;
}

const INITIAL_STATE: AppState = {
  currentPage: "dashboard",
  adapter: null,
  adapterMode: null,
  scanning: false,
  aps: [],
  selectedAP: null,
  attack: { stage: "idle", progress: 0, status: "Ready" },
  logs: [],
  handshakes: [],
};

let logCounter = 0;

export function useAppState() {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  const setPage = useCallback((page: PageId) => {
    setState((s) => ({ ...s, currentPage: page }));
  }, []);

  const addLog = useCallback(
    (level: LogEntry["level"], message: string) => {
      const entry: LogEntry = {
        id: ++logCounter,
        timestamp: new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        level,
        message,
      };
      setState((s) => ({
        ...s,
        logs: [...s.logs.slice(-500), entry],
      }));
    },
    []
  );

  const setAdapter = useCallback(
    (adapter: string | null, mode: "managed" | "monitor" | null = null) => {
      setState((s) => ({ ...s, adapter, adapterMode: mode }));
    },
    []
  );

  const setScanning = useCallback((scanning: boolean) => {
    setState((s) => ({ ...s, scanning }));
  }, []);

  const setAPs = useCallback((aps: AP[]) => {
    setState((s) => ({ ...s, aps }));
  }, []);

  const selectAP = useCallback((ap: AP | null) => {
    setState((s) => ({
      ...s,
      selectedAP: ap,
      attack: ap ? { ...s.attack, stage: "selecting" } : INITIAL_STATE.attack,
    }));
  }, []);

  const setAttack = useCallback((attack: Partial<AttackState>) => {
    setState((s) => ({ ...s, attack: { ...s.attack, ...attack } }));
  }, []);

  const addHandshake = useCallback((hs: HandshakeFile) => {
    setState((s) => ({
      ...s,
      handshakes: [...s.handshakes, hs],
    }));
  }, []);

  const removeHandshake = useCallback((id: string) => {
    setState((s) => ({
      ...s,
      handshakes: s.handshakes.filter((h) => h.id !== id),
    }));
  }, []);

  return {
    state,
    setPage,
    addLog,
    setAdapter,
    setScanning,
    setAPs,
    selectAP,
    setAttack,
    addHandshake,
    removeHandshake,
  };
}
