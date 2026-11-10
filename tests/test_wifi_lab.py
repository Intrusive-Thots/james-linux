import json

import pytest

from james.core import wifi_lab
from james.layers.native import CommandResult
from james.tools.wifi import AircrackSuite

BSSID = "02:11:22:33:44:55"
CLIENT = "02:11:22:33:44:66"
TARGET = ["--interface", "wlan1", "--bssid", BSSID, "--channel", "6"]


def test_active_exercises_require_an_explicit_client():
    with pytest.raises(SystemExit) as error:
        wifi_lab._parse_args(["wpa", *TARGET, "--deauth"])
    assert error.value.code == 2
    args = wifi_lab._parse_args(["wpa", *TARGET, "--deauth", "--client", CLIENT])
    assert args.bssid == BSSID
    assert args.client == CLIENT


@pytest.mark.parametrize("client", ["ff:ff:ff:ff:ff:ff", "01:11:22:33:44:66", BSSID])
def test_active_exercises_reject_broadcast_multicast_and_ap_addresses(client):
    with pytest.raises(SystemExit) as error:
        wifi_lab._parse_args(["hidden", *TARGET, "--client", client, "--deauth"])
    assert error.value.code == 2


def test_airodump_keeps_ssid_and_counts_only_associated_stations():
    content = (
        "BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, "
        "# beacons, # IV, LAN IP, ID-length, ESSID, Key\n"
        f"{BSSID.upper()}, first, last, 6, 54, WPA2, CCMP, PSK, -41, 10, 4, 0.0.0.0, 8, Lab,WiFi, \n"
        "Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs\n"
        f"{CLIENT.upper()}, first, last, -36, 2, {BSSID.upper()}, \n"
        "02:11:22:33:44:77, first, last, -60, 2, (not associated), Lab,WiFi\n"
    )
    data = AircrackSuite.parse_airodump_csv(content)
    assert data["aps"][0] == {
        "bssid": BSSID,
        "channel": 6,
        "privacy": "WPA2",
        "cipher": "CCMP",
        "authentication": "PSK",
        "power": -41,
        "data_packets": 4,
        "essid": "Lab,WiFi",
        "clients": 1,
    }
    assert data["stations"][0]["station_mac"] == CLIENT
    assert data["stations"][1]["bssid"] == ""


@pytest.mark.parametrize(
    ("beacons", "mode"),
    [
        (["2,8"], "transition"),
        (["8"], "sae"),
        (["2"], "psk"),
        (["2", "8"], "unknown"),
        (["1"], "unknown"),
    ],
)
def test_wpa3_transition_requires_both_akms_in_the_same_beacon(beacons, mode):
    assert wifi_lab._wpa3_mode(beacons) == mode


def test_monitor_setup_failure_restores_adapter_and_networkmanager(tmp_path, monkeypatch):
    lab = wifi_lab.WifiLab(wifi_lab._parse_args(["sniff", *TARGET]), tmp_path)
    calls = []

    def run(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("ip", "-j"):
            return CommandResult("ip", 0, json.dumps([{"address": CLIENT, "flags": ["UP"]}]), "")
        if args[:2] == ("nmcli", "-g"):
            return CommandResult("nmcli", 0, "yes\n", "")
        if args[-1] == "monitor":
            raise RuntimeError("driver rejected monitor mode")
        return CommandResult(args[0], 0, "", "")

    monkeypatch.setattr(wifi_lab.shutil, "which", lambda tool: tool)
    monkeypatch.setattr(lab, "_run", run)
    with pytest.raises(RuntimeError, match="driver rejected"), lab._adapter("wlan1", monitor=True):
        pytest.fail("adapter setup failed before capture")
    assert calls[-5:] == [
        ("ip", "link", "set", "dev", "wlan1", "down"),
        ("iw", "dev", "wlan1", "set", "type", "managed"),
        ("ip", "link", "set", "dev", "wlan1", "address", CLIENT),
        ("ip", "link", "set", "dev", "wlan1", "up"),
        ("nmcli", "device", "set", "wlan1", "managed", "yes"),
    ]
    assert not lab.cleanup_errors
