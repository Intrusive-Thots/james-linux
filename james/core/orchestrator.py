"""
JAMES Orchestrator.

Central coordinator that connects tool wrappers, the execution layer,
skill definitions, and the GUI. Maintains a task log and emits
signals the GUI can subscribe to.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from james.layers.native import NativeLayer
from james.tools.parrot import Nmap, AircrackSuite, Hashcat, John

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


class TaskEntry:
    """Single entry in the task log."""

    def __init__(self, action: str, tool: str, params: dict):
        self.timestamp = datetime.now().isoformat()
        self.action = action
        self.tool = tool
        self.params = params
        self.result: Optional[dict] = None
        self.status = "pending"  # pending | running | done | error

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "tool": self.tool,
            "params": self.params,
            "result": self.result,
            "status": self.status,
        }


class Orchestrator:
    """
    Top-level coordinator for JAMES.

    Attributes:
        layer:    NativeLayer instance
        nmap:     Nmap wrapper
        aircrack: AircrackSuite wrapper
        hashcat:  Hashcat wrapper
        john:     John wrapper
        task_log: ordered list of TaskEntry objects
    """

    def __init__(self):
        self.layer = NativeLayer()
        self.nmap = Nmap(self.layer)
        self.aircrack = AircrackSuite(self.layer)
        self.hashcat = Hashcat(self.layer)
        self.john = John(self.layer)
        self.task_log: list[TaskEntry] = []

        # callback the GUI can set to receive new log entries
        self.on_task_update: Optional[callable] = None

    # ── convenience actions ─────────────────────────────────────

    def system_check(self) -> dict:
        """Verify that required tools are installed."""
        tools = ["nmap", "aircrack-ng", "airmon-ng", "airodump-ng",
                 "aireplay-ng", "hashcat", "john", "iwconfig"]
        status = {}
        for t in tools:
            status[t] = self.layer.check_tool(t)
        return status

    def quick_recon(self, target: str) -> dict:
        """Run a fast nmap scan and log it."""
        entry = self._log("quick_recon", "nmap", {"target": target})
        result = self.nmap.quick_scan(target)
        self._finish(entry, result)
        return result

    def full_scan(self, target: str, ports: str = "1-65535") -> dict:
        entry = self._log("full_scan", "nmap", {"target": target, "ports": ports})
        result = self.nmap.scan(target, ports=ports, flags="-sV -sC", sudo=True, timeout=600)
        self._finish(entry, result)
        return result

    def wifi_interfaces(self) -> list[dict]:
        entry = self._log("wifi_interfaces", "aircrack", {})
        ifaces = self.aircrack.list_interfaces()
        self._finish(entry, {"interfaces": ifaces})
        return ifaces

    def start_monitor(self, interface: str) -> dict:
        entry = self._log("start_monitor", "aircrack", {"interface": interface})
        self.aircrack.check_kill()
        result = self.aircrack.enable_monitor(interface)
        self._finish(entry, result.as_dict())
        return result.as_dict()

    def stop_monitor(self, interface: str) -> dict:
        entry = self._log("stop_monitor", "aircrack", {"interface": interface})
        result = self.aircrack.disable_monitor(interface)
        self._finish(entry, result.as_dict())
        return result.as_dict()

    def crack_handshake(self, capture: str, wordlist: str, bssid: str = None) -> dict:
        entry = self._log("crack_handshake", "aircrack",
                          {"capture": capture, "wordlist": wordlist, "bssid": bssid})
        result = self.aircrack.crack_wpa(capture, wordlist, bssid=bssid)
        self._finish(entry, result)
        return result

    def crack_hash(self, hash_file: str, wordlist: str, mode: int = 0) -> dict:
        entry = self._log("crack_hash", "hashcat",
                          {"hash_file": hash_file, "wordlist": wordlist, "mode": mode})
        result = self.hashcat.crack(hash_file, wordlist, hash_mode=mode)
        self._finish(entry, result)
        return result

    # ── skills ──────────────────────────────────────────────────

    def load_skill(self, name: str) -> dict:
        """Load a JSON skill definition from the skills directory."""
        path = SKILLS_DIR / f"{name}.json"
        if not path.exists():
            return {"error": f"Skill '{name}' not found at {path}"}
        with open(path) as f:
            return json.load(f)

    def list_skills(self) -> list[str]:
        """Return names of available skill files."""
        if not SKILLS_DIR.exists():
            return []
        return [p.stem for p in SKILLS_DIR.glob("*.json")]

    # ── task log internals ──────────────────────────────────────

    def _log(self, action: str, tool: str, params: dict) -> TaskEntry:
        entry = TaskEntry(action, tool, params)
        entry.status = "running"
        self.task_log.append(entry)
        if self.on_task_update:
            self.on_task_update(entry)
        logger.info("[task] %s → %s %s", action, tool, params)
        return entry

    def _finish(self, entry: TaskEntry, result) -> None:
        entry.result = result
        entry.status = "done" if not (isinstance(result, dict) and "error" in result) else "error"
        if self.on_task_update:
            self.on_task_update(entry)

    def export_log(self) -> list[dict]:
        return [e.as_dict() for e in self.task_log]
