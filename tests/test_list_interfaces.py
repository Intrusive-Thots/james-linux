"""Interface inventory must describe hardware that exists."""
from pathlib import Path
from unittest.mock import MagicMock

from james.tools.parrot import AircrackSuite, Nmap


def test_list_interfaces_does_not_invent_wlan0():
    ifaces = AircrackSuite(MagicMock()).list_interfaces()
    for item in ifaces:
        name = item["interface"]
        assert name == item["iface"]
        assert Path("/sys/class/net", name).exists()
        assert (Path("/sys/class/net", name, "wireless").exists()
                or Path("/sys/class/net", name, "phy80211").exists())
        assert item["mode"] in {"managed", "monitor"}
    if not Path("/sys/class/net/wlan0").exists():
        assert all(item["interface"] != "wlan0" for item in ifaces)


def test_os_detect_reports_unavailable_instead_of_an_empty_scan():
    result = Nmap(MagicMock()).os_detect("127.0.0.1")
    assert "error" in result
    assert "hosts" not in result
