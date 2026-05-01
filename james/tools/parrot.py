"""
Parrot OS Tool Wrappers.

Structured Python interfaces around common pentesting CLIs.
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

import re
import xml.etree.ElementTree as ET

from james.layers.native import NativeLayer, CommandResult


class Nmap:
    """Wrapper around nmap with XML-based structured output."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        target: str,
        *,
        ports: str | None = None,
        flags: str = "-sV",
        sudo: bool = False,
        timeout: int = 300,
    ) -> dict:
        """
        Run an nmap scan and return structured results.

        Returns dict with keys: command, hosts[], scan_info.
        """
        port_arg = f"-p {ports}" if ports else ""
        cmd = f"nmap {flags} {port_arg} -oX - {target}"
        result = self.layer.run(cmd, sudo=sudo, timeout=timeout)
        if not result.success:
            return {"error": result.stderr, "raw": result.stdout, "command": cmd}
        return self._parse_xml(result.stdout, cmd)

    def quick_scan(self, target: str, sudo: bool = False) -> dict:
        """Fast top-100 port scan."""
        return self.scan(target, flags="-T4 -F", sudo=sudo, timeout=120)

    def os_detect(self, target: str) -> dict:
        """OS detection scan (requires root)."""
        return self.scan(target, flags="-O -sV", sudo=True, timeout=300)

    @staticmethod
    def _parse_xml(xml_str: str, cmd: str) -> dict:
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            return {"error": "Failed to parse nmap XML", "raw": xml_str, "command": cmd}

        hosts = []
        for host_el in root.findall("host"):
            addr_el = host_el.find("address")
            address = addr_el.get("addr", "unknown") if addr_el is not None else "unknown"

            status_el = host_el.find("status")
            state = status_el.get("state", "unknown") if status_el is not None else "unknown"

            ports_list = []
            ports_el = host_el.find("ports")
            if ports_el is not None:
                for port_el in ports_el.findall("port"):
                    svc = port_el.find("service")
                    state_el = port_el.find("state")
                    ports_list.append({
                        "port": int(port_el.get("portid", 0)),
                        "protocol": port_el.get("protocol", ""),
                        "state": state_el.get("state", "") if state_el is not None else "",
                        "service": svc.get("name", "") if svc is not None else "",
                        "version": svc.get("product", "") if svc is not None else "",
                    })

            os_matches = []
            os_el = host_el.find("os")
            if os_el is not None:
                for match in os_el.findall("osmatch"):
                    os_matches.append({
                        "name": match.get("name", ""),
                        "accuracy": match.get("accuracy", ""),
                    })

            hosts.append({
                "address": address,
                "state": state,
                "ports": ports_list,
                "os_matches": os_matches,
            })

        return {"command": cmd, "hosts": hosts}


