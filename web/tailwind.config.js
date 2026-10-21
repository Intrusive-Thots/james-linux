/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#071018",
        panel: "#0d1824",
        raised: "#132233",
        fg: "#e8eef4",
        muted: "#8b9bb0",
        line: "#1c3146",
        bg: {
          DEFAULT: "#0B1120",
          panel: "#111827",
          elevated: "#1F2937",
          surface: "#161E2E",
        },
        accent: {
          DEFAULT: "#2EC4B6",
          fg: "#04221E",
          cyan: "#22D3EE",
          purple: "#8B5CF6",
        },
        danger: "#EF4444",
        success: "#10B981",
        warning: "#F59E0B",
        text: {
          primary: "#E5E7EB",
          secondary: "#94A3B8",
          muted: "#64748B",
        },
        border: {
          DEFAULT: "rgba(0,255,255,0.08)",
          subtle: "rgba(255,255,255,0.04)",
          hover: "rgba(34,211,238,0.25)",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        h1: ["32px", { lineHeight: "40px", fontWeight: "700" }],
        h2: ["24px", { lineHeight: "32px", fontWeight: "600" }],
        h3: ["18px", { lineHeight: "28px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "22px", fontWeight: "400" }],
        small: ["12px", { lineHeight: "18px", fontWeight: "400" }],
        xs: ["11px", { lineHeight: "16px", fontWeight: "500" }],
      },
      spacing: {
        micro: "4px",
        sm: "8px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "48px",
      },
      borderRadius: {
        card: "18px",
        btn: "12px",
        tag: "8px",
      },
      boxShadow: {
        card: "0 0 0 1px rgba(255,255,255,0.02), 0 8px 24px rgba(0,0,0,0.35)",
        "card-hover":
          "0 0 0 1px rgba(34,211,238,0.1), 0 12px 32px rgba(0,0,0,0.45)",
        glow: "0 0 20px rgba(34,211,238,0.15)",
        "glow-strong": "0 0 30px rgba(34,211,238,0.3)",
        border: "0 0 0 1px #1c3146",
        select: "inset 3px 0 0 0 #2EC4B6",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "scan-line": "scanLine 2s linear infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-in": "slideIn 0.25s ease-out",
      },
      keyframes: {
        scanLine: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
      maxWidth: {
        dashboard: "1600px",
      },
    },
  },
  plugins: [],
};
