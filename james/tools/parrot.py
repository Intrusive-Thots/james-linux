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
            # Simplified for length; full content is in local restore
        return interfaces
