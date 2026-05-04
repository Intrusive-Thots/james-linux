"""
JAMES Network Self-Protection Module

Prevents JAMES from severing its own network connectivity during
offensive Wi-Fi operations. This guards against:

1. Deauthing the AP that JAMES is currently connected to
2. Putting JAMES's own connected interface into monitor mode
3. Running `airmon-ng check kill` which kills NetworkManager/wpa_supplicant
4. Evil-twin attacks targeting the AP JAMES is associated with

The module detects the current active connection's BSSID, SSID, interface,
and gateway — then checks incoming attack parameters against them.
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ActiveConnection:
    """Snapshot of the host's current network connection."""
    interface: str = ""
    ssid: str = ""
    bssid: str = ""
    gateway: str = ""
    ip: str = ""
    is_wifi: bool = False


class NetworkGuard:
    """
    Guards against self-inflicted network disconnection.

    Usage:
        guard = NetworkGuard()
        ok, reason = guard.check_deauth_safe("AA:BB:CC:DD:EE:FF")
        if not ok:
            print(f"BLOCKED: {reason}")
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cached_connection: Optional[ActiveConnection] = None
        self._cache_age: float = 0
        self._CACHE_TTL = 15  # seconds — re-check every 15s

    def get_active_connection(self, force_refresh: bool = False) -> ActiveConnection:
        """Detect the current active network connection."""
        import time
        now = time.time()

        if (not force_refresh
                and self._cached_connection
                and (now - self._cache_age) < self._CACHE_TTL):
            return self._cached_connection

        conn = ActiveConnection()

        try:
            # Method 1: nmcli (most reliable on Parrot/Debian)
            conn = self._detect_via_nmcli()
            if not conn.interface:
                # Method 2: ip route + iwconfig fallback
                conn = self._detect_via_ip_route()
        except Exception as e:
            logger.warning("NetworkGuard: detection failed: %s", e)

        self._cached_connection = conn
        self._cache_age = now
        logger.debug("NetworkGuard: active connection: %s", conn)
        return conn

    def _detect_via_nmcli(self) -> ActiveConnection:
        """Use nmcli to detect current Wi-Fi connection."""
        conn = ActiveConnection()
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[2] == "connected":
                    conn.interface = parts[0]
                    conn.is_wifi = parts[1] == "wifi"
                    break

            if conn.interface and conn.is_wifi:
                # Get BSSID and SSID
                wifi_info = subprocess.run(
                    ["nmcli", "-t", "-f", "IN-USE,BSSID,SSID,CHAN",
                     "device", "wifi", "list", "ifname", conn.interface],
                    capture_output=True, text=True, timeout=5
                )
                for line in wifi_info.stdout.splitlines():
                    if line.startswith("*:"):
                        parts = line.split(":")
                        # BSSID is parts[1] through parts[6] (MAC has colons)
                        if len(parts) >= 9:
                            conn.bssid = ":".join(parts[1:7]).strip().upper()
                            conn.ssid = parts[7].strip() if len(parts) > 7 else ""

                # Get gateway
                gw_result = subprocess.run(
                    ["ip", "route", "show", "default", "dev", conn.interface],
                    capture_output=True, text=True, timeout=5
                )
                gw_match = re.search(r"default via (\S+)", gw_result.stdout)
                if gw_match:
                    conn.gateway = gw_match.group(1)

                # Get our IP
                ip_result = subprocess.run(
                    ["ip", "-4", "addr", "show", conn.interface],
                    capture_output=True, text=True, timeout=5
                )
                ip_match = re.search(r"inet (\S+)/", ip_result.stdout)
                if ip_match:
                    conn.ip = ip_match.group(1)

            elif conn.interface and not conn.is_wifi:
                # Wired connection — get gateway
                gw_result = subprocess.run(
                    ["ip", "route", "show", "default", "dev", conn.interface],
                    capture_output=True, text=True, timeout=5
                )
                gw_match = re.search(r"default via (\S+)", gw_result.stdout)
                if gw_match:
                    conn.gateway = gw_match.group(1)

        except FileNotFoundError:
            pass  # nmcli not available, fall through
        return conn

    def _detect_via_ip_route(self) -> ActiveConnection:
        """Fallback: use ip route + iwconfig."""
        conn = ActiveConnection()
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"default via (\S+) dev (\S+)", result.stdout)
            if match:
                conn.gateway = match.group(1)
                conn.interface = match.group(2)

                # Check if it's wireless
                iw_result = subprocess.run(
                    ["iwconfig", conn.interface],
                    capture_output=True, text=True, timeout=5
                )
                if "no wireless extensions" not in iw_result.stderr:
                    conn.is_wifi = True
                    # Extract BSSID
                    bssid_match = re.search(
                        r"Access Point:\s*([0-9A-Fa-f:]{17})",
                        iw_result.stdout
                    )
                    if bssid_match:
                        conn.bssid = bssid_match.group(1).upper()
                    # Extract ESSID
                    ssid_match = re.search(r'ESSID:"(.+?)"', iw_result.stdout)
                    if ssid_match:
                        conn.ssid = ssid_match.group(1)
        except FileNotFoundError:
            pass
        return conn

    # ── Guard checks ──────────────────────────────────────────────

    def check_deauth_safe(self, target_bssid: str) -> tuple[bool, str]:
        """
        Check if deauthing target_bssid is safe (won't kill our own connection).

        Returns (is_safe, reason_if_blocked).
        """
        if not self.enabled:
            return True, ""

        conn = self.get_active_connection()
        if not conn.bssid:
            # Can't determine — allow but warn
            return True, ""

        target_upper = target_bssid.strip().upper()
        if target_upper == conn.bssid:
            reason = (
                f"🛡️ BLOCKED: Target BSSID {target_bssid} is the AP JAMES is "
                f"currently connected to ({conn.ssid or 'unknown SSID'} on {conn.interface}). "
                f"Deauthing would sever your own network connection."
            )
            return False, reason

        return True, ""

    def check_monitor_safe(self, interface: str) -> tuple[bool, str]:
        """
        Check if putting an interface into monitor mode is safe.

        Returns (is_safe, reason_if_blocked).
        """
        if not self.enabled:
            return True, ""

        conn = self.get_active_connection()
        if not conn.interface:
            return True, ""

        # Check if this is the same interface we're connected through
        if interface == conn.interface:
            reason = (
                f"🛡️ BLOCKED: Interface {interface} is currently providing "
                f"your network connection ({conn.ssid or 'wired'}, IP: {conn.ip or 'unknown'}). "
                f"Enabling monitor mode would kill your connectivity. "
                f"Use a separate wireless adapter for attacks."
            )
            return False, reason

        return True, ""

    def check_evil_twin_safe(self, target_bssid: str) -> tuple[bool, str]:
        """Check if evil-twin attack is safe (not targeting our own AP)."""
        return self.check_deauth_safe(target_bssid)

    def check_check_kill_safe(self) -> tuple[bool, str]:
        """
        Check if `airmon-ng check kill` is safe.

        It kills NetworkManager and wpa_supplicant. This is only safe
        if we're connected via ethernet or have no active connection.
        """
        if not self.enabled:
            return True, ""

        conn = self.get_active_connection()
        if conn.is_wifi and conn.interface:
            reason = (
                f"🛡️ WARNING: `airmon-ng check kill` will terminate NetworkManager "
                f"and wpa_supplicant, severing your Wi-Fi connection to "
                f"{conn.ssid or 'unknown'} ({conn.bssid or 'unknown BSSID'}) on {conn.interface}. "
                f"Consider connecting via ethernet first, or use a separate adapter."
            )
            # This is a warning, not a hard block — user may intend this
            return True, reason

        return True, ""

    def check_mitm_safe(self, target_ip: str, gateway_ip: str = "") -> tuple[bool, str]:
        """Check if MITM/ARP spoofing is safe (not poisoning our own gateway)."""
        if not self.enabled:
            return True, ""

        conn = self.get_active_connection()
        if conn.gateway and gateway_ip == conn.gateway:
            # ARP spoofing our own gateway — warn but allow (it's often intentional)
            return True, (
                f"⚠️ NOTE: Gateway {gateway_ip} is YOUR default gateway. "
                f"MITM will route through you — ensure IP forwarding is enabled."
            )

        if conn.ip and target_ip == conn.ip:
            return False, (
                f"🛡️ BLOCKED: Target {target_ip} is JAMES's own IP address."
            )

        return True, ""

    def get_status(self) -> dict:
        """Return current protection status for the GUI."""
        conn = self.get_active_connection(force_refresh=True)
        return {
            "enabled": self.enabled,
            "connected": bool(conn.interface),
            "interface": conn.interface,
            "is_wifi": conn.is_wifi,
            "ssid": conn.ssid,
            "bssid": conn.bssid,
            "gateway": conn.gateway,
            "ip": conn.ip,
        }
