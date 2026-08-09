import { useState, useMemo, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AP } from "../../hooks/useAppState";
import { cn } from "../../lib/utils";

interface AirspaceHeatmapProps {
  aps: AP[];
  selectedAP: AP | null;
  onSelectAP: (ap: AP | null) => void;
  scanning: boolean;
  standalone?: boolean;
}

// Stable angle mapping function using BSSID hash
function getStableAngle(bssid: string): number {
  let hash = 0;
  for (let i = 0; i < bssid.length; i++) {
    hash = bssid.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash % 360) * (Math.PI / 180);
}

// Map signal strength to radial distance from center
function getRadialDistance(dbm: number): number {
  const minDbm = -100;
  const maxDbm = -30;
  const clamped = Math.max(minDbm, Math.min(maxDbm, dbm));
  const norm = (clamped - minDbm) / (maxDbm - minDbm);
  // Strong signal closer to center (15% distance), weak signal closer to edge (90% distance)
  return 90 - norm * 75;
}

// Map security type to semantic colors
function getSecurityColor(privacy: string): string {
  if (privacy.includes("OPN")) return "#10B981"; // Green for Open
  if (privacy.includes("WPA3")) return "#8B5CF6"; // Purple for WPA3
  if (privacy.includes("WEP")) return "#EF4444"; // Red for WEP
  return "#F59E0B"; // Orange for WPA2/WPA
}

