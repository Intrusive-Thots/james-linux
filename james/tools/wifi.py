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
        return self.layer.run(
            shlex.join(["airmon-ng", "start", interface_name(interface)]), sudo=True, timeout=30
        )

    def disable_monitor(self, interface: str) -> CommandResult:
        return self.layer.run(
            shlex.join(["airmon-ng", "stop", interface_name(interface)]), sudo=True, timeout=30
        )

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
