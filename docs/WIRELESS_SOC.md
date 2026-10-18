# Wireless SOC telemetry store

This component is a defensive, metadata-only foundation for the JAMES Wireless
Security Operations dashboard. It stores observations supplied by an authorized
sensor; it does not perform radio discovery, packet capture, injection, credential
collection, or cracking.

## Storage and behavior

- SQLite database at a path chosen by the host application.
- Explicit approved AP inventory with expected SSID and minimum security baseline.
- Detections for unknown BSSIDs, SSID changes, security downgrades, and open/WEP networks.
- Asset inventory, alert review state, and summary counters.
- Input validation for BSSID, SSID byte length, security label, channel, RSSI, and sensor ID.

## Integration status

The store module is intentionally separate from the existing API and radio-control
paths. Mounting HTTP routes and connecting the dashboard to this store are follow-up
integration work. The current HTML dashboard remains a demo and does not claim to
show live telemetry.

## Tests

Run from the repository root:

```bash
pytest -q tests/test_wireless_soc_store.py
```

Only feed observations from sensors and networks you are authorized to monitor.
