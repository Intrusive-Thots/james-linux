"""
JAMES Web API — FastAPI + WebSocket bridge between the React tactical UI
and the JAMES orchestrator backend.

Usage:
    python -m james.api.server

Serves:
    - REST endpoints for one-shot queries (system_check, wifi_interfaces, loot)
    - WebSocket /ws for real-time bidirectional comms (scan events, attack progress, logs)
"""

import asyncio
import glob
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logger = logging.getLogger("james.api")

# ── Orchestrator singleton (lazy init) ──────────────────────────
_orchestrator = None
_orch_lock = threading.Lock()


def get_orchestrator():
    """Get or create the JAMES orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        with _orch_lock:
            if _orchestrator is None:
                from james.core.orchestrator import Orchestrator

                _orchestrator = Orchestrator()
    return _orchestrator


# ── Abort flag for long-running operations ──────────────────────
_abort_flag = asyncio.Event()


# ── WebSocket connection manager ────────────────────────────────
class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        self._loop = asyncio.get_event_loop()
        logger.info("WebSocket client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(self.active))

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected clients."""
        data = json.dumps(message)
        for ws in list(self.active):  # copy list to avoid mutation issues
            try:
                await ws.send_text(data)
            except Exception:
                self.active.remove(ws)

    def broadcast_sync(self, message: dict):
        """Thread-safe broadcast from synchronous orchestrator callbacks."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)


manager = ConnectionManager()

# ── Helper: timestamped log broadcast ───────────────────────────


async def _log(level: str, message: str):
    """Broadcast a log message to all connected clients."""
    await manager.broadcast(
        {
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": time.strftime("%H:%M:%S"),
        }
    )


async def _attack_status(
    stage: str, status: str, progress: int, result: dict | None = None
):
    """Broadcast attack status to all connected clients."""
    msg: dict = {
        "type": "attack_status",
        "stage": stage,
        "status": status,
        "progress": progress,
    }
    if result is not None:
        msg["result"] = result
    await manager.broadcast(msg)


# ── FastAPI App ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("JAMES API server starting…")
    # Wire orchestrator print callback to broadcast
    orch = get_orchestrator()
    original_print = orch.on_print

    def on_print(msg: str):
        if original_print:
            original_print(msg)
        manager.broadcast_sync(
            {
                "type": "log",
                "level": "info",
                "message": msg,
                "timestamp": time.strftime("%H:%M:%S"),
            }
        )

    orch.on_print = on_print
    yield
    logger.info("JAMES API server shutting down…")


app = FastAPI(
    title="JAMES API",
    description="WebSocket + REST bridge for the JAMES Wi-Fi Pentesting Agent",
    version="2.0.0",
    lifespan=lifespan,
)

# Read allowed CORS origins from environment variable, falling back to localhost for development
allowed_origins_env = os.environ.get("JAMES_CORS_ORIGINS", "")
if allowed_origins_env:
    allow_origins = [
        origin.strip()
        for origin in allowed_origins_env.split(",")
        if origin.strip()
    ]
else:
    # Restrict to standard local development ports to prevent open CORS vulnerability
    allow_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ──────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": "JAMES", "version": "2.0.0"}


@app.get("/api/system-check")
async def system_check():
    """Check which pentesting tools are installed."""
    orch = get_orchestrator()
    return await asyncio.to_thread(orch.system_check)


@app.get("/api/interfaces")
async def wifi_interfaces():
    """List available wireless interfaces."""
    orch = get_orchestrator()
    return await asyncio.to_thread(orch.wifi_interfaces)


@app.get("/api/interfaces/audit")
async def audit_wifi():
    """Audit Wi-Fi hardware compatibility."""
    orch = get_orchestrator()
    return await asyncio.to_thread(orch.audit_wifi_hardware)


@app.get("/api/loot")
async def loot_summary():
    """Get cracked keys and loot summary."""
    orch = get_orchestrator()
    return orch.get_loot_summary()


@app.get("/api/wordlists")
async def list_wordlists():
    """List available wordlists."""
    orch = get_orchestrator()
    return await asyncio.to_thread(orch.list_wordlists)


@app.get("/api/log")
async def export_log():
    """Export the orchestrator task log."""
    orch = get_orchestrator()
    return orch.export_log()


# ── WebSocket Handler ───────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    # Send initial state
    orch = get_orchestrator()
    try:
        ifaces = await asyncio.to_thread(orch.wifi_interfaces)
    except Exception:
        ifaces = []

    await ws.send_text(
        json.dumps(
            {
                "type": "init",
                "interfaces": ifaces,
                "loot": orch.get_loot_summary(),
            }
        )
    )

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )
                continue

            action = msg.get("action")
            params = msg.get("params", {})
            request_id = msg.get("id", None)

            # Dispatch action in a task to avoid blocking the event loop
            asyncio.create_task(_handle_action(ws, orch, action, params, request_id))

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        manager.disconnect(ws)


async def _handle_action(
    ws: WebSocket,
    orch,
    action: str,
    params: dict,
    request_id: Any,
):
    """Handle a WebSocket action request."""
    try:
        result = await _dispatch(orch, action, params)
        await ws.send_text(
            json.dumps(
                {
                    "type": "result",
                    "action": action,
                    "id": request_id,
                    "data": result,
                }
            )
        )
    except Exception as e:
        logger.exception("Action '%s' failed: %s", action, e)
        await ws.send_text(
            json.dumps(
                {
                    "type": "error",
                    "action": action,
                    "id": request_id,
                    "message": str(e),
                }
            )
        )


# ── Action dispatcher ───────────────────────────────────────────


async def _dispatch(orch, action: str, params: dict) -> Any:
    """Map action strings to orchestrator methods."""

    if action == "scan_aps":
        return await _action_scan(orch, params)
    elif action == "start_monitor":
        return await asyncio.to_thread(orch.start_monitor, params.get("interface", ""))
    elif action == "stop_monitor":
        return await asyncio.to_thread(orch.stop_monitor, params.get("interface", ""))
    elif action == "capture_handshake":
        return await _action_capture(orch, params)
    elif action == "crack_wpa":
        return await _action_crack(orch, params)
    elif action == "evil_twin":
        return await _action_evil_twin(orch, params)
    elif action == "auto_pilot":
        return await _action_auto_pilot(orch, params)
    elif action == "agent_command":
        return await _action_agent_command(orch, params)
    elif action == "abort_attack":
        return await _action_abort(orch)
    elif action == "kill_james":
        await _log("warn", "KILL JAMES initiated — shutting down all operations…")
        return await asyncio.to_thread(orch.kill_james)
    elif action == "system_check":
        return await asyncio.to_thread(orch.system_check)
    elif action == "interfaces":
        return await asyncio.to_thread(orch.wifi_interfaces)
    else:
        raise ValueError(f"Unknown action: {action}")


# ── Scan ────────────────────────────────────────────────────────


async def _action_scan(orch, params: dict):
    interface = params.get("interface", "")
    duration = params.get("duration", 10)
    await manager.broadcast({"type": "scan_status", "scanning": True})
    try:
        result = await asyncio.to_thread(orch.scan_nearby_aps, interface, duration)
    except Exception as e:
        await manager.broadcast({"type": "scan_status", "scanning": False})
        await _log("error", f"Scan failed: {e}")
        return {"error": str(e)}
    await manager.broadcast({"type": "scan_status", "scanning": False})
    await manager.broadcast(
        {
            "type": "scan_results",
            "aps": result.get("aps", []),
            "count": result.get("count", 0),
        }
    )
    return result


# ── Capture Handshake ───────────────────────────────────────────


async def _action_capture(orch, params: dict):
    interface = params.get("interface", "")
    bssid = params.get("bssid", "")
    channel = params.get("channel", 0)
    essid = params.get("essid", "")

    _abort_flag.clear()
    await _attack_status("capturing", "Initializing capture…", 0)

    # 1. Ensure monitor mode
    try:
        mon_iface = await asyncio.to_thread(orch.ensure_monitor_mode, interface)
    except Exception as e:
        await _log("error", f"Failed to enter monitor mode: {e}")
        await _attack_status("idle", f"Monitor mode failed: {e}", 0)
        return {"success": False, "error": str(e)}

    # 2. Clean old captures and start airodump
    prefix = "/tmp/james_hscap"
    try:
        await asyncio.to_thread(orch.layer.run, f"rm -f {prefix}*")
        await _attack_status("capturing", "Starting packet capture…", 10)
        proc = await asyncio.to_thread(
            orch.aircrack.start_airodump,
            mon_iface,
            write_prefix=prefix,
            channel=str(channel),
            bssid=bssid,
        )
    except Exception as e:
        await _log("error", f"Airodump failed to start: {e}")
        await _attack_status("idle", f"Capture failed: {e}", 0)
        return {"success": False, "error": str(e)}

    # 3. Deauth bursts with abort checks
    for burst in range(3):
        if _abort_flag.is_set():
            await _safe_kill(orch, proc)
            await _attack_status("idle", "Attack aborted", 0)
            await _log("warn", "Attack aborted by operator.")
            return {"success": False, "error": "Aborted"}

        pct = 20 + (burst + 1) * 20  # 40, 60, 80
        await _attack_status("capturing", f"Deauth burst {burst+1}/3…", pct)
        try:
            await asyncio.to_thread(orch.aircrack.deauth, mon_iface, bssid, count=5)
        except Exception as e:
            await _log("warn", f"Deauth burst {burst+1} failed: {e}")
        await asyncio.sleep(3)

    # 4. Wait and collect
    await _attack_status("capturing", "Waiting for handshake…", 90)
    await asyncio.sleep(5)
    await _safe_kill(orch, proc)

    # 5. Check results
    cap_files = sorted(glob.glob(f"{prefix}*.cap"))

    if cap_files:
        cap_file = cap_files[0]
        await _attack_status("capturing", "Handshake captured!", 100)
        await _log("success", f"Handshake captured: {cap_file}")

        # Broadcast handshake to the vault
        await manager.broadcast(
            {
                "type": "handshake_data",
                "data": {
                    "id": f"hs-{int(time.time())}",
                    "essid": essid or bssid,
                    "bssid": bssid,
                    "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "file_path": cap_file,
                    "cracked": False,
                },
            }
        )

        # Auto-transition to cracking
        await asyncio.sleep(1)
        wifi_task = asyncio.to_thread(orch.find_wordlist, "wifi")
        pass_task = asyncio.to_thread(orch.find_wordlist, "password")
        wifi_wordlist, pass_wordlist = await asyncio.gather(wifi_task, pass_task)
        wordlist = wifi_wordlist or pass_wordlist
        if wordlist:
            await _log(
                "info",
                f"Auto-starting crack with wordlist: {Path(wordlist).name}",
            )
            crack_result = await _action_crack(
                orch,
                {
                    "capture": cap_file,
                    "wordlist": wordlist,
                    "bssid": bssid,
                    "ssid": essid,
                },
            )
            return {
                "success": True,
                "capture_file": cap_file,
                "crack": crack_result,
            }
        else:
            await _attack_status(
                "complete",
                "Captured — no wordlist found for auto-crack",
                100,
                {"found": False},
            )
            await _log(
                "warn",
                "No wordlist found. Upload one or install rockyou.txt to auto-crack.",
            )
            return {"success": True, "capture_file": cap_file}
    else:
        await _attack_status("idle", "No handshake captured", 0)
        await _log(
            "error",
            "No handshake was captured. Try moving closer or increasing deauth count.",
        )
        return {"success": False, "error": "No capture file generated"}


async def _safe_kill(orch, proc):
    """Kill a background process safely."""
    try:
        await asyncio.to_thread(orch.layer.kill_background, proc)
    except Exception as e:
        logger.debug("kill_background failed: %s", e)


# ── Crack WPA ───────────────────────────────────────────────────


async def _action_crack(orch, params: dict):
    capture = params.get("capture", "")
    wordlist = params.get("wordlist", "")
    bssid = params.get("bssid", "")
    ssid = params.get("ssid", "")

    await _attack_status("cracking", "Starting WPA crack…", 0)

    try:
        result = await asyncio.to_thread(
            orch.crack_wpa_smart,
            capture,
            wordlist,
            bssid=bssid or None,
            ssid=ssid or None,
        )
    except Exception as e:
        await _log("error", f"Crack failed: {e}")
        await _attack_status("complete", f"Crack error: {e}", 100, {"found": False})
        return {"found": False, "error": str(e)}

    if result.get("found"):
        key = result["key"]
        await _attack_status(
            "complete", f"Key found: {key}", 100, {"found": True, "key": key}
        )
        await _log("success", f"KEY CRACKED: {key}")
        # Cache the key
        try:
            orch.cache_cracked_key(bssid, key, method="smart_wpa", essid=ssid)
        except Exception:
            pass
    else:
        await _attack_status(
            "complete", "Key not found in wordlist", 100, {"found": False}
        )
        await _log("warn", "Key not found. Try a larger wordlist or Evil Twin attack.")

    return result


# ── Evil Twin ───────────────────────────────────────────────────


async def _action_evil_twin(orch, params: dict):
    interface = params.get("interface", "")
    bssid = params.get("bssid", "")
    essid = params.get("essid", "")
    channel = params.get("channel", 6)

    await _attack_status("capturing", "Launching Evil Twin…", 0)
    await _log("info", f"Deploying Evil Twin AP: {essid or 'FreeWiFi'}")

    try:
        result = await asyncio.to_thread(
            orch.pineap.start_karma_with_portal,
            interface,
            channel=channel,
            ssid=essid or "FreeWiFi",
            portal="wifi_login",
            bssid=bssid or None,
        )
    except Exception as e:
        await _log("error", f"Evil Twin failed: {e}")
        await _attack_status("idle", f"Evil Twin failed: {e}", 0)
        return {"success": False, "error": str(e)}

    if result.get("status") == "active":
        await _log(
            "success",
            f"Evil Twin active — SSID: {result.get('ssid')}, Gateway: {result.get('gateway')}",
        )
        await _attack_status(
            "capturing", "Evil Twin running — waiting for credentials…", 50
        )
        return {"success": True, **result}
    else:
        await _log("error", f"Evil Twin returned unexpected status: {result}")
        await _attack_status("idle", "Evil Twin failed", 0)
        return {"success": False, **result}


# ── Auto-Pilot ──────────────────────────────────────────────────


async def _action_auto_pilot(orch, params: dict):
    """Full autonomous attack pipeline: scan → select best target → capture → crack."""
    interface = params.get("interface", "")
    duration = params.get("duration", 15)

    _abort_flag.clear()

    # Phase 1: Scan
    await _log("info", "🤖 Auto-Pilot: Phase 1 — Scanning for targets…")
    await manager.broadcast({"type": "scan_status", "scanning": True})
    try:
        scan_result = await asyncio.to_thread(orch.scan_nearby_aps, interface, duration)
    except Exception as e:
        await manager.broadcast({"type": "scan_status", "scanning": False})
        await _log("error", f"Auto-Pilot scan failed: {e}")
        return {"success": False, "phase": "scan", "error": str(e)}

    await manager.broadcast({"type": "scan_status", "scanning": False})
    aps = scan_result.get("aps", [])
    await manager.broadcast(
        {
            "type": "scan_results",
            "aps": aps,
            "count": len(aps),
        }
    )

    if not aps:
        await _log("warn", "🤖 Auto-Pilot: No targets found. Aborting.")
        return {"success": False, "phase": "scan", "error": "No APs found"}

    if _abort_flag.is_set():
        await _log("warn", "🤖 Auto-Pilot aborted.")
        return {"success": False, "error": "Aborted"}

    # Phase 2: Select best target (strongest WPA/WPA2 with clients)
    wpa_targets = [
        ap
        for ap in aps
        if any(
            sec in (ap.get("privacy", "") or ap.get("encryption", ""))
            for sec in ["WPA", "WPA2"]
        )
    ]
    if not wpa_targets:
        wpa_targets = aps  # fallback to all

    # Sort: prefer APs with clients, then strongest signal
    wpa_targets.sort(
        key=lambda ap: (
            ap.get("clients", ap.get("num_clients", 0)),
            ap.get("power", ap.get("signal", -99)),
        ),
        reverse=True,
    )

    target = wpa_targets[0]
    target_essid = target.get("essid", target.get("ssid", ""))
    target_bssid = target.get("bssid", "")
    target_channel = target.get("channel", 0)

    await _log(
        "info",
        f"🤖 Auto-Pilot: Phase 2 — Target: {target_essid or '[Hidden]'} ({target_bssid}) CH:{target_channel}",
    )

    # Broadcast target selection
    await manager.broadcast(
        {
            "type": "auto_pilot_target",
            "target": target,
        }
    )

    if _abort_flag.is_set():
        await _log("warn", "🤖 Auto-Pilot aborted.")
        return {"success": False, "error": "Aborted"}

    # Phase 3: Capture + Crack (reuses existing flow)
    await _log("info", "🤖 Auto-Pilot: Phase 3 — Capture & Crack")
    capture_result = await _action_capture(
        orch,
        {
            "interface": interface,
            "bssid": target_bssid,
            "channel": target_channel,
            "essid": target_essid,
        },
    )

    await _log(
        "info",
        f"🤖 Auto-Pilot complete. Result: {'Success' if capture_result.get('success') else 'No key found'}",
    )
    return {
        "success": capture_result.get("success", False),
        "target": target,
        "result": capture_result,
    }


# ── Agent Command (chat) ────────────────────────────────────────


async def _action_agent_command(orch, params: dict):
    """Handle free-text commands from the agent chat interface."""
    command = params.get("command", "").strip().lower()

    if not command:
        return {"response": "No command received."}

    # Parse known commands
    if command in ("scan", "recon", "find networks", "start scan"):
        await _log("info", "🤖 Agent executing: network scan")
        ifaces = await asyncio.to_thread(orch.wifi_interfaces)
        if ifaces:
            iface = ifaces[0].get("interface", ifaces[0].get("name", ""))
            result = await _action_scan(orch, {"interface": iface, "duration": 15})
            count = result.get("count", len(result.get("aps", [])))
            return {"response": f"Scan complete. Found {count} networks."}
        return {"response": "No wireless interface found."}

    elif command in ("status", "health", "check"):
        ifaces = await asyncio.to_thread(orch.wifi_interfaces)
        loot = orch.get_loot_summary()
        return {
            "response": f"System online. {len(ifaces)} interface(s) detected. "
            f"{loot.get('cracked_count', 0)} key(s) in loot cache."
        }

    elif command in ("loot", "keys", "results", "cracked"):
        loot = orch.get_loot_summary()
        keys = loot.get("keys", [])
        if keys:
            lines = [f"  • {k['essid'] or k['id']}: {k['key']}" for k in keys]
            return {"response": "Cracked keys:\n" + "\n".join(lines)}
        return {"response": "No cracked keys yet."}

    elif command in ("stop", "abort", "cancel"):
        await _action_abort(orch)
        return {"response": "Abort signal sent."}

    elif (
        command.startswith("autopilot")
        or command.startswith("auto-pilot")
        or command.startswith("auto pilot")
    ):
        ifaces = await asyncio.to_thread(orch.wifi_interfaces)
        if ifaces:
            iface = ifaces[0].get("interface", ifaces[0].get("name", ""))
            asyncio.create_task(_action_auto_pilot(orch, {"interface": iface}))
            return {
                "response": "🤖 Auto-Pilot launched. Monitor the Attacks tab for progress."
            }
        return {"response": "No wireless interface found."}

    elif command in ("interfaces", "adapters", "wifi"):
        ifaces = await asyncio.to_thread(orch.wifi_interfaces)
        if ifaces:
            lines = [
                f"  • {i.get('interface', i.get('name', '?'))} [{i.get('mode', '?')}]"
                for i in ifaces
            ]
            return {"response": "Interfaces:\n" + "\n".join(lines)}
        return {"response": "No wireless interfaces detected."}

    elif command in ("help", "commands", "?"):
        return {
            "response": (
                "Available commands:\n"
                "  • scan — Scan for nearby networks\n"
                "  • status — System health check\n"
                "  • loot — Show cracked keys\n"
                "  • interfaces — List wireless adapters\n"
                "  • autopilot — Launch full auto attack\n"
                "  • stop — Abort current operation\n"
                "  • help — Show this message"
            )
        }

    else:
        return {
            "response": f"Unknown command: '{command}'. Type 'help' for available commands."
        }


# ── Abort ───────────────────────────────────────────────────────


async def _action_abort(orch):
    """Set abort flag and kill any running PineAP services."""
    _abort_flag.set()
    await _log("warn", "Abort signal sent. Stopping active operations…")
    try:
        await asyncio.to_thread(orch.pineap.stop_all)
    except Exception:
        pass
    await _attack_status("idle", "Aborted", 0)
    return {"status": "aborted"}


# ── Entry point ─────────────────────────────────────────────────
def main():
    """
    Run the JAMES API server.

    Initializes the FastAPI application via uvicorn. Resolves the port
    from the JAMES_API_PORT environment variable (defaulting to 8745).
    """
    port = int(os.environ.get("JAMES_API_PORT", 8745))
    uvicorn.run(
        "james.api.server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
