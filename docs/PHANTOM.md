# Phantom Wireless Security Orchestrator

Phantom is the engagement console for JAMES. It lives on the `phantom-soc` branch as `web/src/phantom/` and is the default workspace when you open the React UI.

## Workflow

Recon → Triage → Capture → Analysis → Report

One primary action per state. Packets, telemetry, audit log, and the CLI start collapsed.

## Radio sources

| Source | When | What happens |
| --- | --- | --- |
| JAMES live | FastAPI / WebSocket connected | `scan_aps`, `capture_pmkid`, `capture_handshake` go to Kali radios. Results ingest into the target list. |
| SDR lab | Backend offline | Hopper campus simulation + Web Crypto PBKDF2-HMAC-SHA1 dictionary verify. |

Switch back to the original Agent / Auto / Settings chrome via **Utilities → JAMES → Agent console**.

## Authorization

Active scan and injection stay locked until a Rules of Engagement is signed (ECDSA P-256). **Sign lab range** authorizes `Hopper-*` / `00:1A:8C:*` plus the planted rogue. Live jobs need a matching custom RoE.

## Lab verify

Planted guest PSK is `Welcome1`. Capture Hopper-Guest, run analysis, generate the report.

## Files

- `web/src/phantom/lib/` — RF lab, PoA, crypto, dictionary, reports (engine)
- `web/src/phantom/components/` — SOC shell
- `web/src/phantom/james-bridge.ts` — live radio adapter
- `web/src/phantom/live-ingest.ts` — WebSocket scan / handshake ingest
