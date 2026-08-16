"""
Parrot OS Tool Wrappers.

Structured Python interfaces around common pentesting CLIs.
Each wrapper executes via NativeLayer and parses raw output into
dictionaries suitable for the AI orchestrator or the GUI.

This module re-exports classes from modular submodules for backward compatibility.
"""

from james.tools.wifi import AircrackSuite, Hcxtools, WPA3Tools, Reaver
from james.tools.crack import Hashcat, John
from james.tools.scan import Nmap, Masscan
from james.tools.osint import TheHarvester, Wafw00f, Sslscan
from james.tools.network import Ettercap, Responder, IoTTools

__all__ = [
    "AircrackSuite",
    "Hashcat",
    "Hcxtools",
    "WPA3Tools",
    "Nmap",
    "John",
    "TheHarvester",
    "Wafw00f",
    "Ettercap",
    "Masscan",
    "Reaver",
    "Responder",
    "Sslscan",
    "IoTTools",
]
