# JAMES Linux

**Autonomous AI Pentesting Agent** for Parrot OS / Kali Linux.

Native PyQt5 desktop application + FastAPI remote server that wraps industry-standard
security tools (`nmap`, `aircrack-ng`, `hashcat`, `john`) behind a conversational AI agent
with a dark-themed GUI and a responsive web dashboard for remote control from any device.

## Quick Start

```bash
# Clone
git clone https://github.com/Intrusive-Thots/james-linux.git
cd james-linux

# Install deps (most are pre-installed on Parrot OS)
pip install -r requirements.txt

# Launch desktop GUI
python3 main.py

# Launch remote server (accessible from Android / Windows / any browser)
python3 main.py --setup     # first-time: set API key + generate TLS certs
python3 main.py --server    # start headless API server

# Launch both GUI + server
python3 main.py --both
```

## Remote Access (Android / Windows / Any Device)

JAMES includes a built-in web dashboard that works on any device with a browser:

1. Run `python3 main.py --setup` to set an API key and generate TLS certs
2. Run `python3 main.py --server` to start the server
3. Open `https://<your-parrot-ip>:8443` on your phone or Windows PC
4. Log in with your API key
5. Control JAMES remotely — run scans, crack hashes, chat with the agent

The web dashboard can be installed as a **PWA** (Add to Home Screen) on Android/Windows
for a native app experience.

## Architecture

```
┌─────────────────────────────────────────────┐
│            Parrot OS Machine                │
│                                             │
│  ┌─────────┐    ┌──────────────────────┐    │
│  │ PyQt5   │    │  FastAPI + WebSocket │    │
│  │ Desktop │───▶│  Server (:8443)      │◀───┼──── Android / Windows / Browser
│  │ GUI     │    └──────────────────────┘    │
│  └─────────┘              │                 │
│        │                  │                 │
│        ▼                  ▼                 │
│  ┌─────────────────────────────────┐        │
│  │  Orchestrator + Agent Brain     │        │
│  │  ┌──────┐ ┌─────────┐ ┌──────┐ │        │
│  │  │ nmap │ │aircrack │ │ john │ │        │
│  │  └──────┘ └─────────┘ └──────┘ │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

## Project Structure

```
james-linux/
├── main.py                    # CLI entry point (--server, --both, --setup)
├── requirements.txt
├── james/
│   ├── core/
│   │   ├── agent.py           # AI agent brain (NLP intent matching)
│   │   └── orchestrator.py    # Central coordinator & task log
│   ├── gui/
│   │   ├── main_window.py     # PyQt5 tabbed dashboard (6 tabs)
│   │   ├── chat_panel.py      # Agent chat interface
│   │   └── theme.py           # Dark cyber-aesthetic stylesheet
│   ├── layers/
│   │   └── native.py          # Subprocess execution (sudo, streaming, bg)
│   ├── tools/
│   │   └── parrot.py          # Nmap, AircrackSuite, Hashcat, John wrappers
│   ├── skills/
│   │   ├── wifi_audit.json    # Wi-Fi audit workflow
│   │   └── full_recon.json    # Network recon workflow
│   ├── server/
│   │   ├── app.py             # FastAPI application factory
│   │   ├── auth.py            # JWT auth + bcrypt key hashing
│   │   ├── routes.py          # REST API endpoints
│   │   ├── websocket.py       # Real-time streaming
│   │   ├── config.py          # Server configuration
│   │   ├── tls.py             # Self-signed cert generation
│   │   └── service.py         # Systemd service installer
│   └── web/
│       ├── index.html         # SPA dashboard (PWA-capable)
│       ├── style.css          # Dark cyber theme
│       ├── app.js             # Client logic + WebSocket
│       ├── manifest.json      # PWA manifest
│       └── sw.js              # Service worker
```

## CLI Modes

| Command | Description |
|---------|-------------|
| `python3 main.py` | Desktop GUI only |
| `python3 main.py --server` | API server only (headless) |
| `python3 main.py --both` | GUI + API server |
| `python3 main.py --setup` | Interactive setup wizard |
| `python3 main.py --install-service` | Install as systemd service |
| `python3 main.py --remove-service` | Remove systemd service |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/agent/chat` | Chat with AI agent |
| GET | `/api/system/status` | Tool availability |
| POST | `/api/recon/quick` | Quick nmap scan |
| POST | `/api/recon/full` | Full nmap scan |
| GET | `/api/wifi/interfaces` | List wireless interfaces |
| POST | `/api/wifi/monitor` | Toggle monitor mode |
| POST | `/api/wifi/deauth` | Send deauth frames |
| POST | `/api/crack/wpa` | Crack WPA handshake |
| POST | `/api/crack/hash` | Crack hash file |
| GET | `/api/log` | Task log |
| WS | `/ws` | Real-time WebSocket |

## Requirements

- **OS:** Parrot Security 6.x or Kali Linux
- **Python:** 3.10+
- **System tools:** nmap, aircrack-ng suite, hashcat, john

## Security

⚠️ This tool exposes pentesting capabilities over the network. Always:
- Set a strong API key via `python3 main.py --setup`
- Use TLS (enabled by default with self-signed certs)
- Only run on trusted networks or behind a VPN
