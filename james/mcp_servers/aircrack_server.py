from typing import Dict, Any, Optional
from .base_server import MCPToolClient
from james.layers.native import NativeLayer
import re

class AircrackServer(MCPToolClient):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AircrackServer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, layer: NativeLayer = None):
        if not getattr(self, '_initialized', False):
            super().__init__("Aircrack MCP Server")
            self.layer = layer if layer else NativeLayer()
            self._initialized = True

            self.register_tool(
                "airodump_scan",
                "Scan for surrounding Wi-Fi APs on a given interface. Arguments: interface (str).",
                self.airodump_scan
            )
            self.register_tool(
                "airodump_capture",
                "Capture WPA handshake on a given BSSID and channel. Arguments: interface (str), bssid (str), channel (int), timeout_seconds (int).",
                self.airodump_capture
            )
            self.register_tool(
                "aireplay_deauth",
                "Send deauth packets to a given BSSID on an interface. Arguments: interface (str), bssid (str), count (int).",
                self.aireplay_deauth
            )

    def airodump_scan(self, interface: str) -> Dict[str, Any]:
        result = self.layer.run(f"airodump-ng {interface} --output-format csv -w /tmp/scan & sleep 5; kill $!", timeout=10)

        # Simplified parsing of the CSV output
        try:
            with open("/tmp/scan-01.csv", "r") as f:
                content = f.read()
            # Extract basic AP info (BSSID, channel, ESSID) using regex for demo
            aps = []
            for match in re.finditer(r'([0-9A-F:]+),\s+\d{4}-\d{2}-\d{2}.*?,\s+(\d+),\s+\d+,\s+\d+,\s+.*?,\s+\d+,\s+\d+,\s+.*?,\s+.*?,\s+.*?,\s+.*?,\s+.*?,\s+(.*?)$', content, re.MULTILINE):
                aps.append({
                    "bssid": match.group(1),
                    "channel": int(match.group(2)),
                    "essid": match.group(3).strip()
                })
            return {"status": "success", "aps": aps}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def airodump_capture(self, interface: str, bssid: str, channel: int, timeout_seconds: int = 15) -> Dict[str, Any]:
        output_prefix = f"/tmp/capture_{bssid.replace(':', '')}"
        # Start capture
        cmd = f"airodump-ng -c {channel} --bssid {bssid} -w {output_prefix} {interface} & sleep {timeout_seconds}; kill $!"
        self.layer.run(cmd, timeout=timeout_seconds + 5)

        cap_file = f"{output_prefix}-01.cap"
        return {"status": "success", "capture_file": cap_file}

    def aireplay_deauth(self, interface: str, bssid: str, count: int = 10) -> Dict[str, Any]:
        cmd = f"aireplay-ng --deauth {count} -a {bssid} {interface}"
        result = self.layer.run(cmd, timeout=30)
        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        return {"status": "error", "output": result.stderr}
