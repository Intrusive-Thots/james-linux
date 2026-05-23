import { motion } from "framer-motion";
import {
  Radar,
  FileKey,
  Key,
  Wifi,
  Shield,
  Activity,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import type { AppState, PageId } from "../hooks/useAppState";

interface DashboardProps {
  state: AppState;
  onNavigate: (page: PageId) => void;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function Dashboard({ state, onNavigate }: DashboardProps) {
  const crackedCount = state.handshakes.filter((h) => h.cracked).length;
  const pendingCount = state.handshakes.filter((h) => !h.cracked).length;
  const errorCount = state.logs.filter((l) => l.level === "error").length;
  const recentLogs = state.logs.slice(-8);

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="h-full overflow-y-auto p-lg"
    >
      <div className="max-w-dashboard mx-auto space-y-lg">
        {/* Header */}
        <motion.div variants={item}>
          <h2 className="text-h2 text-text-primary mb-sm">Operator Dashboard</h2>
          <p className="text-body text-text-secondary">
            Real-time overview of your pentesting session.
          </p>
        </motion.div>

        {/* Stat Cards Row */}
        <motion.div
          variants={item}
          className="grid grid-cols-4 gap-md"
        >
          <StatCard
            icon={Radar}
            label="Networks Found"
            value={String(state.aps.length)}
            accent="cyan"
          />
          <StatCard
            icon={FileKey}
            label="Handshakes"
            value={String(state.handshakes.length)}
            accent="purple"
          />
          <StatCard
            icon={Key}
            label="Keys Cracked"
            value={String(crackedCount)}
            accent="green"
          />
          <StatCard
            icon={AlertTriangle}
            label="Errors"
            value={String(errorCount)}
            accent={errorCount > 0 ? "red" : "muted"}
          />
        </motion.div>

        {/* Main Grid: Quick Actions + Status */}
        <div className="grid grid-cols-12 gap-lg">
          {/* Quick Actions */}
          <motion.div variants={item} className="col-span-5 card">
            <div className="card-header">
              <div className="card-title">
                <Activity className="w-5 h-5 text-accent-cyan" />
                Quick Actions
              </div>
            </div>
            <div className="space-y-sm">
              <ActionButton
                label="Start Reconnaissance"
                description="Scan area for WiFi networks"
                icon={Radar}
                onClick={() => onNavigate("recon")}
              />
              <ActionButton
                label="Launch Attack"
                description="Capture handshakes and crack keys"
                icon={Shield}
                onClick={() => onNavigate("attacks")}
                variant="danger"
              />
              <ActionButton
                label="View Handshake Vault"
                description={`${pendingCount} pending · ${crackedCount} cracked`}
                icon={FileKey}
                onClick={() => onNavigate("handshakes")}
              />
            </div>
          </motion.div>

          {/* System Status */}
          <motion.div variants={item} className="col-span-7 card">
            <div className="card-header">
              <div className="card-title">
                <Wifi className="w-5 h-5 text-accent-cyan" />
                System Status
              </div>
              <span
                className={`badge-${state.adapter ? "success" : "danger"}`}
              >
                {state.adapter ? "ONLINE" : "NO ADAPTER"}
              </span>
            </div>

            <div className="space-y-md">
              <StatusRow
                label="Wireless Adapter"
                value={state.adapter || "Not connected"}
                status={state.adapter ? "ok" : "error"}
              />
              <StatusRow
                label="Adapter Mode"
                value={state.adapterMode?.toUpperCase() || "—"}
                status={state.adapterMode === "monitor" ? "active" : "idle"}
              />
              <StatusRow
                label="Scan Engine"
                value={state.scanning ? "Active" : "Standby"}
                status={state.scanning ? "active" : "idle"}
              />
              <StatusRow
                label="Attack Module"
                value={state.attack.status}
                status={
                  state.attack.stage === "idle"
                    ? "idle"
                    : state.attack.stage === "complete"
                      ? "ok"
                      : "active"
                }
              />
            </div>
          </motion.div>
        </div>

        {/* Recent Activity */}
        <motion.div variants={item} className="card">
          <div className="card-header">
            <div className="card-title">
              <Activity className="w-5 h-5 text-accent-cyan" />
              Recent Activity
            </div>
            <button
              className="btn-ghost btn-sm"
              onClick={() => onNavigate("logs")}
            >
              View All
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {recentLogs.length === 0 ? (
            <p className="text-text-muted text-body py-xl text-center">
              No activity yet. Start a recon scan to begin.
            </p>
          ) : (
            <div className="space-y-[2px] font-mono">
              {recentLogs.map((log) => (
                <div
                  key={log.id}
                  className="log-entry flex items-start gap-sm"
                >
                  <span className="text-text-muted flex-shrink-0">
                    {log.timestamp}
                  </span>
                  <span
                    className={
                      log.level === "info"
                        ? "log-info"
                        : log.level === "warn"
                          ? "log-warn"
                          : log.level === "error"
                            ? "log-error"
                            : "log-success"
                    }
                  >
                    [{log.level.toUpperCase()}]
                  </span>
                  <span className="text-text-primary">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}

/* ── Sub-components ──────────────────────────── */

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  accent: "cyan" | "purple" | "green" | "red" | "muted";
}) {
  const colors = {
    cyan: { bg: "bg-accent-cyan/8", text: "text-accent-cyan", icon: "text-accent-cyan" },
    purple: { bg: "bg-accent-purple/8", text: "text-accent-purple", icon: "text-accent-purple" },
    green: { bg: "bg-success/8", text: "text-success", icon: "text-success" },
    red: { bg: "bg-danger/8", text: "text-danger", icon: "text-danger" },
    muted: { bg: "bg-bg-elevated", text: "text-text-muted", icon: "text-text-muted" },
  };
  const c = colors[accent];

  return (
    <div className="card flex items-center gap-md">
      <div
        className={`w-12 h-12 rounded-btn ${c.bg} flex items-center justify-center flex-shrink-0`}
      >
        <Icon className={`w-6 h-6 ${c.icon}`} />
      </div>
      <div>
        <div className={`text-h2 font-bold ${c.text}`}>{value}</div>
        <div className="text-small text-text-secondary">{label}</div>
      </div>
    </div>
  );
}

function ActionButton({
  label,
  description,
  icon: Icon,
  onClick,
  variant = "default",
}: {
  label: string;
  description: string;
  icon: React.ElementType;
  onClick: () => void;
  variant?: "default" | "danger";
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-md p-md rounded-btn border border-border hover:border-border-hover hover:bg-bg-elevated/60 transition-all duration-150 text-left group"
    >
      <div
        className={`w-10 h-10 rounded-tag flex items-center justify-center flex-shrink-0 ${
          variant === "danger" ? "bg-danger/10" : "bg-bg-elevated"
        }`}
      >
        <Icon
          className={`w-5 h-5 ${
            variant === "danger"
              ? "text-danger"
              : "text-text-muted group-hover:text-accent-cyan"
          } transition-colors`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-body font-medium text-text-primary">{label}</div>
        <div className="text-small text-text-muted truncate">{description}</div>
      </div>
      <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-secondary transition-colors" />
    </button>
  );
}

function StatusRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: "ok" | "active" | "idle" | "error";
}) {
  const dotClass = {
    ok: "status-dot-success",
    active: "status-dot-active",
    idle: "status-dot-idle",
    error: "status-dot-danger",
  };

  return (
    <div className="flex items-center justify-between py-[6px]">
      <span className="text-body text-text-secondary">{label}</span>
      <div className="flex items-center gap-sm">
        <span className={dotClass[status]} />
        <span className="text-body text-text-primary font-medium">{value}</span>
      </div>
    </div>
  );
}
