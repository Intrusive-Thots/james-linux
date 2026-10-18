# JAMES Linux

JAMES is a Python desktop application with a FastAPI/WebSocket backend and a React web client.

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Run the API server separately with `python3 main.py --server`. The default API bind is loopback on port 8745. Remote binding requires an API token and TLS configuration.

## Wireless SOC

The standalone [Wireless SOC dashboard](dashboard/wireless_soc.html) reads live observations from the API. It starts empty and reports connection errors rather than displaying fabricated assets or alerts.

Backend endpoints are documented in [docs/WIRELESS_SOC.md](docs/WIRELESS_SOC.md). Configure approved access points and provide metadata observations from an authorized wireless sensor. The application does not generate replacement observations when a sensor or API is unavailable.

## Development and verification

Run the Python tests with `pytest -q`. The React client lives in `web/`; use its package scripts to run the development server and checks.

No test fixture, recorded example, or mock result should be presented as a live observation. Unit tests may use controlled test doubles where necessary, but runtime paths must fail clearly when a real dependency is unavailable.
