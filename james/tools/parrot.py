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
        result = self.layer.run('iwconfig 2>/dev/null', timeout=10)
        interfaces = []
        current = {}
        for line in result.stdout.splitlines():
            if 'no wireless extensions' in line:
                if current:
                    interfaces.append(current)
                    current = {}
                continue
            if line and (not line.startswith(' ')) and (not line.startswith('\t')):
                if current:
                    interfaces.append(current)
                iface = line.split()[0]
                mode = 'unknown'
                if 'Mode:' in line:
                    mode = line.split('Mode:')[1].split()[0]
                current = {'interface': iface, 'mode': mode}
            elif current and 'Mode:' in line:
                current['mode'] = line.split('Mode:')[1].split()[0]
        if current:
            interfaces.append(current)
        return interfaces

    def enable_monitor(self, interface: str) -> CommandResult:
        """Put an interface into monitor mode via airmon-ng."""
        return self.layer.run(f'airmon-ng start {interface}', sudo=True, timeout=30)

    def disable_monitor(self, interface: str) -> CommandResult:
        """Restore managed mode via airmon-ng."""
        return self.layer.run(f'airmon-ng stop {interface}', sudo=True, timeout=30)

    def check_kill(self) -> CommandResult:
        """Kill processes that might interfere with monitor mode."""
        return self.layer.run('airmon-ng check kill', sudo=True, timeout=15)

    def start_airodump(self, interface: str, *, channel: Optional[int]=None, bssid: Optional[str]=None, write_prefix: Optional[str]=None):
        """
        Start airodump-ng in the background. Returns the Popen handle.

        The caller should use NativeLayer.kill_background(proc) to stop it.
        """
        parts = ['airodump-ng']
        if channel:
            parts.append(f'--channel {channel}')
        if bssid:
            parts.append(f'--bssid {bssid}')
        if write_prefix:
            parts.append(f'-w {write_prefix}')
            parts.append('--output-format pcap,csv')
        parts.append(interface)
        return self.layer.run_background(' '.join(parts), sudo=True)

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
                with open(csv_content, 'r', encoding='utf-8', errors='ignore') as f:
                    csv_content = f.read()
            except Exception as e:
                logger.warning("Could not read CSV file %s: %s", csv_content, e)
                return {'aps': [], 'stations': []}

        aps = []
        stations = []
        section = 0
        for line in csv_content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('BSSID,'):
                section = 1
                continue
            elif line.startswith('Station MAC,'):
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
                    aps.append({'bssid': bssid, 'channel': parts[3], 'privacy': parts[5], 'power': power, 'essid': parts[13] if len(parts) > 13 else ''})
                elif section == 3 and len(parts) >= 6:
                    station_mac = parts[0]
                    connected_bssid = parts[5]
                    try:
                        cli_power = int(parts[3])
                    except (ValueError, IndexError):
                        cli_power = -100
                    # Probed SSIDs are in column 6+
                    probes = ','.join(p.strip() for p in parts[6:] if p.strip()) if len(parts) > 6 else ''
                    stations.append({
                        'station_mac': station_mac,
                        'bssid': connected_bssid if connected_bssid != '(not associated)' else '',
                        'power': cli_power,
                        'probes': probes,
                    })
            except Exception as e:
                logger.debug("Failed to parse airodump CSV line: '%s'. Error: %s", line, e)
        return {'aps': aps, 'stations': stations}

    def deauth(self, interface: str, bssid: str, *, count: int=10, client: Optional[str]=None) -> CommandResult:
        """Send deauthentication frames."""
        client_arg = f'-c {shlex.quote(client)}' if client else ''
        cmd = f'aireplay-ng -0 {count} -a {shlex.quote(bssid)} {client_arg} -D {shlex.quote(interface)}'
        return self.layer.run(cmd, sudo=True, timeout=60)

    def crack_wpa(self, capture_file: str, wordlist: str, *, bssid: Optional[str]=None) -> dict:
        """
        Run aircrack-ng against a capture file.
        Returns dict with 'found', 'key', and raw output.
        """
        bssid_arg = f'-b {shlex.quote(bssid)}' if bssid else ''
        cmd = f'aircrack-ng {bssid_arg} -w {shlex.quote(wordlist)} {shlex.quote(capture_file)}'
        result = self.layer.run(cmd, timeout=600)
        found = False
        key = ''
        for line in result.stdout.splitlines():
            if 'KEY FOUND!' in line:
                found = True
                match = re.search('\\[\\s*(.+?)\\s*\\]', line)
                if match:
                    key = match.group(1)
                break
        return {'command': cmd, 'found': found, 'key': key, 'returncode': result.returncode, 'output': result.stdout[-2000:]}

    def check_handshake(self, capture_file: str, bssid: str) -> bool:
        """Check if a valid handshake exists in the capture file."""
        cmd = f'aircrack-ng -b {shlex.quote(bssid)} {shlex.quote(capture_file)}'
        result = self.layer.run(cmd, timeout=10)
        return '1 handshake' in result.stdout or 'WPA (1 handshake)' in result.stdout

    def fake_auth(self, interface: str, bssid: str, *, delay: int=0) -> CommandResult:
        """Perform fake authentication against a WEP AP."""
        cmd = f"aireplay-ng -1 {delay} -e '' -a {shlex.quote(bssid)} -h $(macchanger -s {shlex.quote(interface)} | grep -oP '[0-9a-f:]+' | head -1) {shlex.quote(interface)}"
        return self.layer.run(cmd, sudo=True, timeout=30)

    def arp_replay(self, interface: str, bssid: str, *, timeout: int=300) -> CommandResult:
        """ARP request replay attack to generate IVs for WEP cracking."""
        cmd = f'aireplay-ng -3 -b {shlex.quote(bssid)} {shlex.quote(interface)}'
        return self.layer.run(cmd, sudo=True, timeout=timeout)

    def chopchop(self, interface: str, bssid: str, *, timeout: int=300) -> dict:
        """KoreK chopchop attack — decrypt a WEP packet without the key."""
        cmd = f'aireplay-ng -4 -b {shlex.quote(bssid)} {shlex.quote(interface)} -F'
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {'command': cmd, 'success': 'Use packetforge-ng' in result.stdout or result.returncode == 0, 'output': result.stdout[-2000:]}

    def fragment_attack(self, interface: str, bssid: str, *, timeout: int=300) -> dict:
        """Fragmentation attack — obtain a PRGA keystream from WEP."""
        cmd = f'aireplay-ng -5 -b {shlex.quote(bssid)} {shlex.quote(interface)} -F'
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {'command': cmd, 'success': 'Use packetforge-ng' in result.stdout or result.returncode == 0, 'output': result.stdout[-2000:]}

    def crack_wep(self, capture_file: str, *, bssid: Optional[str]=None) -> dict:
        """Crack WEP key from captured IVs."""
        bssid_arg = f'-b {shlex.quote(bssid)}' if bssid else ''
        cmd = f'aircrack-ng {bssid_arg} {shlex.quote(capture_file)}'
        result = self.layer.run(cmd, timeout=300)
        found = False
        key = ''
        for line in result.stdout.splitlines():
            if 'KEY FOUND!' in line:
                found = True
                match = re.search('\\[\\s*(.+?)\\s*\\]', line)
                if match:
                    key = match.group(1)
                break
        return {'command': cmd, 'found': found, 'key': key, 'output': result.stdout[-2000:]}

    def interactive_replay(self, interface: str, bssid: str, *, timeout: int=120) -> CommandResult:
        """Interactive packet selection replay (aireplay-ng -2)."""
        cmd = f'aireplay-ng -2 -b {shlex.quote(bssid)} -F {shlex.quote(interface)}'
        return self.layer.run(cmd, sudo=True, timeout=timeout)

