# JAMES Linux — UI Polish Backlog

Owner: impeccable (James's UX/UI improver). Ongoing, multi-session work.
All UI work lands on branch `ui-polish` only — never `master`.
Primary UI surface = `web/` (React 19 + Tailwind + Radix + framer-motion),
rendered dev server at `http://127.0.0.1:5173`. Secondary surfaces:
`dashboard/wireless_soc.html` (standalone SOC) and `james/gui/` (PyQt desktop).

Mode: **Operate** (an operator completes tasks). Ambition shows as precision,
scannability, honest empty/offline states, and themed browser surfaces — not decoration.

## How to pick up next session
Take the first unchecked item below, implement on `ui-polish`, render + screenshot
to `/workspace/jl_*.png`, keep `web` tests (`npm test`) and `pytest -q` green, commit
with a clear message. Check the box and add a one-line note. Then push `ui-polish`.

## Prioritized backlog (roughly by impact)

1. [x] **Backend-offline guidance.** When the WebSocket is disconnected the app
   only shows a tiny "OFFLINE" chip; a new operator has no idea what to do.
   Add a calm, full-width banner that names the problem and the exact recovery
   command (`./launch_ui.sh --api`). (done this run — see ConnectionBanner.tsx)
2. [x] **Dashboard empty states.** "Tactical Airspace", "Engagement HUD", and the
   signal scope render near-blank with 0 data. Give each a purposeful empty state
   with an icon, one line of what it will show, and the single next action
   ("Run a scan") instead of a dead panel. (done this run — radar now shows a
   centered icon + "No networks detected yet" + explainer + "Run a scan" button
   (and "Sweeping the airspace…" while scanning); Engagement HUD distinguishes
   "No targets in range yet" (with a scan button) from "No target selected"; the
   signal scope shows an honest "Standby · activity shows during a scan" label.)
3. [x] **TopNav runtime chips contrast + grouping.** The adapter/AP/clients/clock
   chips are 10–11px low-contrast mono on near-black (below 4.5:1). Lift contrast,
   add consistent labels, and group them so status is scannable at a glance.
   (done this run — chips are now one bordered cluster with IFACE / NETWORKS /
   CLIENTS / UPTIME labels; values lifted to text-primary and labels to
   text-secondary (≥4.5:1 on #0A0E1A), tabular-nums, missing adapter shown in
   danger red; SCANNING/ATTACK moved to their own pills reserved for live state.)
4. [x] **Recon AP table.** Tune the data table for dense scanning: tabular-nums
   numerals, right-aligned signal/channel, a real signal-strength visual per row,
   sortable headers, and a clear "no networks yet / start a scan" empty row.
   (done this run — Signal/CH/Clients right-aligned with tabular-nums; new
   per-row SignalCell shows a proportional strength meter + high-contrast dBm
   colored by bucket (green/cyan/amber/red); sort arrows reserve space and sit
   on the correct side with aria-sort; empty row now has an icon + headline +
   explainer and a "Start a scan" button, with distinct scanning and
   no-filter-match states.)
5. [x] **Attacks flow states.** Audit the attack stage UI for all states
   (idle, selecting, running, success, error) and make progress + abort obvious.
   (done this run — during a live capture/crack the Actions panel now shows a
   compact live status: spinner + phase label ("Capturing handshake" /
   "Cracking password") + LIVE pill, the current sub-stage name, a large
   tabular-nums percentage, the overall ProgressBar, and the Abort button
   directly beneath — progress and abort now sit together in the control
   column instead of a lone abort button and a progress bar buried at the
   bottom of the right telemetry card. Removed the duplicate second progress
   bar and lifted the sub-stage counter from text-muted to text-secondary for
   contrast. Idle/selecting/success/error states audited and left intact.)
6. [x] **Handshakes page.** Cracked vs pending should be instantly distinguishable;
   add copy-to-clipboard for keys/paths and an empty state.
   (done this run — cracked rows now carry a subtle success tint plus a leading
   green CheckCircle2, pending rows a leading amber Lock, so status reads at a
   glance across the table. The recovered key is now a click-to-copy control
   (Copy icon on hover, transient "Copied" check), and the row action that
   copies the capture file path now uses a real Copy icon with correct labelling
   instead of the misleading Download glyph. The empty state is a proper
   icon + "No handshakes captured yet" headline + one-line explainer that points
   to the Attacks page, and a distinct "no captures match <query>" state was
   added for an active filter with no results.)
7. [x] **Settings polish.** Consistent field styling, hover/focus/disabled states,
   and clear save affordances across panels.
   (done this run — the General panel's API-token field now uses a shared,
   themed `.input` class (added to index.css): consistent 40px height, palette
   border, a cyan focus-visible ring + hovered border, and a disabled style, so
   it matches the rest of the UI instead of a borderless box. The "Save &
   reconnect" button was a bare <button> that fell back to the browser's default
   light chrome (the undefined `bg-surface-primary`/`surface-secondary` tokens
   rendered nothing); it's now a real `.btn btn-primary` that is disabled until
   the token actually changes, with a sibling "Clear" ghost button when a token
   is stored and a live helper line ("Unsaved change…" / "A token is stored…" /
   "No token stored…"). Save affordance and dirty/disabled state are now honest.)
8. [x] **Keyboard shortcuts discoverability.** Alt+1..0 exist but are hidden; add a
   shortcuts legend/overlay (e.g. `?`), and show hints in tooltips consistently.
   (done this run — new ShortcutsOverlay.tsx is a palette-themed dialog listing
   every Alt+1..0 navigation shortcut with real <kbd> chips plus a General
   section (? toggles the help, Esc closes). It opens by pressing `?` anywhere
   (ignored while typing in a field), closes on Esc / backdrop / the X, and has
   one authored entrance (fade + rise). A discoverable "⌨ ?" trigger was added
   to the StatusBar so the shortcut is findable by mouse too. WorkspaceTabs
   already surfaces per-item Alt+N hints in its tooltips, so those stay the
   consistent in-context hint.)
9. [x] **Focus rings & browser surfaces.** Theme focus-visible rings, caret, text
   selection, and scrollbars from the palette app-wide (partially done in index.css).
   (done this run — app-wide keyboard focus now uses a 2px cyan (#22d3ee) ring
   with a 2px offset, replacing the browser's default bright-white outline that
   looked foreign on the dark tactical palette (visible before on nav tabs and
   the StatusBar "View logs" button). The ring is keyboard-only via
   :focus-visible (no ring on mouse click); inputs keep their own themed
   border+glow ring so they don't double up. Added a cyan caret-color app-wide,
   lifted the selection tint slightly (cyan 0.28 on #f0fbff), and re-themed the
   scrollbar from off-palette slate (rgba(148,163,184)) to a cyan-tinted pill
   thumb (rgba(34,211,238,.18) → .34 on hover) with Firefox scrollbar-color +
   scrollbar-width:thin for parity. All in index.css @layer base.)
10. [x] **Motion discipline.** Replace the many simultaneous pulses/animations with
    one authored entrance per view; reserve pulsing for genuinely live/active state.
    (done 2026-10-26 pm — added a global `prefers-reduced-motion: reduce` guard in
    index.css that neutralizes animation + transition durations app-wide. Dashboard:
    removed decorative `animate-pulse` from the header Radio icon, the TARGET ACQUIRED
    badge and the StatCard red glow; the only surviving pulse is the live attack-progress
    indicator. SignalScope now draws one static calm frame when idle (no rAF loop) and
    only animates the waveform + scan beam while `active`. AirspaceHeatmap gates its
    coverage pulse + orbit animation on `scanning` and makes the lock-on brackets static
    instead of spinning. Pulsing is now reserved for genuinely live/active state.)
11. [x] **AgentConsole / Logs readability.** Monospace log stream line-height,
    level color legend, auto-scroll affordance, and a filter.
    (done 2026-10-26 pm — Logs: looser row line-height (py-5px + leading-relaxed),
    timestamps lifted from text-muted to text-secondary tabular-nums, the level filter
    row now carries solid color dots so it doubles as an info/warn/error/success legend,
    the follow toggle became a "Following"/"Paused" button with a live green dot, and a
    floating "Jump to latest" pill appears when follow is paused. Search input gained a
    cyan keyboard-focus ring. AgentConsole: agent message bodies lifted from text-secondary
    to text-primary for contrast, and the command input got the same cyan focus ring.
    The existing level filter already satisfied the "filter" ask.)
12. [ ] **AutoPilot clarity.** Make the phase/stage machine legible with a clear
    stepper; align with the Airgeddon auto-pilot plan in implementation_plan.
13. [ ] **Standalone `dashboard/wireless_soc.html`.** Bring it in line with the React
    app's palette/typography and give it an honest empty/disconnected state.
14. [ ] **PyQt `james/gui/` pass.** Theme consistency, spacing, and empty states in
    the desktop tabs (wifi, autopilot, airgeddon, activity, setup, troubleshoot).
15. [ ] **Responsive / smaller viewports.** The dashboard is fixed to a large grid;
    verify and fix layout down to ~1280px and narrower.

16. [x] **Dashboard stat cards when all-zero.** The four hero-metric cards
    (Networks / Handshakes / Keys / Alerts) read as identical empty tiles on a
    fresh/offline load. Differentiate the zero state or collapse into a compact
    summary so the row carries information instead of four 0s.
    (done this run — when every metric is zero the row collapses into one
    ZeroMetricsSummary card: phase label ("Standby — no activity yet" / IDLE, or
    "Sweeping the airspace…" / SCANNING), a one-line explainer of what the row
    tracks, a compact Networks/Handshakes/Keys/Alerts legend, and a single
    "Run a scan" action. The four StatCards return as soon as any metric is
    non-zero.)
17. [x] **Signal-scope idle treatment.** With the new standby label in place,
    dim or flatten the idle waveform further so the label sits unobstructed and
    the panel clearly reads "nothing happening yet".
    (done 2026-10-26 pm as part of #10 — idle SignalScope now renders a single flat,
    low-amplitude (amp=3, noise=0) calm frame with no animation loop, so the "STANDBY —
    activity shows during a scan" label sits unobstructed.)
18. [ ] **Hardware Status vs backend-offline.** When the WebSocket is simply
    disconnected the panel still says "No adapter detected" / OFFLINE; distinguish
    "backend unreachable" from "adapter genuinely absent".

19. [ ] **Recon metric cards vs new table.** The four MiniStat tiles above the
    Recon table (Total APs / Encrypted / Open / Clients) use the same hero-tile
    pattern just addressed on the Dashboard; give them the same zero-state
    treatment or fold them into the table header for consistency.

20. [ ] **Password-cracked overlay gradient wordmark.** The full-screen
    "ACCESS GRANTED" success overlay (PasswordCrackedOverlay) renders its
    wordmark as gradient text, which the craft floor calls out as a default to
    avoid; emphasis should come from weight/size. Re-treat the success moment
    without gradient-filled type.
21. [ ] **Attacks workflow step numerals.** The idle Attack Workflow stepper
    prefixes each step with 01/02/03/04. The icons + connector already convey
    the sequence, so the numerals are redundant chrome; drop them or fold the
    ordinal into the icon badge.

22. [ ] **Settings groups are read-only but look interactive.** The Appearance /
    Notifications / Display / Session (General) and Attack Engine / Capture /
    PMKID / Paths (Advanced) groups render value labels ("Enabled", "Dark
    Tactical", …) that look like settings yet have no controls and change
    nothing. Either wire real controls (toggles/selects bound to backend) or
    relabel the blocks as a read-only "Current configuration" summary so they
    stop implying interactivity.
23. [ ] **App font vs config mismatch.** index.css `@import`s Inter and sets
    `html { font-family: Inter }`, while tailwind.config declares the sans stack
    as IBM Plex Sans. The two disagree and Inter is a flagged overused face;
    pick one intentional typeface and align the @import, the base rule, and the
    Tailwind token (self-host it per the craft floor rather than Google Fonts).
24. [ ] **NetworkGuard heading icon spacing.** On the Interfaces panel the Shield
    glyph sits flush against "NetworkGuard Self-Protection: ACTIVE" with no gap;
    give the icon/label a consistent gap like the other panel headers.

25. [ ] **Filter-input focus affordance.** The search/command inputs on Recon,
    Handshakes, Logs, AgentConsole and Agent use inline Tailwind with only
    `focus:border-border-hover` (a faint cyan 0.25 border) + `focus:outline-none`,
    so keyboard focus on them is barely visible. Promote them to the shared
    `.input` treatment (or a stronger focus ring) for consistency with Settings.
    (partial 2026-10-26 pm — the Logs search input and AgentConsole command input
    now get an accent-cyan border + 3px cyan focus ring; Recon, Handshakes and Agent
    still need the same treatment.)

26. [ ] **AgentConsole empty state.** With no messages the Live Session card is a
    large blank void below the single intro bubble. Add a centered, muted
    empty-state hint (e.g. a terminal glyph + "Send a command to begin — try scan,
    status, loot or help") so the panel reads as ready rather than unrendered.
    (noticed 2026-10-26 pm while verifying #11.)
