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
  shortcut?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, section: "Overview", shortcut: "1" },
  { id: "recon", label: "Recon", icon: Radar, section: "Operations", shortcut: "2" },
  { id: "attacks", label: "Attacks", icon: Swords, shortcut: "3" },
  { id: "handshakes", label: "Handshakes", icon: FileKey, shortcut: "4" },
  { id: "agent", label: "AI Agent", icon: Bot, section: "System", shortcut: "5" },
  { id: "logs", label: "Logs", icon: ScrollText, shortcut: "6" },
  { id: "settings", label: "Settings", icon: Settings, shortcut: "7" },
];

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  return (
    <aside className="w-[260px] h-full border-r border-border flex-shrink-0 flex flex-col bg-bg-panel/50">
      {/* Nav Items */}
      <nav className="flex-1 py-lg px-sm overflow-y-auto">
        {NAV_ITEMS.map((item, index) => {
          const isActive = currentPage === item.id;
          const Icon = item.icon;

          let showSection = false;
          if (item.section) {
            // Find the last section before this item
            let prevSection;
            for (let i = index - 1; i >= 0; i--) {
              if (NAV_ITEMS[i].section) {
                prevSection = NAV_ITEMS[i].section;
                break;
              }
            }
            showSection = item.section !== prevSection;
          }

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
                <span className="flex-1 text-left">{item.label}</span>
                {item.shortcut && (
                  <span
                    className={cn(
                      "text-[10px] font-mono px-[6px] py-[2px] rounded border flex-shrink-0 ml-auto",
                      isActive
                        ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/30"
                        : "bg-bg-elevated text-text-muted border-border"
                    )}
                  >
                    Alt+{item.shortcut}
                  </span>
                )}
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
