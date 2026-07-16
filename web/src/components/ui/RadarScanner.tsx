import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AP } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface RadarScannerProps {
  aps: AP[];
  selectedAP: AP | null;
  onSelectAP: (ap: AP | null) => void;
  scanning: boolean;
}

// Simple hash function to map a BSSID string to a stable angle (in radians)
function getStableAngle(bssid: string): number {
  let hash = 0;
  for (let i = 0; i < bssid.length; i++) {
    hash = bssid.charCodeAt(i) + ((hash << 5) - hash);
  }
  // Map hash to 0 - 2*PI range
  return Math.abs(hash % 360) * (Math.PI / 180);
}

// Convert dBm signal power to a radial distance percentage (10% to 90% from center)
function getRadialDistance(dbm: number): number {
  // Typical range: -100 (weakest) to -30 (strongest)
  const minDbm = -100;
  const maxDbm = -30;
  const clamped = Math.max(minDbm, Math.min(maxDbm, dbm));
  
  // Normalized 0 to 1 (0 = weakest, 1 = strongest)
  const norm = (clamped - minDbm) / (maxDbm - minDbm);
  
  // Map to distance from center (strong signal closer to center, weak closer to edge)
  // Distance percentage from center of radar
  return 90 - norm * 75; // strongest is at 15%, weakest at 90%
}

