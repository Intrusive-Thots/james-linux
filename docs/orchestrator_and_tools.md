# ⚙️ Orchestrator, Subprocess Layer & Tool Wrappers — JAMES Linux

This document details the low-level automation, process management, safety firewalls, and tool abstraction mechanisms in JAMES, implemented across [orchestrator.py](file:///home/malcolm/Desktop/james-linux/james/core/orchestrator.py), [native.py](file:///home/malcolm/Desktop/james-linux/james/layers/native.py), and [parrot.py](file:///home/malcolm/Desktop/james-linux/james/tools/parrot.py).

---

## 💻 Native Linux Execution Layer (`NativeLayer`)

Subprocess management is handled by `NativeLayer` inside `native.py`. This component manages the execution environment:

### 1. Privilege Escalation (Sudo Management)
*   **Password Storage**: If JAMES is run by a non-root user, `NativeLayer` caches the user's password in-memory (`self._sudo_pass`). This is loaded during configuration setup or from `~/.config/james/settings.json`.
*   **Stdin Piping**: When a command requires root permission (`sudo=True`), the native layer intercepts the call and executes:
    `echo <password> | sudo -S <command>`
    If no password is cached, it attempts `sudo -n <command>` (non-interactive sudo).

### 2. Process Registry & Background Execution
To run tools like `airodump-ng` or packet sniffers in the background without blocking the UI/server, the native layer provides `run_background()`.
*   **Process Grouping**: It uses `start_new_session=True` when spawning processes. This creates a new Unix process group (PGID) for the subprocess.
*   **Safe Cleanup**: When calling `kill_background()`, it kills the entire process group (`os.killpg(pgid, signal.SIGTERM)`) rather than just the parent PID, ensuring that child helper binaries spawned by tools are also terminated.
*   **Reaping Registry**: The layer retains a registry of all background processes (`self._bg_procs`). This is cleared on app termination or during emergency shutdown.

### 3. Real-Time Streaming Output
For long-running scans like `nmap` or `gobuster`, `run()` supports an `on_output` callable parameter. The layer reads stdout line-by-line using a generator and yields it back to the orchestrator to update GUI log windows or stream WebSocket packets to PWAs in real time.

---

## ⚙️ The Orchestrator Hub

`Orchestrator` ties the presentation layer and execution layer together:
*   **Task Log Registry**: Maintains a circular history of up to 500 tasks (`self.task_log`). Each `TaskEntry` stores command parameters, execution start/end timestamps, stdout logs, and status state (`pending`, `running`, `done`, `error`).
*   **GUI & Server Signals**: Provides callback hooks (`on_task_update`, `on_print`, `on_progress`) so the presentation layers can display output dynamically.
*   **Loot Management**: Serializes cracked credentials into `~/.james/loot/results.json`.

---

## 🚦 Prerequisite Auto-Resolution

To make hacking "one-click", the orchestrator features prerequisite checks that run before executing tools:

### 1. Wireless Interface Auto-Selection (`ensure_wireless_interface`)
If no interface is specified in a Wi-Fi command, the orchestrator calls `aircrack.list_interfaces()` and auto-selects the first available wireless card, prioritizing cards already in Monitor mode.

### 2. Monitor Mode Automation (`ensure_monitor_mode`)
Before running sniffing or injection tools, the system checks if the interface is in Monitor mode:
*   If in Managed mode, it runs `airmon-ng start <iface>`.
*   It monitors `stdout` to detect if the interface was renamed (e.g. `wlan0` -> `wlan0mon`) and automatically updates the session context parameters with the new monitor name.

### 3. Smart Wordlist Selection (`find_wordlist` / `ensure_wordlist`)
If a dictionary crack is executed, the orchestrator scans and scores available wordlists in order:
1.  SSID-specific targeted wordlists (generated under `wordlists/`).
2.  Large standard dictionary locations (e.g. `/usr/share/wordlists/rockyou.txt`).
3.  Project default lists (e.g. `worst-500.txt`).

---

## 🛡️ Network Self-Protection (`NetworkGuard`)

The `NetworkGuard` module protects the operator from accidentally severing their own SSH or VNC connection:
*   **Connection Sniffing**: It queries active connections using `nmcli` or `ip route`. It resolves the active interface, gateway IP, associated SSID, and AP BSSID.
*   **Guard Verification Checks**:
    *   `check_deauth_safe`: Blocks sending deauth frames if the target BSSID matches the host's connected AP.
    *   `check_monitor_safe`: Blocks converting an interface to monitor mode if it is the host's active internet adapter.
    *   `check_check_kill_safe`: Warns if the user runs `airmon-ng check kill` while connected over Wi-Fi.

---

## 📦 Tool Wrappers Structure

Tool wrappers located in `james/tools/` translate Python calls to CLI strings and back. For example, `Nmap` in `parrot.py` takes a target string, converts it to `nmap -sV -T4 -O --script vuln <target>`, runs it via the native layer, and parses the XML output into structured hosts and open ports dictionaries.
Similarly, `PineAP` inside `pineap.py` wraps the rogue access point setup (configuring `hostapd` and `dnsmasq` files) and starts the credential harvester.
