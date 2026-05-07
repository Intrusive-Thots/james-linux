"""
Constants and pre-compiled regex patterns for tools.
"""

import re

# Strict validation for interface names to prevent argument injection
INTERFACE_REGEX = re.compile(r"^[a-zA-Z0-9._][a-zA-Z0-9._-]*$")

# Default timeout for subprocess executions in seconds
DEFAULT_TIMEOUT = 60

# Short timeout for quick operations
SHORT_TIMEOUT = 10

# Long timeout for extended scans or brute-forcing
LONG_TIMEOUT = 300