class AircrackSuite:
    """Wrappers around airmon-ng, airodump-ng, aireplay-ng, aircrack-ng."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    # ── interface management ────────────────────────────────────

    def list_interfaces(self) -> list[dict]:
        """List wireless interfaces and their current mode."""
        result = self.layer.run("iwconfig 2>/dev/null", timeout=10)
        interfaces = []
        current = {}
        for line in result.stdout.splitlines():
            if line and not line.startswith(" "):
                if current:
                    interfaces.append(current)
                iface = line.split()[0]
                mode = "unknown"
                if "Mode:" in line:
                    mode = line.split("Mode:")[1].split()[0]
                current = {"interface": iface, "mode": mode}
            elif current and "Mode:" in line:
                current["mode"] = line.split("Mode:")[1].split()[0]
        if current:
            interfaces.append(current)
        return interfaces

    def enable_monitor(self, interface: str) -> CommandResult:
        """Put an interface into monitor mode via airmon-ng."""
        return self.layer.run(f"airmon-ng start {interface}", sudo=True, timeout=30)

    def disable_monitor(self, interface: str) -> CommandResult:
        """Restore managed mode via airmon-ng."""
        return self.layer.run(f"airmon-ng stop {interface}", sudo=True, timeout=30)

    def check_kill(self) -> CommandResult:
        """Kill processes that might interfere with monitor mode."""
        return self.layer.run("airmon-ng check kill", sudo=True, timeout=15)

    # ── scanning ────────────────────────────────────────────────

    def start_airodump(
        self,
        interface: str,
        *,
        channel: int | None = None,
        bssid: str | None = None,
        write_prefix: str | None = None,
    ):
        """
        Start airodump-ng in the background. Returns the Popen handle.

        The caller should use NativeLayer.kill_background(proc) to stop it.
        """
        parts = ["airodump-ng"]
        if channel:
            parts.append(f"--channel {channel}")
        if bssid:
            parts.append(f"--bssid {bssid}")
        if write_prefix:
            parts.append(f"-w {write_prefix}")
        parts.append(interface)
        return self.layer.run_background(" ".join(parts), sudo=True)

    # ── attacks ─────────────────────────────────────────────────

    def deauth(
        self,
        interface: str,
        bssid: str,
        *,
        count: int = 10,
        client: str | None = None,
    ) -> CommandResult:
        """Send deauthentication frames."""
        client_arg = f"-c {client}" if client else ""
        cmd = f"aireplay-ng -0 {count} -a {bssid} {client_arg} {interface}"
        return self.layer.run(cmd, sudo=True, timeout=60)

    # ── cracking ────────────────────────────────────────────────

    def crack_wpa(
        self,
        capture_file: str,
        wordlist: str,
        *,
        bssid: str | None = None,
    ) -> dict:
        """
        Run aircrack-ng against a capture file.
        Returns dict with 'found', 'key', and raw output.
        """
        bssid_arg = f"-b {bssid}" if bssid else ""
        cmd = f"aircrack-ng {bssid_arg} -w {wordlist} {capture_file}"
        result = self.layer.run(cmd, timeout=600)

        found = False
        key = ""
        for line in result.stdout.splitlines():
            if "KEY FOUND!" in line:
                found = True
                match = re.search(r"\[\s*(.+?)\s*\]", line)
                if match:
                    key = match.group(1)
                break

        return {
            "command": cmd,
            "found": found,
            "key": key,
            "returncode": result.returncode,
            "output": result.stdout[-2000:],  # last 2k chars
        }


class Hashcat:
    """Wrapper around hashcat."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def crack(
        self,
        hash_file: str,
        wordlist: str,
        *,
        hash_mode: int = 0,
        rules: str | None = None,
        timeout: int = 600,
    ) -> dict:
        rules_arg = f"-r {rules}" if rules else ""
        cmd = f"hashcat -m {hash_mode} {rules_arg} {hash_file} {wordlist} --force"
        result = self.layer.run(cmd, timeout=timeout)
        return {
            "command": cmd,
            "success": result.success,
            "output": result.stdout[-3000:],
            "stderr": result.stderr[-1000:],
        }

    def identify_hash(self, hash_value: str) -> dict:
        """Use hashcat's built-in hash identification (--identify)."""
        # hashcat 6.2.6+ supports --identify
        cmd = f"echo {hash_value!r} | hashcat --identify"
        result = self.layer.run(cmd, timeout=30)
        return {"output": result.stdout, "stderr": result.stderr}


class John:
    """Wrapper around John the Ripper."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def crack(
        self,
        hash_file: str,
        *,
        wordlist: str | None = None,
        fmt: str | None = None,
        timeout: int = 600,
    ) -> dict:
        parts = ["john"]
        if wordlist:
            parts.append(f"--wordlist={wordlist}")
        if fmt:
            parts.append(f"--format={fmt}")
        parts.append(hash_file)
        cmd = " ".join(parts)
        result = self.layer.run(cmd, timeout=timeout)
        return {
            "command": cmd,
            "success": result.success,
            "output": result.stdout[-3000:],
        }

    def show(self, hash_file: str) -> dict:
        """Show already-cracked passwords."""
        result = self.layer.run(f"john --show {hash_file}", timeout=30)
        return {"output": result.stdout}
