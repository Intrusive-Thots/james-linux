# 🖥️ GUI, API Server & PWA Remote — JAMES Linux

This document details the user interface structures, FastAPI uvicorn APIs, remote HTTP services, and WebSocket messaging formats in JAMES, implemented across [gui/](file:///home/malcolm/Desktop/james-linux/james/gui), [remote/](file:///home/malcolm/Desktop/james-linux/james/remote), [api/](file:///home/malcolm/Desktop/james-linux/james/api), and [web/](file:///home/malcolm/Desktop/james-linux/james/web).

---

## 🖥️ PyQt5 Desktop Application (`james/gui/`)

The desktop client is a PyQt5 GUI configured in dark mode styling (`theme.py`). It consists of:
*   **MainWindow (`main_window.py`)**: Coordinates the primary view. It initializes the panels and sets up layout containers.
*   **The Dashboard Tabs (`gui/tabs/`)**:
    *   `wifi_tab.py`: Displays scanned AP nodes, signal gauges, and lock states. Allows selection and launching of deauth attacks or PMKID captures.
    *   `autopilot_tab.py`: One-click autonomous audit execution tracker.
    *   `airgeddon_tab.py`: Captive portal evil twin selector.
    *   `setup_tab.py` & `setup_wizard.py`: Configuring system environments and credentials.
    *   `troubleshoot_tab.py`: Tool checks and diagnostics.
*   **Chat Panel (`chat_panel.py`)**: A chat window to converse with the agent. Features contextsuggestion chips (e.g. *"Auto-select interface"*, *"Dominate target"*) to simplify common workflows.
*   **Thread Safety (`QThread` & `Worker`)**:
    To prevent long subprocess operations (e.g., waiting 15s for airodump-ng or running Hashcat) from freezing the Qt GUI event loop, all operations are spawned inside `Worker` objects using `QThread` workers. The worker communicates results back to the GUI using thread-safe Qt Signals.

---

## 🌐 FastAPI & WebSocket server (`james/api/`)

For the React-based frontend client, JAMES provides a robust uvicorn-hosted API layer in `james/api/server.py` listening on port `8745`.

### 1. REST Endpoints
*   `GET /api/health`: Health status endpoint.
*   `GET /api/system-check`: Runs the tool diagnostics check.
*   `GET /api/interfaces`: Retrieves host wireless adapters.
*   `GET /api/loot`: Aggregates cached cracked credentials.
*   `GET /api/wordlists`: Indexes local dictionary directories.

### 2. WebSocket Channel (`ws://<ip>:8745/ws`)
This channel manages real-time bidirectional communication:
*   **State Push**: Upon connection, the server pushes an `init` message containing the interface array and loot history.
*   **Log Broadcasts**: Command stdout logs are streamed using a thread-safe `broadcast_sync()` mapping that routes the orchestrator's `on_print` messages down to the WebSocket.
*   **Action Routing**: Client actions (e.g., `scan_aps`, `capture_handshake`, `crack_wpa`, `evil_twin`) are dispatched as concurrent asyncio tasks (`asyncio.create_task`) and run on background worker threads (`asyncio.to_thread`).
*   **Command Cancellation**: Operators can send `abort_attack`, which triggers a shared `_abort_flag` event, killing the running processes immediately.

---

## 📱 HTTP Remote Server (`james/remote/`)

For lightweight remote management from any browser or mobile phone, JAMES runs a second server inside `james/remote/server.py` on port `1337`.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HTTP Remote Server (:1337)                      │
├────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐                   ┌─────────────────────┐  │
│  │   Token-Based Auth     │                   │     Web UI HTML     │  │
│  │ (urlsafe secrets token)│                   │  (WEB_UI_TEMPLATE)  │  │
│  └────────────────────────┘                   └─────────────────────┘  │
│                                                          │             │
│  ┌────────────────────────┐                   ┌──────────▼──────────┐  │
│  │    REST Command API    │ <──────────────── │   JavaScript AJAX   │  │
│  │      (/api/cmd)        │                   │     Fetch API       │  │
│  └────────────────────────┘                   └─────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Token-Based Authentication
*   On server startup, `RemoteServer` generates a secure URL-safe secret token (`secrets.token_urlsafe(32)`).
*   All `/api/*` endpoints validate requests by checking the `Authorization: Bearer <token>` header.
*   To make client access seamless, the token is dynamically injected into the index HTML file template upon load, enabling pre-authenticated browser requests.

### 2. Web UI Client (`WEB_UI_TEMPLATE`)
*   Serves a high-contrast dark cybersecurity client UI containing a command palette sidebar, conversational chat box, context ticker, and logs terminal.
*   Allows operators to run commands from their phones by sending POST commands to `/api/cmd` and displaying output logs in the terminal console panel.
