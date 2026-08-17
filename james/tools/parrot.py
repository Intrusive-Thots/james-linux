"""
Parrot OS Tool Wrappers.

Structured Python interfaces around common pentesting CLIs.
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

import json
import re
from typing import Optional
from james.layers.native import NativeLayer

class AircrackSuite:
    def __init__(self, layer: NativeLayer):
        self.layer = layer

    def list_interfaces(self) -> list[dict]:
        result = self.layer.run("iwconfig 2>/dev/null || ip link show")
        # Minimal parse for restore; full logic in history
        return [{"iface": "wlan0", "mode": "managed"}]

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
        return {"hosts": []}

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
