# JAMES Linux

**Autonomous AI Pentesting Agent** for Parrot OS / Kali Linux.

Native PyQt5 desktop application that wraps industry-standard security tools
(`nmap`, `aircrack-ng`, `hashcat`, `john`) behind a dark-themed GUI with an
integrated terminal, task launcher, and structured output parsing.

## Project Structure

```
james-linux/
├── main.py                    # Entry point
├── requirements.txt
├── james/
│   ├── core/
│   │   └── orchestrator.py    # Central coordinator & task log
│   ├── gui/
│   │   ├── main_window.py     # PyQt5 tabbed dashboard
│   │   └── theme.py           # Dark hacker-aesthetic stylesheet
│   ├── layers/
│   │   └── native.py          # Subprocess execution layer (sudo, streaming, bg)
│   ├── tools/
│   │   └── parrot.py          # Nmap, AircrackSuite, Hashcat, John wrappers
│   └── skills/
│       ├── wifi_audit.json    # Wi-Fi audit workflow definition
│       └── full_recon.json    # Network recon workflow definition
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Intrusive-Thots/james-linux.git
cd james-linux

# 2. Install deps (PyQt5 is usually pre-installed on Parrot)
pip install -r requirements.txt

# 3. Launch
python3 main.py
```

## GUI Tabs

| Tab | Purpose |
|-----|---------|
| ⚡ Dashboard | System status, tool availability, manual terminal |
| 🔍 Recon | Quick / full nmap scans with parsed results table |
| 📡 Wi-Fi | Interface management, monitor mode, deauth |
| 🔓 Cracking | WPA handshake + hash cracking (aircrack / hashcat) |
| 📋 Log | Full task history with JSON export |

## Requirements

- **OS:** Parrot Security 6.x or Kali Linux
- **Python:** 3.10+
- **System tools:** nmap, aircrack-ng suite, hashcat, john
