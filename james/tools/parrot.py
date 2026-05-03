"""
Parrot OS Tool Wrappers.

Structured Python interfaces around common pentesting CLIs.
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

import json
import re
import shlex
import xml.etree.ElementTree as ET
from typing import Optional

from james.layers.native import NativeLayer, CommandResult


class Nmap:
    """Wrapper around nmap with XML-based structured output."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        target: str,
        *,
        ports: Optional[str] = None,
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
        channel: Optional[int] = None,
        bssid: Optional[str] = None,
        write_prefix: Optional[str] = None,
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
        
        import logging
        logger = logging.getLogger(__name__)
        
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
        client: Optional[str] = None,
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
        bssid: Optional[str] = None,
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
        rules: Optional[str] = None,
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
        wordlist: Optional[str] = None,
        fmt: Optional[str] = None,
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
    """Wrapper around Reaver and Bully for WPS attacks (Pixie Dust and Bruteforce)."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

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
            "output": result.stdout[-2000:]
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
