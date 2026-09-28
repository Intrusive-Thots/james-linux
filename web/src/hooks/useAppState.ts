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
  sub_stage?: number;
  total_stages?: number;
  stage_name?: string;
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

// ── Workspace-aware routing ────────────────────────────
export type WorkspaceId = "phantom" | "agent" | "auto" | "settings";

export type PhantomSubPage = "orchestrator";
export type AgentSubPage = "dashboard" | "recon" | "attacks" | "handshakes" | "logs";
export type AutoSubPage = "autopilot" | "console";
export type SettingsSubPage = "general" | "interfaces" | "dependencies" | "diagnostics" | "advanced";
export type SubPageId = PhantomSubPage | AgentSubPage | AutoSubPage | SettingsSubPage;

/** Default sub-page for each workspace */
export const WORKSPACE_DEFAULTS: Record<WorkspaceId, SubPageId> = {
  phantom: "orchestrator",
  agent: "dashboard",
  auto: "autopilot",
  settings: "general",
};

/** Sub-pages available per workspace */
export const WORKSPACE_SUBPAGES: Record<WorkspaceId, SubPageId[]> = {
  phantom: ["orchestrator"],
  agent: ["dashboard", "recon", "attacks", "handshakes", "logs"],
  auto: ["autopilot", "console"],
  settings: ["general", "interfaces", "dependencies", "diagnostics", "advanced"],
};

// ── Backward-compat: flatten for components that still use PageId ──
export type PageId = SubPageId;

export interface AppState {
  currentWorkspace: WorkspaceId;
  currentSubPage: SubPageId;
  adapter: string | null;
  adapterMode: "managed" | "monitor" | null;
  scanning: boolean;
  aps: AP[];
  selectedAP: AP | null;
  attack: AttackState;
  logs: LogEntry[];
  handshakes: HandshakeFile[];
}

const INITIAL_STATE: AppState = {
  currentWorkspace: "phantom",
  currentSubPage: "orchestrator",
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

  const setWorkspace = useCallback((workspace: WorkspaceId) => {
    setState((s) => ({
      ...s,
      currentWorkspace: workspace,
      currentSubPage: WORKSPACE_DEFAULTS[workspace],
    }));
  }, []);

  const setSubPage = useCallback((subPage: SubPageId) => {
    setState((s) => ({ ...s, currentSubPage: subPage }));
  }, []);

  // Legacy compat — maps old PageId calls to workspace-aware routing
  const setPage = useCallback((page: PageId) => {
    setState((s) => {
      for (const [ws, pages] of Object.entries(WORKSPACE_SUBPAGES)) {
        if (pages.includes(page)) {
          return {
            ...s,
            currentWorkspace: ws as WorkspaceId,
            currentSubPage: page,
          };
        }
      }
      return s;
    });
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
    setState((s) => {
      const newHandshakes = [];
      for (const h of s.handshakes) {
        if (h.id !== id) newHandshakes.push(h);
      }
      return {
        ...s,
        handshakes: newHandshakes,
      };
    });
  }, []);

  return {
    state,
    setWorkspace,
    setSubPage,
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
