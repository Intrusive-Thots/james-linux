# Phantom's Journal

Critical learnings only.

## 2026-06-01 - WPA Cracking Wizard & Real-Time Storyteller
Learning: Non-technical users often feel lost or intimidated when launching background actions that take time (like handshake captures or dictionary cracks), resulting in zero feedback until completion. By capturing granular process milestones (sub-stages) in the backend orchestrator and passing them via WebSockets, we can render a high-tech "Telemetry HUD" showing active steps (monitor mode prep, deauth broadcast, hashcat mutation) and translate them into a plain-English "Storyteller Console". If it fails, rather than a generic error, we present an immediate recovery path (Deploy Evil Twin or Generate Targeted List).
Action: Always build deep, step-by-step progress tracking for long-running pentest operations, and pair them with contextual explanations and immediate one-click fallback recovery options to hide technical complexity from beginners.

## 2026-06-01 - Smart Attack Advisor (AP Analysis → Auto-Strategy)
Learning: Beginners should never choose between "PMKID", "deauth", or "handshake" — these terms mean nothing to them. By analyzing the target AP's properties (WPA2/WPA3, client count, signal strength), we can auto-select the optimal attack and explain the reasoning in one sentence of plain English. The key insight: AP metadata (clients=0 → PMKID, clients>0 → deauth, WPA3 → PMKID-only warning, OPN → skip) is a perfect decision tree that replaces ALL strategy UI for beginners. The recommendation badge (color + icon + explanation) gives confidence without requiring knowledge.
Action: For any multi-strategy tool, build an analysis layer that examines the target's properties and auto-selects the best approach, showing the user a plain-English recommendation instead of technical options. Always include a manual override for power users.
