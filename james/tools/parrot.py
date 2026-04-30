import re
from typing import Dict, Any, List, Optional
from james.layers.native import NativeLayer

class AircrackSuite:
    """Wrapper for the aircrack-ng suite tools commonly used on Parrot OS."""

    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def start_monitor_mode(self, interface: str) -> Dict[str, Any]:
        """Starts monitor mode on the specified interface using airmon-ng."""
        # Using sudo because airmon-ng requires root
        code, out, err = self.layer.execute(["airmon-ng", "start", interface], require_root=True)

        # Simple parsing logic
        success = code == 0
        new_interface = interface
        if "mac80211 monitor mode vif enabled for" in out:
             # Basic parse attempt to find the new interface name (e.g., wlan0mon)
             match = re.search(r"enabled for \[phy\d+\](\w+)", out)
             if match:
                 new_interface = match.group(1)
             elif f"{interface}mon" in out:
                 new_interface = f"{interface}mon"

        return {
            "success": success,
            "original_interface": interface,
            "monitor_interface": new_interface,
            "output": out,
            "error": err
        }

    def stop_monitor_mode(self, interface: str) -> Dict[str, Any]:
        """Stops monitor mode on the specified interface."""
        code, out, err = self.layer.execute(["airmon-ng", "stop", interface], require_root=True)
        return {
            "success": code == 0,
            "interface": interface,
            "output": out,
            "error": err
        }

    def scan_networks(self, interface: str, duration: int = 10) -> Dict[str, Any]:
        """Scans networks using airodump-ng for a limited duration and parses result."""
        # airodump-ng runs continuously. We need a specific timeout or write to CSV
        # For simplicity in this wrapper, we run it with timeout and parse stdout loosely
        # To avoid orphaned root processes when using sudo + timeout in python,
        # we can pass the system `timeout` utility directly.
        code, out, err = self.layer.execute(["timeout", str(duration), "airodump-ng", interface], require_root=True)

        # Note: Return code might be negative or non-zero due to timeout killing it
        # We parse the output to extract BSSID, PWR, CH, ESSID
        networks = []
        for line in out.splitlines() + err.splitlines():
            # A very simplistic regex for matching BSSID and ESSID from airodump-ng output
            # Real implementation might parse the CSV output instead
            bssid_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", line)
            if bssid_match:
                networks.append(line.strip())

        return {
            "interface": interface,
            "networks_found_raw": networks,
            "raw_output": out + err
        }