export const AirspaceHeatmap = memo(function AirspaceHeatmap({
  aps,
  selectedAP,
  onSelectAP,
  scanning,
  standalone = true,
}: AirspaceHeatmapProps) {
  const [hoveredAP, setHoveredAP] = useState<AP | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Map AP entries to canvas coordinates system (0-300 grid, center 150, 150)
  const apNodes = useMemo(() => {
    const maxRadius = 135; // max radius for blips within SVG
    return aps.map((ap) => {
      const angle = getStableAngle(ap.bssid);
      const distPct = getRadialDistance(ap.power);
      const r = (distPct / 100) * maxRadius;
      
      const x = 150 + r * Math.cos(angle);
      const y = 150 + r * Math.sin(angle);

      // Signal coverage radius for heatmap gradient
      const coverageRadius = Math.max(25, (ap.power + 105) * 1.4);
      const color = getSecurityColor(ap.privacy);
      const nodeSize = 4 + Math.min(ap.clients, 5);

      return {
        ap,
        x,
        y,
        color,
        coverageRadius,
        nodeSize,
        id: ap.bssid,
      };
    });
  }, [aps]);

  const handleMouseMove = (e: React.MouseEvent<SVGGElement>, ap: AP) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const svgEl = e.currentTarget.ownerSVGElement;
    if (svgEl) {
      const svgRect = svgEl.getBoundingClientRect();
      setTooltipPos({
        x: rect.left - svgRect.left + rect.width / 2,
        y: rect.top - svgRect.top - 12,
      });
    }
    setHoveredAP(ap);
  };

  const content = (
    <>
      {/* SVG CSS Styles for modular performance-tuned keyframe animations */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes sweep-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes ripple-wave {
          0% { transform: scale(0.6); opacity: 0.9; }
          100% { transform: scale(2.4); opacity: 0; }
        }
        @keyframes client-orbit {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulse-light {
          0%, 100% { opacity: 0.15; }
          50% { opacity: 0.35; }
        }
        .anim-sweep {
          transform-origin: 150px 150px;
          animation: sweep-spin 6s linear infinite;
        }
        .anim-ripple {
          transform-origin: center;
          animation: ripple-wave 2.8s cubic-bezier(0.1, 0.8, 0.3, 1) infinite;
        }
        .anim-orbit {
          transform-origin: center;
          animation: client-orbit 10s linear infinite;
        }
        .anim-pulse-bg {
          animation: pulse-light 3s ease-in-out infinite;
        }
      ` }} />

      {standalone && (
        <div className="w-full flex items-center justify-between mb-md">
          <div className="flex flex-col">
            <span className="text-body font-bold text-text-primary uppercase tracking-wider">Airspace Signal Heatmap</span>
            <span className="text-xs text-text-muted">Real-time thermal signal boundaries & threat vectors</span>
          </div>
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full font-mono font-semibold",
              scanning
                ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 animate-pulse"
                : "bg-bg-elevated text-text-muted border border-border"
            )}
          >
            {scanning ? "SWEEPING AIRSPACE..." : "STANDBY"}
          </span>
        </div>
      )}

      <div className="relative w-full max-w-[340px] aspect-square flex items-center justify-center my-auto">
        <svg
          viewBox="0 0 300 300"
          className="w-full h-full text-text-muted/15 select-none"
        >
          <defs>
            {/* Standard scan line gradient */}
            <linearGradient id="sweepTrailGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(34, 211, 238, 0.25)" />
              <stop offset="25%" stopColor="rgba(34, 211, 238, 0.05)" />
              <stop offset="100%" stopColor="rgba(34, 211, 238, 0)" />
            </linearGradient>

            {/* Glowing filters */}
            <filter id="glow-cyan-node" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            
            <filter id="glow-selected-node" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            {/* Generate dynamic gradients for each AP to show thermal signal coverage */}
            {apNodes.map((node) => (
              <radialGradient
                key={`grad-${node.id}`}
                id={`heat-grad-${node.id}`}
                cx="50%"
                cy="50%"
                r="50%"
              >
                <stop offset="0%" stopColor={node.color} stopOpacity="0.25" />
                <stop offset="40%" stopColor={node.color} stopOpacity="0.12" />
                <stop offset="100%" stopColor={node.color} stopOpacity="0" />
              </radialGradient>
            ))}
          </defs>

          {/* Grid Boundaries */}
          <circle cx="150" cy="150" r="135" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="95" fill="none" stroke="currentColor" strokeWidth="0.75" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="55" fill="none" stroke="currentColor" strokeWidth="0.75" strokeDasharray="3 3" />
          <circle cx="150" cy="150" r="15" fill="none" stroke="currentColor" strokeWidth="0.5" strokeDasharray="3 3" />

          {/* Crosshair Axes */}
          <line x1="15" y1="150" x2="285" y2="150" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />
          <line x1="150" y1="15" x2="150" y2="285" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />

          {/* 1. Heatmap layer: Overlapping signal coverage circles */}
          <g className="anim-pulse-bg">
            {apNodes.map((node) => (
              <circle
                key={`heat-${node.id}`}
                cx={node.x}
                cy={node.y}
                r={node.coverageRadius}
                fill={`url(#heat-grad-${node.id})`}
                pointerEvents="none"
              />
            ))}
          </g>

          {/* 2. Rotating Radar Sweep */}
          {scanning && (
            <g className="anim-sweep">
              <line x1="150" y1="150" x2="150" y2="15" stroke="#22D3EE" strokeWidth="1" opacity="0.7" filter="url(#glow-cyan-node)" />
              <path
                d="M 150 150 L 150 15 A 135 135 0 0 1 245.4 245.4 Z"
                fill="url(#sweepTrailGrad)"
                opacity="0.6"
              />
            </g>
          )}

          {/* 3. Interactive AP Nodes layer */}
          <g>
            <AnimatePresence>
              {apNodes.map((node) => {
                const isSelected = selectedAP?.bssid === node.ap.bssid;
                const rippleSpeed = Math.max(1.2, 4 - (node.ap.power + 100) / 20); // Faster ripples for stronger signal

                return (
                  <motion.g
                    key={node.id}
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0 }}
                    transition={{ type: "spring", stiffness: 180, damping: 14 }}
                    className="cursor-pointer"
                    onClick={() => onSelectAP(isSelected ? null : node.ap)}
                    onMouseMove={(e) => handleMouseMove(e, node.ap)}
                    onMouseLeave={() => setHoveredAP(null)}
                  >
                    {/* Expand Beacon ripples when active */}
                    {(scanning || isSelected) && (
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={node.nodeSize * 2.5}
                        fill="none"
                        stroke={node.color}
                        strokeWidth="1.2"
                        className="anim-ripple opacity-30"
                        style={{ animationDuration: `${rippleSpeed}s` }}
                      />
                    )}

                    {/* AP Core circle */}
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.nodeSize}
                      fill={node.color}
                      className="transition-all duration-300"
                      filter={isSelected ? "url(#glow-selected-node)" : "url(#glow-cyan-node)"}
                      stroke={isSelected ? "#FFFFFF" : "none"}
                      strokeWidth={isSelected ? 1.5 : 0}
                    />

                    {/* Orbiting client devices */}
                    {node.ap.clients > 0 && (
                      <g transform={`translate(${node.x}, ${node.y})`}>
                        {Array.from({ length: Math.min(node.ap.clients, 5) }).map((_, idx) => {
                          const dist = node.nodeSize + 6 + idx * 3;
                          const orbitDuration = 6 + idx * 4;
                          return (
                            <g
                              key={`orbit-${node.id}-${idx}`}
                              className="anim-orbit"
                              style={{ animationDuration: `${orbitDuration}s` }}
                            >
                              <circle
                                cx={dist}
                                cy={0}
                                r={1.5}
                                fill="#22D3EE"
                                className="shadow-glow opacity-80"
                              />
                            </g>
                          );
                        })}
                      </g>
                    )}

                    {/* rotating Lock-On target brackets */}
                    {isSelected && (
                      <g transform={`translate(${node.x}, ${node.y})`} className="animate-spin" style={{ animationDuration: "12s" }}>
                        <path d={`M -${node.nodeSize + 6} -${(node.nodeSize + 6) / 2} L -${node.nodeSize + 6} -${node.nodeSize + 6} L -${(node.nodeSize + 6) / 2} -${node.nodeSize + 6}`} stroke="#8B5CF6" strokeWidth="1.5" fill="none" />
                        <path d={`M ${(node.nodeSize + 6) / 2} -${node.nodeSize + 6} L ${node.nodeSize + 6} -${node.nodeSize + 6} L ${node.nodeSize + 6} -${(node.nodeSize + 6) / 2}`} stroke="#8B5CF6" strokeWidth="1.5" fill="none" />
                        <path d={`M -${node.nodeSize + 6} ${(node.nodeSize + 6) / 2} L -${node.nodeSize + 6} ${node.nodeSize + 6} L -${(node.nodeSize + 6) / 2} ${node.nodeSize + 6}`} stroke="#8B5CF6" strokeWidth="1.5" fill="none" />
                        <path d={`M ${(node.nodeSize + 6) / 2} ${node.nodeSize + 6} L ${node.nodeSize + 6} ${node.nodeSize + 6} L ${node.nodeSize + 6} ${(node.nodeSize + 6) / 2}`} stroke="#8B5CF6" strokeWidth="1.5" fill="none" />
                      </g>
                    )}

                    {/* Small text label for strong or selected nodes */}
                    {(isSelected || node.ap.power >= -50) && (
                      <text
                        x={node.x}
                        y={node.y + node.nodeSize + 11}
                        textAnchor="middle"
                        fill="#E5E7EB"
                        fontSize="8"
                        fontFamily="JetBrains Mono"
                        fontWeight="bold"
                        className="bg-black/80 pointer-events-none select-none drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]"
                      >
                        {node.ap.essid || "Hidden"}
                      </text>
                    )}
                  </motion.g>
                );
              })}
            </AnimatePresence>
          </g>
        </svg>

        {/* Float Glass Tooltip */}
        <AnimatePresence>
          {hoveredAP && (
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: 4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 4 }}
              transition={{ duration: 0.1 }}
              style={{
                position: "absolute",
                left: tooltipPos.x,
                top: tooltipPos.y,
                transform: "translate(-50%, -100%)",
                pointerEvents: "none",
                zIndex: 50,
              }}
              className="bg-bg-panel/95 backdrop-blur-md border border-accent-cyan/30 rounded-tag p-md shadow-[0_0_20px_rgba(34,211,238,0.12)] text-left min-w-[170px] pointer-events-none space-y-xs font-mono"
            >
              <div className="text-small font-extrabold text-text-primary truncate max-w-[200px] border-b border-border/20 pb-[4px]">
                {hoveredAP.essid || <span className="italic text-text-muted">&lt;Hidden SSID&gt;</span>}
              </div>
              <div className="text-[10px] text-text-muted">{hoveredAP.bssid}</div>
              
              <div className="flex items-center justify-between text-xs pt-xs">
                <span className="text-text-secondary">Signal:</span>
                <span className={cn(
                  "font-bold",
                  hoveredAP.power >= -55 ? "text-success" : hoveredAP.power >= -75 ? "text-warning" : "text-danger"
                )}>
                  {hoveredAP.power} dBm
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">Security:</span>
                <span className="font-bold text-warning">{hoveredAP.privacy.split(" ")[0]}</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">Channel:</span>
                <span className="font-bold text-accent-cyan">CH {hoveredAP.channel}</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">Clients:</span>
                <span className="font-bold text-accent-purple">{hoveredAP.clients} connected</span>
              </div>

              <div className="text-[10px] text-text-muted truncate">
                {hoveredAP.vendor !== "Unknown" ? hoveredAP.vendor : "Unknown chipset vendor"}
              </div>

              {hoveredAP.wps && (
                <div className="text-[10px] text-success font-extrabold flex items-center gap-1 border-t border-success/20 pt-[4px] mt-[4px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                  WPS PIXIE VULNERABLE
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Legend Console */}
      <div className="w-full flex items-center justify-around border-t border-border-subtle pt-sm text-[10px] font-mono text-text-secondary">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-success inline-block shadow-[0_0_8px_rgba(16,185,129,0.3)]" />
          <span>Open</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-warning inline-block shadow-[0_0_8px_rgba(245,158,11,0.3)]" />
          <span>WPA2</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-purple inline-block shadow-[0_0_8px_rgba(139,92,246,0.3)]" />
          <span>WPA3</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-danger inline-block shadow-[0_0_8px_rgba(239,68,68,0.3)]" />
          <span>WEP</span>
        </div>
      </div>
    </>
  );

  if (standalone) {
    return (
      <div className="card flex flex-col items-center justify-between relative overflow-hidden min-h-[460px] flex-1">
        {content}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-between relative overflow-hidden w-full h-full py-sm">
      {content}
    </div>
  );
});