class Hashcat:
    """Wrapper around hashcat."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def crack(self, hash_file: str, wordlist: str, *, hash_mode: int=0, rules: Optional[str]=None, timeout: int=600) -> dict:
        rules_arg = f'-r {shlex.quote(rules)}' if rules else ''
        cmd = f'hashcat -m {int(hash_mode)} {rules_arg} {shlex.quote(hash_file)} {shlex.quote(wordlist)} --force'
        result = self.layer.run(cmd, timeout=timeout)
        return {'command': cmd, 'success': result.success, 'output': result.stdout[-3000:], 'stderr': result.stderr[-1000:]}

    def identify_hash(self, hash_value: str) -> dict:
        """Use hashcat's built-in hash identification (--identify)."""
        cmd = f'echo {hash_value!r} | hashcat --identify'
        result = self.layer.run(cmd, timeout=30)
        return {'output': result.stdout, 'stderr': result.stderr}

class Hcxtools:
    """Wrapper around hcxdumptool and hcxpcapngtool for clientless PMKID attacks."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def capture_pmkid(self, interface: str, output_pcapng: str, *, timeout: int=600) -> dict:
        """Run hcxdumptool to capture PMKID hashes from nearby APs."""
        cmd = f'timeout {int(timeout)} hcxdumptool -i {shlex.quote(interface)} -o {shlex.quote(output_pcapng)} --enable_status=15'
        result = self.layer.run(cmd, sudo=True, timeout=timeout + 10)
        return {'command': cmd, 'output': result.stdout[-2000:], 'stderr': result.stderr[-2000:]}

    def extract_hashes(self, pcapng_file: str, output_hash_file: str) -> dict:
        """Extract crackable hashes (hc22000 format) from a pcapng using hcxpcapngtool."""
        cmd = f'hcxpcapngtool -o {shlex.quote(output_hash_file)} {shlex.quote(pcapng_file)}'
        result = self.layer.run(cmd, timeout=30)
        pmkid_count = 0
        eapol_count = 0
        for line in result.stdout.splitlines():
            if 'PMKID(s) written' in line:
                match = re.search('(\\d+)\\s+PMKID', line)
                if match:
                    pmkid_count = int(match.group(1))
            if 'EAPOL message pairs written' in line or 'EAPOL M1/M2' in line:
                match = re.search('(\\d+)\\s+EAPOL', line)
                if match:
                    eapol_count = int(match.group(1))
        return {'command': cmd, 'success': pmkid_count > 0 or eapol_count > 0, 'pmkid_count': pmkid_count, 'eapol_count': eapol_count, 'output': result.stdout}