export function RadarScanner({
  aps,
  selectedAP,
  onSelectAP,
  scanning,
}: RadarScannerProps) {
  const [hoveredAP, setHoveredAP] = useState<AP | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Map APs to target coordinates on a 300x300 canvas coordinates system (center at 150, 150)
  const apBlips = useMemo(() => {
    const radius = 135; // max radius for blips within SVG viewBox="0 0 300 300"
    return aps.map((ap) => {
      const angle = getStableAngle(ap.bssid);
      const distPct = getRadialDistance(ap.power);
      const r = (distPct / 100) * radius;
      
      // Calculate coordinates relative to center (150, 150)
      const x = 150 + r * Math.cos(angle);
      const y = 150 + r * Math.sin(angle);
      
      return {
        ap,
        x,
        y,
        id: ap.bssid,
      };
    });
  }, [aps]);

  const handleMouseMove = (e: React.MouseEvent<SVGGElement>, ap: AP) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const svgEl = e.currentTarget.ownerSVGElement;
    if (svgEl) {
      const svgRect = svgEl.getBoundingClientRect();
      // Position tooltip relative to the SVG container
      setTooltipPos({
        x: rect.left - svgRect.left + rect.width / 2,
        y: rect.top - svgRect.top - 12,
      });
    }
    setHoveredAP(ap);
  };

  return (
    <div className="card flex flex-col items-center justify-between relative overflow-hidden min-h-[360px] flex-1">
      <div className="w-full flex items-center justify-between mb-sm">
        <div className="flex flex-col">
          <span className="text-body font-semibold text-text-primary">Tactical Airspace</span>
          <span className="text-xs text-text-muted">WiFi Signal Distribution</span>
        </div>
        <span
          className={cn(
            "text-xs px-2 py-0.5 rounded-full font-mono font-semibold",
            scanning
              ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 animate-pulse"
              : "bg-bg-elevated text-text-muted border border-border"
          )}
        >
          {scanning ? "SWEEPING..." : "STANDBY"}
        </span>
      </div>

      <div className="relative w-full max-w-[260px] aspect-square flex items-center justify-center my-auto">
        <svg
          viewBox="0 0 300 300"
          className="w-full h-full text-text-muted/20 select-none"
        >
          <defs>
            {/* Radar Sweep Gradient */}
            <radialGradient id="sweepGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(34, 211, 238, 0)" />
              <stop offset="90%" stopColor="rgba(34, 211, 238, 0.02)" />
              <stop offset="98%" stopColor="rgba(34, 211, 238, 0.25)" />
              <stop offset="100%" stopColor="rgba(34, 211, 238, 0.4)" />
            </radialGradient>

            {/* Sweep trail overlay */}
            <linearGradient id="sweepTrail" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(34, 211, 238, 0.25)" />
              <stop offset="30%" stopColor="rgba(34, 211, 238, 0.05)" />
              <stop offset="100%" stopColor="rgba(34, 211, 238, 0)" />
            </linearGradient>

            {/* Blip glow filters */}
            <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            
            <filter id="glow-purple" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Concentric grid lines */}
          <circle cx="150" cy="150" r="135" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="95" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="55" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="15" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />

          {/* Crosshairs */}
          <line x1="15" y1="150" x2="285" y2="150" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
          <line x1="150" y1="15" x2="150" y2="285" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />

          {/* Radar Sweep Arc */}
          {scanning && (
            <g className="origin-[150px_150px] animate-[spin_5s_linear_infinite]">
              {/* Rotating line */}
              <line x1="150" y1="150" x2="150" y2="15" stroke="#22D3EE" strokeWidth="1.5" filter="url(#glow-cyan)" />
              {/* Pie slice representing the sweep tail */}
              <path
                d="M 150 150 L 150 15 A 135 135 0 0 1 245.4 245.4 Z"
                fill="url(#sweepTrail)"
                opacity="0.7"
              />
            </g>
          )}

          {/* Access Point Blips */}
          <g>
            <AnimatePresence>
              {apBlips.map(({ ap, x, y, id }) => {
                const isSelected = selectedAP?.bssid === ap.bssid;
                const isWps = ap.wps;
                const color = isSelected 
                  ? "#8B5CF6" // Purple for selected
                  : isWps 
                    ? "#10B981" // Green for WPS vulnerable
                    : "#22D3EE"; // Cyan for default WPA

                return (
                  <motion.g
                    key={id}
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0 }}
                    transition={{ type: "spring", stiffness: 200, damping: 15 }}
                    className="cursor-pointer"
                    onClick={() => onSelectAP(isSelected ? null : ap)}
                    onMouseEnter={(e) => handleMouseMove(e, ap)}
                    onMouseLeave={() => setHoveredAP(null)}
                  >
                    {/* Blip Outer Ring (pulse animation) */}
                    <circle
                      cx={x}
                      cy={y}
                      r={isSelected ? 10 : 6}
                      fill="none"
                      stroke={color}
                      strokeWidth="1.5"
                      className={cn(
                        "opacity-40 origin-[center]",
                        (scanning || isSelected) && "animate-ping"
                      )}
                      style={{ animationDuration: isSelected ? "1.5s" : "2.5s" }}
                    />

                    {/* Core dot */}
                    <circle
                      cx={x}
                      cy={y}
                      r={isSelected ? 5 : 4}
                      fill={color}
                      className="transition-all duration-300"
                      filter={isSelected ? "url(#glow-purple)" : "url(#glow-cyan)"}
                    />
                  </motion.g>
                );
              })}
            </AnimatePresence>
          </g>
        </svg>

        {/* Floating Tooltip HTML Overlay */}
        <AnimatePresence>
          {hoveredAP && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 4 }}
              transition={{ duration: 0.12 }}
              style={{
                position: "absolute",
                left: tooltipPos.x,
                top: tooltipPos.y,
                transform: "translate(-50%, -100%)",
                pointerEvents: "none",
                zIndex: 50,
              }}
              className="bg-bg-panel border border-accent-cyan/30 rounded-tag p-sm shadow-glow text-left min-w-[150px] pointer-events-none"
            >
              <div className="text-small font-bold text-text-primary truncate max-w-[180px]">
                {hoveredAP.essid || <span className="italic text-text-muted">&lt;Hidden SSID&gt;</span>}
              </div>
              <div className="text-xs text-text-muted font-mono">{hoveredAP.bssid}</div>
              <div className="flex items-center justify-between text-xs mt-1 pt-1 border-t border-border-subtle">
                <span className="text-text-secondary">Signal:</span>
                <span className={cn(
                  "font-mono font-semibold",
                  hoveredAP.power >= -55 ? "text-success" : hoveredAP.power >= -75 ? "text-warning" : "text-danger"
                )}>
                  {hoveredAP.power} dBm
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">CH / Security:</span>
                <span className="font-mono text-accent-cyan font-semibold">
                  {hoveredAP.channel} · {hoveredAP.privacy.split(" ")[0]}
                </span>
              </div>
              {hoveredAP.wps && (
                <div className="text-[10px] text-success font-semibold flex items-center gap-1 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                  WPS ENABLED (PIXIE VULN)
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Legend / Quick stats */}
      <div className="w-full flex items-center justify-around border-t border-border/40 pt-xs text-xs font-mono text-text-secondary">
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-cyan inline-block shadow-[0_0_8px_rgba(34,211,238,0.4)]" />
          <span>AP</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-success inline-block shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
          <span>WPS</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-purple inline-block shadow-[0_0_8px_rgba(139,92,246,0.4)]" />
          <span>Selected</span>
        </div>
      </div>
    </div>
  );
}
