"""
Kali/Debian tool wrappers.

Legacy module name (`parrot.py`). Structured Python interfaces around
common pentesting CLIs on Kali Linux (Parrot still compatible).
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.
"""

from james.layers.native import NativeLayer
from james.tools.wifi import AircrackSuite as AircrackSuite

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
