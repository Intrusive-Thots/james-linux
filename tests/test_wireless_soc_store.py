import pytest

from james.api.wireless_soc import WirelessSOCStore, validate_observation


def test_rejects_invalid_bssid():
    with pytest.raises(ValueError, match="bssid"):
        validate_observation({"bssid": "not-a-mac", "ssid": "lab", "security": "wpa2"})


def test_ingest_flags_unknown_and_open_ap(tmp_path):
    store = WirelessSOCStore(tmp_path / "soc.sqlite3")
    result = store.ingest({
        "bssid": "AA:BB:CC:DD:EE:01",
        "ssid": "Unapproved",
        "security": "open",
        "channel": 6,
        "rssi": -55,
        "sensor_id": "lab-sensor-1",
    })
    kinds = {item["kind"] for item in result["detections"]}
    assert {"unknown_bssid", "weak_security"} <= kinds
    assert store.summary()["unreviewed_detections"] == 2


def test_approved_ap_flags_ssid_change(tmp_path):
    store = WirelessSOCStore(tmp_path / "soc.sqlite3")
    store.approve_ap("AA:BB:CC:DD:EE:02", "OfficeWiFi", "wpa2", site="Lab")
    result = store.ingest({
        "bssid": "AA:BB:CC:DD:EE:02",
        "ssid": "OfficeWiFi-Clone",
        "security": "wpa2",
        "sensor_id": "sensor-2",
    })
    assert [x["kind"] for x in result["detections"]] == ["ssid_mismatch"]


def test_review_detection_and_asset_inventory(tmp_path):
    store = WirelessSOCStore(tmp_path / "soc.sqlite3")
    store.ingest({
        "bssid": "AA:BB:CC:DD:EE:03",
        "ssid": "Guest",
        "security": "wpa2",
        "sensor_id": "sensor-3",
    })
    detection_id = store.list_detections()[0]["id"]
    assert store.review_detection(detection_id)
    assert store.list_detections(unreviewed_only=True) == []
    assert store.list_assets()[0]["ssid"] == "Guest"
