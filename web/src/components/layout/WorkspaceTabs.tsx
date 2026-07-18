import { motion } from "framer-motion";
import {
  Crosshair,
  Cpu,
  Settings,
  LayoutDashboard,
  Radar,
  Swords,
  FileKey,
  ScrollText,
  Sparkles,
  Terminal,
  Sliders,
  Wifi,
  Package,
  Stethoscope,
  Wrench,
} from "lucide-react";
import type {
  WorkspaceId,
  SubPageId,
} from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface WorkspaceTabsProps {
  currentWorkspace: WorkspaceId;
  currentSubPage: SubPageId;
  onWorkspaceChange: (ws: WorkspaceId) => void;
  onSubPageChange: (sp: SubPageId) => void;
}

interface WorkspaceConfig {
  id: WorkspaceId;
  label: string;
  icon: React.ElementType;
  accent: string;
  accentBg: string;
  accentBorder: string;
  glowColor: string;
  shortcut?: string;
}

const WORKSPACES: WorkspaceConfig[] = [
  {
    id: "agent",
    label: "AGENT",
    shortcut: "Alt+5",
    icon: Crosshair,
    accent: "text-accent-cyan",
    accentBg: "bg-accent-cyan/10",
    accentBorder: "border-accent-cyan/30",
    glowColor: "rgba(34,211,238,0.15)",
  },
  {
    id: "auto",
    label: "AUTO",
    icon: Cpu,
    accent: "text-accent-purple",
    accentBg: "bg-accent-purple/10",
    accentBorder: "border-accent-purple/30",
    glowColor: "rgba(139,92,246,0.15)",
  },
  {
    id: "settings",
    label: "SETTINGS",
    shortcut: "Alt+7",
    icon: Settings,
    accent: "text-text-secondary",
    accentBg: "bg-bg-elevated",
    accentBorder: "border-border",
    glowColor: "rgba(148,163,184,0.08)",
  },
];

interface SubPageConfig {
  id: SubPageId;
  label: string;
  icon: React.ElementType;
  shortcut?: string;
}

const AGENT_SUBPAGES: SubPageConfig[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, shortcut: "Alt+1" },
  { id: "recon", label: "Recon", icon: Radar, shortcut: "Alt+2" },
  { id: "attacks", label: "Attacks", icon: Swords, shortcut: "Alt+3" },
  { id: "handshakes", label: "Handshakes", icon: FileKey, shortcut: "Alt+4" },
  { id: "logs", label: "Logs", icon: ScrollText, shortcut: "Alt+6" },
];

const AUTO_SUBPAGES: SubPageConfig[] = [
  { id: "autopilot", label: "Auto-Pilot", icon: Sparkles },
  { id: "console", label: "Agent Console", icon: Terminal },
];

const SETTINGS_SUBPAGES: SubPageConfig[] = [
  { id: "general", label: "General", icon: Sliders },
  { id: "interfaces", label: "Interfaces", icon: Wifi },
  { id: "dependencies", label: "Dependencies", icon: Package },
  { id: "diagnostics", label: "Diagnostics", icon: Stethoscope },
  { id: "advanced", label: "Advanced", icon: Wrench },
];

const SUB_NAV_MAP: Record<WorkspaceId, SubPageConfig[]> = {
  agent: AGENT_SUBPAGES,
  auto: AUTO_SUBPAGES,
  settings: SETTINGS_SUBPAGES,
};

export function WorkspaceTabs({
  currentWorkspace,
  currentSubPage,
  onWorkspaceChange,
  onSubPageChange,
}: WorkspaceTabsProps) {
  const subPages = SUB_NAV_MAP[currentWorkspace];
  const activeWs = WORKSPACES.find((w) => w.id === currentWorkspace)!;

  return (
    <div className="flex-shrink-0 border-b border-border" style={{ background: "#0D1324" }}>
      {/* Primary Workspace Tabs */}
      <div className="flex items-center px-lg h-[44px] gap-[2px]">
        {WORKSPACES.map((ws) => {
          const isActive = currentWorkspace === ws.id;
          const Icon = ws.icon;
          return (
            <button
              key={ws.id}
              onClick={() => onWorkspaceChange(ws.id)}
              className={cn(
                "relative flex items-center gap-sm px-lg py-[8px] rounded-t-[10px] text-[13px] font-bold uppercase tracking-wider transition-all duration-200",
                isActive
                  ? `${ws.accent} bg-bg/80 border border-b-0 ${ws.accentBorder}`
                  : "text-text-muted hover:text-text-secondary border border-transparent hover:bg-bg-elevated/30"
              )}
              style={isActive ? { boxShadow: `0 -2px 12px ${ws.glowColor}` } : undefined}
            >
              <Icon className={cn("w-4 h-4", isActive ? ws.accent : "text-text-muted")} />
              <div className="flex flex-col items-start leading-none">
                <span>{ws.label}</span>
                {ws.shortcut && !isActive && (
                  <span className="text-[9px] text-text-muted/50 font-mono mt-0.5">{ws.shortcut}</span>
                )}
              </div>
              {isActive && (
                <motion.div
                  layoutId="workspace-indicator"
                  className="absolute bottom-[-1px] left-lg right-lg h-[2px] rounded-t-full"
                  style={{ background: ws.id === "agent" ? "#22D3EE" : ws.id === "auto" ? "#8B5CF6" : "#64748B" }}
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Contextual Sub-Navigation */}
      <div className="flex items-center px-lg h-[36px] gap-[4px] bg-bg/40">
        {subPages.map((sp) => {
          const isActive = currentSubPage === sp.id;
          const Icon = sp.icon;
          return (
            <button
              key={sp.id}
              onClick={() => onSubPageChange(sp.id)}
              className={cn(
                "relative flex items-center gap-[6px] px-md py-[5px] rounded-btn text-[12px] font-semibold transition-all duration-150",
                isActive
                  ? `text-text-primary ${activeWs.accentBg}`
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-elevated/40"
              )}
            >
              <Icon className={cn("w-3.5 h-3.5", isActive ? activeWs.accent : "")} />
              <span>{sp.label}</span>
              {sp.shortcut && !isActive && (
                <span className="ml-1 text-[9px] text-text-muted/50 font-mono">{sp.shortcut}</span>
              )}
              {isActive && (
                <motion.div
                  layoutId="subpage-indicator"
                  className="absolute bottom-0 left-2 right-2 h-[2px] rounded-t-full"
                  style={{ background: activeWs.id === "agent" ? "#22D3EE" : activeWs.id === "auto" ? "#8B5CF6" : "#64748B" }}
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
