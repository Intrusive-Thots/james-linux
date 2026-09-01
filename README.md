# 🔥 JAMES Linux

> *The AI that f**ks networks so you don't have to.*

**Autonomous Pentesting Agent** — Because clicking buttons is for people with free time and zero ambition.

![Kali Linux](https://img.shields.io/badge/Kali%20Linux-ready-557c94?style=for-the-badge&logo=kalilinux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-00f0ff?style=for-the-badge&logo=python&logoColor=white)
![Tools](https://img.shields.io/badge/Tools-30%2B-ff6b35?style=for-the-badge)
![License](https://img.shields.io/badge/License-FAFO-ff4757?style=for-the-badge)

---

## 🤔 What the hell is this?

JAMES is an **autonomous AI pentesting agent** that wraps **30+ security tools** behind one brain, one GUI, and zero patience for manual labor. Point it at a target, whisper sweet nothings like *"wifi blitz wlan0"*, and watch it rip through PMKID captures, WPA handshakes, WPS Pixie Dust, brute-force attacks, and SQL injections like your ex going through your DMs.

Built for **Kali Linux**. Parrot OS still works. Native **PyQt5 desktop app** + **FastAPI remote server** so you can hack from your couch, your phone, or the toilet — we don't judge.

<br>

### Why JAMES?

| | Feature | What It Means |
|---|---------|---------------|
| 🧠 | **AI Brain** | Understands plain English. *"Scan that shit"* actually works. |
| 🔥 | **One-Click Hacks** | Five autonomous attack chains. Click once, ruin someone's day. |
| 🔑 | **Persistent Loot** | Cracked keys survive reboots. Your trophies are safe, you animal. |
| 📡 | **Live AP Scanner** | See every network around you. Double-click to target. That easy. |
| 🎯 | **30+ Tools** | nmap, aircrack-ng, hashcat, hydra, sqlmap, responder, ettercap, reaver... |
| 📱 | **Remote Control** | Hack from your Android. PWA support. Install it like a real app. |
| 🛡️ | **Phantom SOC** | Professional 802.11 workflow console: Recon → Triage → Capture → Analysis → Report. |

---

## 🛡️ Phantom orchestrator (`phantom-soc`)

Phantom is now the **default web workspace**. It is a signed-engagement SOC console:

1. **Authorize** — ECDSA P-256 Proof of Authorization / Rules of Engagement
2. **Recon** — live JAMES radios when the API is up; otherwise the in-browser Hopper SDR lab
3. **Triage → Capture → Analysis → Report** — one primary action per stage

Agent / Auto / Settings remain under **Utilities → JAMES → Agent console** (or the PHANTOM / AGENT workspace tabs).

```bash
cd web
npm install
npm run dev
```

With `python3 main.py --server` on Kali, Phantom sends `scan_aps`, `capture_pmkid`, and `capture_handshake` over the existing WebSocket. Offline, the SDR lab still runs the full dictionary-verify path (including planted lab PSKs).

See `docs/PHANTOM.md` for the workflow and lab notes.

---

---

## 🚀 Quick Start

> Stop reading. Start hacking.

```bash
# Clone this beautiful disaster
git clone https://github.com/Intrusive-Thots/james-linux.git
cd james-linux

# Install deps (Kali already has most of this shit)
pip install -r requirements.txt

# Launch the beast
python3 main.py
```

**Want remote access from your phone?**

```bash
python3 main.py --setup     # Set API key + TLS certs (first time only)
python3 main.py --server    # Headless server mode
python3 main.py --both      # GUI + server — for the greedy
```

Then open `http://<your-ip>:8745` (or the port in `JAMES_API_PORT`) on literally any device. Done.

---

## 🔥 One-Click Hacks

> For when you're too busy (lazy) to chain tools together like some kind of cave person.

| Command | What It Does | Vibe |
|:--------|:-------------|:----:|
| `wifi blitz wlan0` | PMKID → Handshake → WPS Pixie Dust. All vectors. No mercy. | 💀 |
| `network dominate 192.168.1.0/24` | Scan → Fingerprint → Brute-force → Vuln scan | 🔨 |
| `web pwn http://target.com` | WAF detect → DirBust → SQLi → SSL audit → Nikto | 🌐 |
| `stealth recon target.com` | OSINT → DNS → WHOIS → Passive scan. Ghost mode. | 👻 |
| `evil twin wlan0` | Clone an AP, serve a fake portal, harvest creds. *Chef's kiss.* | 😈 |

Just type it in the chat. JAMES handles the rest while you sit there looking pretty.

---

## 💬 Talk to It Like a Human

JAMES isn't some braindead CLI wrapper. It understands context, remembers your targets, and suggests next moves like a degenerate co-pilot.

```
You:    scan 192.168.1.0/24
JAMES:  🔍 Found 12 hosts, 47 open ports...
        💡 Suggested: full scan, network dominate, osint

You:    wifi blitz
JAMES:  🔥 Wi-Fi Blitz launched on wlan0
        Phase 1: PMKID capture...
        Phase 2: Handshake harvest...
        Phase 3: WPS Pixie Dust...

You:    show loot
JAMES:  🔑 Cracked Keys (3):
        • HomeNetwork: password123 [aircrack]
        • CoffeeShop_5G: ilovecoffee [hashcat]
        • Neighbor_FBI_Van: hunter2 [reaver]
```

Yeah, it remembers everything. **Persistent loot cache.** Your cracked keys survive reboots because JAMES respects the grind.

---

## 📱 Remote Access

> Control JAMES from your phone while pretending to check Instagram.

1. `python3 main.py --setup` → set an API key
2. `python3 main.py --server` → fire up the server
3. Open `http://<kali-ip>:8745` on your phone (override with `JAMES_API_PORT`)
4. Install as **PWA** (Add to Home Screen) for that *premium hacker aesthetic*
5. Profit. Or prison. Depends on your choices.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│              Kali Linux Machine                   │
│                                                  │
│  ┌──────────┐    ┌──────────────────────┐       │
│  │  PyQt5   │    │ FastAPI + WebSocket   │       │
│  │  Desktop │───>│ Server (:8745)        │<──────┼── Phone / PC / Browser
│  │  GUI     │    └───────────────────────┘       │
│  └──────────┘              |                     │
│        |                   |                     │
│        v                   v                     │
│  ┌──────────────────────────────────────┐        │
│  │     Orchestrator + Agent Brain       │        │
│  │                                      │        │
│  │  nmap  aircrack  hashcat  hydra      │        │
│  │  nikto  reaver  responder  ettercap  │        │
│  │  sqlmap  gobuster  masscan  john     │        │
│  │           + 20 more tools            │        │
│  └──────────────────────────────────────┘        │
│                    |                             │
│                    v                             │
│  ┌──────────────────────────────────────┐        │
│  │  Persistent Loot Cache               │        │
│  │  ~/.james/loot/results.json          │        │
│  └──────────────────────────────────────┘        │
└──────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
james-linux/
├── main.py                       # Entry point — pick your poison
├── requirements.txt
├── requirements-dev.txt
│
├── james/
│   ├── core/
│   │   ├── agent/                # Agent package (intents, models, Agent class)
│   │   ├── orchestrator/         # Orchestrator package
│   │   ├── ai_engine.py
│   │   ├── auto_agent.py
│   │   ├── net_guard.py
│   │   ├── primers.py
│   │   ├── report.py
│   │   └── sedge.py
│   │
│   ├── gui/                      # PyQt5 desktop UI
│   │   ├── main_window.py
│   │   ├── chat_panel.py
│   │   ├── setup_wizard.py
│   │   ├── theme.py
│   │   └── tabs/
│   │
│   ├── layers/
│   │   └── native.py             # Subprocess execution
│   │
│   ├── tools/
│   │   ├── parrot.py             # Tool wrappers (legacy name; Kali/Debian CLIs)
│   │   └── pineap.py
│   │
│   ├── skills/                   # JSON workflow definitions
│   ├── api/
│   │   └── server.py             # FastAPI + WebSocket server
│   ├── remote/
│   ├── web/                      # Legacy SPA (primary client is web/ React)
│   └── wordlists/
│
├── web/                          # Primary React UI (Phantom SOC + tactical Agent)
│   └── src/phantom/              # Phantom orchestrator (PoA, RF lab, workflows)
├── docs/
├── tests/
└── wordlists/
```

Primary remote web client: `web/` (React). Legacy: `james/web/`.

---

## ⌨️ CLI Modes

| Command | What It Does |
|:--------|:-------------|
| `python3 main.py` | Desktop GUI — the full experience |
| `python3 main.py --server` | Headless API server — for real ones |
| `python3 main.py --both` | GUI + server — you greedy bastard |
| `python3 main.py --setup` | First-time setup wizard |
| `python3 main.py --install-service` | Systemd daemon. It never sleeps. |

Default API port: **8745** (override with `JAMES_API_PORT`).

---

## 📖 Full Command Reference

<details>
<summary><b>🔍 Recon & Scanning</b></summary>

| Command | Description |
|:--------|:------------|
| `scan <target>` | Quick nmap scan |
| `full scan <target>` | Deep service + script scan |
| `masscan <target>` | Ultra-fast 65535-port scan |
| `os detect <target>` | OS fingerprinting (needs root) |
| `scan aps [iface]` | List nearby Wi-Fi networks |

</details>

<details>
<summary><b>📡 Wi-Fi</b></summary>

| Command | Description |
|:--------|:------------|
| `list interfaces` | Show wireless adapters |
| `enable monitor [iface]` | Start monitor mode |
| `disable monitor [iface]` | Stop monitor mode |
| `deauth <BSSID> [count]` | Send deauth frames |
| `autopwn [iface]` | Full autonomous Wi-Fi crack |

</details>

<details>
<summary><b>🌐 Web & OSINT</b></summary>

| Command | Description |
|:--------|:------------|
| `osint <domain>` | Harvest emails, subdomains, IPs |
| `whois <domain>` | Domain registration lookup |
| `dns enum <domain>` | DNS record enumeration |
| `waf detect <url>` | Detect web application firewall |
| `ssl scan <target>` | SSL/TLS security audit |
| `nikto <url>` | Web vulnerability scan |
| `gobuster <url>` | Directory brute-force |
| `sqlmap <url>` | SQL injection testing |

</details>

<details>
<summary><b>🕸️ Network Attacks</b></summary>

| Command | Description |
|:--------|:------------|
| `mitm <victim> [gateway]` | ARP poisoning MITM |
| `responder [iface]` | LLMNR/NBT-NS hash capture |
| `sniff [iface]` | Packet capture & analysis |
| `brute <target> [proto]` | Hydra brute-force |

</details>

<details>
<summary><b>🔓 Cracking & Exploit</b></summary>

| Command | Description |
|:--------|:------------|
| `crack wpa <file>` | Crack WPA handshake |
| `crack hash <file>` | Crack hash file (hashcat) |
| `show loot` | Display all cracked keys |
| `reverse shell [port]` | Generate payloads + listener |
| `msf <search>` | Metasploit search/exploit |

</details>

<details>
<summary><b>⚙️ System</b></summary>

| Command | Description |
|:--------|:------------|
| `status` | Check all tools |
| `list skills` | Show skill workflows |
| `run skill <name>` | Execute a skill |
| `report` | Generate session report |
| `history` | Show task log |
| `set <key> <value>` | Set context variable |
| `! <command>` | Raw shell passthrough |

</details>

---

## 📋 Requirements

| | Requirement | Details |
|---|:-----------|:--------|
| 💻 | **OS** | Kali Linux (primary). Parrot Security still compatible. |
| 🐍 | **Python** | 3.10+ |
| 🔧 | **Tools** | nmap, aircrack-ng, hashcat, john, hydra, sqlmap, nikto, reaver, hcxdumptool, responder, ettercap... |
| 🧠 | **Attitude** | Questionable at best |

---

## ⚠️ Legal Disclaimer

> **Don't be a dumbass.** This tool is for **authorized security testing only.** Using it against networks you don't own or have explicit written permission to test is illegal and will absolutely get your ass thrown in jail.
>
> We are not your lawyers. We are not responsible for your life choices. Get written authorization before touching anything.
>
> This is an educational tool made by security professionals for security professionals. If you use it to be a dick, that's on you.
>
> *"With great power comes great responsibility"* — Uncle Ben, right before he got f**king shot.

---

## 👥 Credits

Built with sleep deprivation, energy drinks, and an unhealthy obsession with dark mode.

**Intrusive Thots** — *Thinking what you're thinking, but actually doing it.*

<br>

```
     ╔═  ═════ ╔═══   ═══╔══════╔═══════
     ║║╔════╚╔═══ ══║║════║║
     ║║║║║║║║╔════║║╔═════║║
╔═   ║║╔════║║══╔═╝ ══║║════  ╚═════║║
╚═════╝╚══  ══║║══ ╔═╝ ══║║╔═══════║║╔═══════║
 ╚═════╝ ╚══  ══╝╚══     ╚═╝╚═══════╝╚═══════╝
            v0.4.0 — Autonomous AF
```
