"""
Constants for Parrot tools.
"""
import re

# BSSID Regex for validation
BSSID_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

# Default values
DEFAULT_TIMEOUT_NMAP = 300
DEFAULT_TIMEOUT_QUICK_NMAP = 120
DEFAULT_TIMEOUT_AIRCRACK = 600
DEFAULT_TIMEOUT_HASHCAT = 600
DEFAULT_TIMEOUT_JOHN = 600
DEFAULT_DEAUTH_COUNT = 10
