"""Dependency checks and system package setup shared by Wi-Fi Lab entry points."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path

RADIO_PACKAGES = {
    "ip": "iproute2",
    "iw": "iw",
    "timeout": "coreutils",
    "airodump-ng": "aircrack-ng",
    "aireplay-ng": "aircrack-ng",
    "aircrack-ng": "aircrack-ng",
    "tshark": "tshark",
    "hostapd": "hostapd",
    "tcpdump": "tcpdump",
}
_APT = Path("/usr/bin/apt-get")
_SYSTEM_PATH = "/usr/local/sbin:/usr/sbin:/sbin:/usr/local/bin:/usr/bin:/bin"


def find_tool(command: str) -> str | None:
    return shutil.which(command) or shutil.which(command, path=_SYSTEM_PATH)


def missing_radio_packages() -> list[str]:
    return sorted({package for tool, package in RADIO_PACKAGES.items() if not find_tool(tool)})


def required_radio_tools(args) -> set[str]:
    tools = {"ip", "iw", "timeout", "airodump-ng"}
    if args.exercise in {"wpa", "wpa3", "wep", "twin"}:
        tools.add("aircrack-ng")
    if args.deauth or args.arp_replay or args.inject_test or args.exercise == "wep-replay":
        tools.add("aireplay-ng")
    if args.exercise in {"hidden", "wpa3", "traffic", "twin"} or (
        args.exercise == "wpa" and args.client
    ):
        tools.add("tshark")
    if args.ap_interface:
        tools.add("hostapd")
    if args.exercise == "traffic":
        tools.add("tcpdump")
    return tools


def install_packages(packages: list[str]):
    if not packages:
        return
    if not _APT.is_file():
        raise RuntimeError(
            f"Install these system packages with your package manager: {', '.join(packages)}"
        )
    prefix = []
    if os.geteuid() != 0:
        sudo = find_tool("sudo")
        if not sudo:
            raise RuntimeError("Package installation requires sudo or system administrator access.")
        prefix = [sudo, "--"]
    print(f"Installing required packages: {', '.join(packages)}", flush=True)
    subprocess.run([*prefix, str(_APT), "update"], check=True)
    subprocess.run(
        [
            *prefix,
            "/usr/bin/env",
            "DEBIAN_FRONTEND=noninteractive",
            str(_APT),
            "-y",
            "--no-install-recommends",
            "install",
            *packages,
        ],
        check=True,
    )


def idle_adapter_state(interface: str) -> str:
    """Describe a managed adapter using current Linux link state."""
    device = Path("/sys/class/net") / interface
    if (device / "master").exists():
        return "in use"
    try:
        carrier = (device / "carrier").read_text().strip()
    except OSError:
        try:
            return "idle" if (device / "operstate").read_text().strip() == "down" else "unknown"
        except OSError:
            return "unknown"
    return {"0": "idle", "1": "connected"}.get(carrier, "unknown")


def parse_ap_list(output: str) -> list[tuple[str, str, int, int, str]]:
    """Parse escaped nmcli output into unique 2.4 GHz access points."""
    from james.tools.wifi import radio_address

    access_points = {}
    for row in csv.reader(
        output.splitlines(), delimiter=":", escapechar="\\", quoting=csv.QUOTE_NONE
    ):
        if len(row) != 6:
            continue
        bssid, ssid, channel_text, frequency_text, signal_text, security = row
        try:
            address = radio_address(bssid)
            channel = int(channel_text)
            frequency = int(frequency_text.split()[0])
            signal = int(signal_text)
        except (ValueError, IndexError):
            continue
        if not (1 <= channel <= 14 and 2400 <= frequency < 2500):
            continue
        entry = (address, ssid, channel, signal, security)
        if address not in access_points or signal > access_points[address][3]:
            access_points[address] = entry
    return sorted(access_points.values(), key=lambda entry: (-entry[3], entry[0]))


if __name__ == "__main__":
    if os.geteuid() != 0:
        raise SystemExit("The package worker requires system administrator access.")
    try:
        install_packages(missing_radio_packages())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Wi-Fi Lab tool setup failed: {error}") from None
