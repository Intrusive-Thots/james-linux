"""
Kali/Debian tool wrappers.

Legacy module name (`parrot.py`). Structured Python interfaces around
common pentesting CLIs on Kali Linux (Parrot still compatible).
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

from pathlib import Path
from james.layers.native import NativeLayer

_SYS_NET = Path("/sys/class/net")
# ARPHRD_IEEE80211_RADIOTAP — monitor-mode interfaces
_ARPHRD_RADIOTAP = 803


def _wireless_entries() -> list[dict]:
    """Wireless interfaces that exist on this host. Never invents a name."""
    if not _SYS_NET.is_dir():
        return []
    found: list[dict] = []
    for entry in sorted(_SYS_NET.iterdir(), key=lambda path: path.name):
        if entry.name == "lo" or not entry.is_dir():
            continue
        if not (entry / "wireless").exists() and not (entry / "phy80211").exists():
            continue
        mode = "managed"
        try:
            if int((entry / "type").read_text().strip()) == _ARPHRD_RADIOTAP:
                mode = "monitor"
        except (OSError, ValueError):
            mode = "managed"
        found.append({"interface": entry.name, "iface": entry.name, "mode": mode})
    return found


class AircrackSuite:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def list_interfaces(self) -> list[dict]:
        return _wireless_entries()

class Hashcat:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Hcxtools:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class WPA3Tools:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Nmap:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def os_detect(self, target: str) -> dict:
        return {"error": "OS detection wrapper is not available."}

class John:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class TheHarvester:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Wafw00f:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Ettercap:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Masscan:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Reaver:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Responder:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class Sslscan:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

class IoTTools:
    def __init__(self, layer: NativeLayer):
        self.layer = layer
