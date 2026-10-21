import { AnimatePresence, motion } from "framer-motion";
import { PlugZap } from "lucide-react";

interface ConnectionBannerProps {
  connected: boolean;
}

/**
 * Backend-offline guidance.
 *
 * When the WebSocket link to the JAMES backend is down, the app otherwise only
 * surfaces a small "OFFLINE" chip in the top nav, which leaves a first-run
 * operator stranded. This banner names the problem plainly and gives the exact
 * recovery command. It animates in once and removes itself the moment the
 * backend connects, so it never competes with live data.
 */
export function ConnectionBanner({ connected }: ConnectionBannerProps) {
  return (
    <AnimatePresence initial={false}>
      {!connected && (
        <motion.div
          role="status"
          aria-live="polite"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="flex-shrink-0 overflow-hidden border-b border-warning/25 bg-warning/[0.07]"
        >
          <div className="flex items-center gap-md px-lg py-[10px]">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-btn border border-warning/30 bg-warning/10">
              <PlugZap className="h-4 w-4 text-warning" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body font-semibold text-text-primary">
                Backend offline — the dashboard can&rsquo;t receive live data.
              </p>
              <p className="text-small text-warning/90">
                Start the API server, then this banner clears on its own.
              </p>
            </div>
            <code className="hidden flex-shrink-0 rounded-tag border border-warning/25 bg-bg-panel px-sm py-[6px] font-mono text-small text-warning sm:block">
              ./launch_ui.sh --api
            </code>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
