import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/utils";

interface SignalScopeProps {
  active: boolean; // scanning or attacking
  className?: string;
}

export function SignalScope({ active, className }: SignalScopeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(300);
  const height = 70;
  
  const path1Ref = useRef<SVGPathElement>(null);
  const path2Ref = useRef<SVGPathElement>(null);
  const path3Ref = useRef<SVGPathElement>(null);
  
  // Track animation state variables in refs to avoid React re-renders on every frame
  const stateRef = useRef({
    phase: 0,
    speed: active ? 0.15 : 0.04,
    frequency: active ? 0.08 : 0.03,
    amplitude: active ? 22 : 8,
    noise: active ? 5 : 0.5,
  });

  // Keep state sync with props
  useEffect(() => {
    stateRef.current.speed = active ? 0.18 : 0.05;
    stateRef.current.frequency = active ? 0.09 : 0.035;
    stateRef.current.amplitude = active ? 24 : 9;
    stateRef.current.noise = active ? 6 : 0.5;
  }, [active]);

  // Handle resizing of the container to keep path sharp
  useEffect(() => {
    if (!containerRef.current) return;
    
    const handleResize = () => {
      if (containerRef.current) {
        setWidth(containerRef.current.clientWidth);
      }
    };
    
    handleResize();
    const observer = new ResizeObserver(handleResize);
    observer.observe(containerRef.current);
    
    return () => observer.disconnect();
  }, []);

  // Animation Loop
  useEffect(() => {
    let animationId: number;
    
    const animate = () => {
      const state = stateRef.current;
      state.phase += state.speed;

      // Draw Wave 1 (Primary Cyan Wave)
      let d1 = `M 0 ${height / 2}`;
      // Draw Wave 2 (Secondary Purple Wave, phase-shifted)
      let d2 = `M 0 ${height / 2}`;
      // Draw Wave 3 (Background Dim Green Wave, higher frequency)
      let d3 = `M 0 ${height / 2}`;

      const step = 4; // draw point every 4px
      
      for (let x = 0; x <= width; x += step) {
        // Calculate y coordinate for Wave 1
        const sin1 = Math.sin(x * state.frequency + state.phase);
        const noise1 = (Math.random() - 0.5) * state.noise;
        const y1 = height / 2 + sin1 * state.amplitude + noise1;
        d1 += ` L ${x} ${y1}`;

        // Calculate y coordinate for Wave 2
        const sin2 = Math.sin(x * (state.frequency * 0.7) - state.phase * 0.8 + Math.PI / 4);
        const noise2 = (Math.random() - 0.5) * (state.noise * 0.7);
        const y2 = height / 2 + sin2 * (state.amplitude * 0.8) + noise2;
        d2 += ` L ${x} ${y2}`;

        // Calculate y coordinate for Wave 3
        const sin3 = Math.sin(x * (state.frequency * 1.5) + state.phase * 1.2);
        const y3 = height / 2 + sin3 * (state.amplitude * 0.4);
        d3 += ` L ${x} ${y3}`;
      }

      if (path1Ref.current) path1Ref.current.setAttribute("d", d1);
      if (path2Ref.current) path2Ref.current.setAttribute("d", d2);
      if (path3Ref.current) path3Ref.current.setAttribute("d", d3);

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [width]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "w-full h-[70px] bg-black/35 rounded-btn border border-border/40 overflow-hidden relative flex items-center justify-center backdrop-blur-sm",
        className
      )}
    >
      {/* Scope Grid Background */}
      <div className="absolute inset-0 grid grid-cols-12 grid-rows-4 pointer-events-none opacity-10">
        {Array.from({ length: 11 }).map((_, i) => (
          <div key={`v-${i}`} className="border-r border-accent-cyan h-full" style={{ gridColumnStart: i + 2 }} />
        ))}
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={`h-${i}`} className="border-b border-accent-cyan w-full" style={{ gridRowStart: i + 2 }} />
        ))}
      </div>

      {/* Floating sweep laser reflection */}
      <div 
        className={cn(
          "absolute top-0 bottom-0 w-16 bg-gradient-to-r from-transparent via-accent-cyan/15 to-transparent pointer-events-none",
          active ? "animate-[scan-line_2.5s_linear_infinite]" : "animate-[scan-line_6s_linear_infinite]"
        )}
      />

      <svg className="w-full h-full block" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {/* Wave 3 - Green Background Wave */}
        <path
          ref={path3Ref}
          fill="none"
          stroke="rgba(16, 185, 129, 0.25)"
          strokeWidth="1.5"
          className="transition-colors duration-300"
        />

        {/* Wave 2 - Purple Middle Wave */}
        <path
          ref={path2Ref}
          fill="none"
          stroke="rgba(139, 92, 246, 0.45)"
          strokeWidth="1.5"
          className="transition-colors duration-300"
        />

        {/* Wave 1 - Cyan Front Wave */}
        <path
          ref={path1Ref}
          fill="none"
          stroke="rgba(34, 211, 238, 0.85)"
          strokeWidth="2"
          className="transition-colors duration-300"
          style={{
            filter: "drop-shadow(0 0 4px rgba(34, 211, 238, 0.5))",
          }}
        />
      </svg>

      {/* Live HUD ticker overlay */}
      <div className="absolute bottom-1 right-2 font-mono text-[9px] text-text-muted flex gap-2 pointer-events-none select-none">
        <span>RF SCANNER</span>
        <span>GAIN: {active ? "AUTO (24dB)" : "STATIC (6dB)"}</span>
        <span>{active ? "STREAM: ACTIVE" : "STREAM: STABLE"}</span>
      </div>
    </div>
  );
}
