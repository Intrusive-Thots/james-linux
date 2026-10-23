import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, Command } from "lucide-react";

interface ShortcutsOverlayProps {
  open: boolean;
  onClose: () => void;
}

interface Shortcut {
  keys: string[];
  label: string;
}

const NAVIGATION: Shortcut[] = [
  { keys: ["Alt", "1"], label: "Dashboard" },
  { keys: ["Alt", "2"], label: "Recon" },
  { keys: ["Alt", "3"], label: "Attacks" },
  { keys: ["Alt", "4"], label: "Handshakes" },
  { keys: ["Alt", "5"], label: "Agent workspace" },
  { keys: ["Alt", "6"], label: "Logs" },
  { keys: ["Alt", "7"], label: "Settings" },
  { keys: ["Alt", "8"], label: "Auto workspace" },
  { keys: ["Alt", "9"], label: "Auto-Pilot" },
  { keys: ["Alt", "0"], label: "Agent Console" },
];

const GENERAL: Shortcut[] = [
  { keys: ["?"], label: "Toggle this shortcuts help" },
  { keys: ["Esc"], label: "Close this help" },
];

function Keys({ keys }: { keys: string[] }) {
  return (
    <span className="flex items-center gap-[4px]">
      {keys.map((k, i) => (
        <kbd
          key={i}
          className="inline-flex min-w-[22px] h-[22px] items-center justify-center rounded-[6px] border border-border bg-bg-elevated px-[6px] font-mono text-xs font-semibold text-text-primary tabular-nums"
        >
          {k}
        </kbd>
      ))}
    </span>
  );
}

function Row({ s }: { s: Shortcut }) {
  return (
    <div className="flex items-center justify-between gap-md py-[7px]">
      <span className="text-body text-text-secondary">{s.label}</span>
      <Keys keys={s.keys} />
    </div>
  );
}

export function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    closeRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-lg"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <motion.div
            className="relative w-full max-w-[560px] rounded-card border border-border bg-bg-panel p-lg shadow-card"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between pb-md mb-md border-b border-border">
              <div className="flex items-center gap-sm">
                <div className="w-9 h-9 rounded-btn bg-accent-cyan/10 flex items-center justify-center">
                  <Command className="w-[18px] h-[18px] text-accent-cyan" />
                </div>
                <div>
                  <h2 className="text-h3 text-text-primary">Keyboard shortcuts</h2>
                  <p className="text-small text-text-secondary mt-[1px]">
                    Jump between views without leaving the keyboard.
                  </p>
                </div>
              </div>
              <button
                ref={closeRef}
                onClick={onClose}
                aria-label="Close shortcuts"
                className="btn btn-ghost btn-sm !h-8 !w-8 !px-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-xl gap-y-0">
              <div>
                <h3 className="text-small font-bold uppercase tracking-wider text-text-muted mb-xs">
                  Navigation
                </h3>
                <div className="divide-y divide-border-subtle">
                  {NAVIGATION.map((s) => (
                    <Row key={s.label} s={s} />
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-small font-bold uppercase tracking-wider text-text-muted mb-xs">
                  General
                </h3>
                <div className="divide-y divide-border-subtle">
                  {GENERAL.map((s) => (
                    <Row key={s.label} s={s} />
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}
