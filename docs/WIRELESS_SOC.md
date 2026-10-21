# Wireless SOC

The Wireless SOC stores metadata observations received from an authorized sensor. It does not perform radio discovery, packet capture, injection, credential collection, or cracking.

## Data and detection

- SQLite database defaults to `~/.james/wireless_soc.sqlite3`; override with `JAMES_WIRELESS_SOC_DB`.
- Approved access point inventory with expected SSID and minimum security baseline.
- Detection events for unapproved BSSIDs, SSID changes, security downgrades, and open/WEP security.
- Asset inventory, alert review state, and summary counters.
- Input validation for BSSID, SSID byte length, security label, channel, RSSI, and sensor ID.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/wireless-soc/summary` | Live counters |
| GET | `/api/wireless-soc/assets` | Latest observed metadata |
| GET | `/api/wireless-soc/detections` | Detection queue |
| POST | `/api/wireless-soc/observations` | Ingest a real sensor observation |
| POST | `/api/wireless-soc/approved-aps` | Register an approved AP |
| POST | `/api/wireless-soc/detections/{id}/review` | Review an alert |

The API uses the existing `JAMES_API_TOKEN` middleware when configured. The dashboard requests these endpoints directly and shows an empty state or connection error when live data is unavailable. It contains no fallback inventory or generated detections.

## Tests

Run `pytest -q tests/test_wireless_soc_store.py` from the repository root.
