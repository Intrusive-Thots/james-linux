"""
JAMES Network Utilities.

Shared helpers for network-related operations used across
the remote server, GUI, and agent modules.
"""

import socket
import logging

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the machine's primary LAN IP address.

    Uses a UDP connect trick (no actual traffic sent) to determine
    which local interface routes to the internet. Falls back to
    localhost on failure.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
