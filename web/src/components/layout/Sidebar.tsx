import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Radar,
  Swords,
  FileKey,
  Bot,
  ScrollText,
  Settings,
} from "lucide-react";
import type { PageId } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface SidebarProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
}

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ElementType;
  section?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, section: "Overview" },
  { id: "recon", label: "Recon", icon: Radar, section: "Operations" },
  { id: "attacks", label: "Attacks", icon: Swords },
  { id: "handshakes", label: "Handshakes", icon: FileKey },
  { id: "agent", label: "AI Agent", icon: Bot, section: "System" },
  { id: "logs", label: "Logs", icon: ScrollText },
  { id: "settings", label: "Settings", icon: Settings },
];

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  let lastSection: string | undefined;

  return (
    <aside className="w-[260px] h-full border-r border-border flex-shrink-0 flex flex-col bg-bg-panel/50">
      {/* Nav Items */}
      <nav className="flex-1 py-lg px-sm overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = currentPage === item.id;
          const Icon = item.icon;
          const showSection = item.section && item.section !== lastSection;
          if (item.section) lastSection = item.section;

          return (
            <div key={item.id}>
              {showSection && (
                <div className="px-md pt-lg pb-sm first:pt-0">
                  <span className="text-xs font-semibold uppercase tracking-widest text-text-muted">
                    {item.section}
                  </span>
                </div>
              )}
              <button
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "relative w-full flex items-center gap-sm px-md py-[10px] rounded-btn text-body font-medium transition-all duration-150",
                  isActive
                    ? "text-text-primary bg-accent-cyan/8"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated/60"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="sidebar-active-bar"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <Icon
                  className={cn(
                    "w-[18px] h-[18px] flex-shrink-0",
                    isActive ? "text-accent-cyan" : "text-text-muted"
                  )}
                />
                <span>{item.label}</span>
              </button>
            </div>
          );
        })}
      </nav>

      {/* Bottom Branding */}
      <div className="p-md border-t border-border">
        <div className="text-xs text-text-muted text-center">
          JAMES v2.0 · Tactical UI
        </div>
      </div>
    </aside>
  );
}
