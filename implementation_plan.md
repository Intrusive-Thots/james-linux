# James-Linux: Parrot OS Pentesting Agent

This document outlines the architecture and implementation plan for `james-linux`, a brand new, completely independent native desktop application tailored for Linux (specifically Parrot OS distributions).

> [!WARNING]
> This is a completely new project directory, not a modification of the existing `james-1` codebase. All Windows-specific code (PowerShell, WMI, WinReg) is omitted entirely.

## Open Questions
> [!IMPORTANT]
> 1. **GUI Framework:** I propose using **PyQt6** for the native desktop application. It provides a highly customizable, native feel on Linux.
> 2. **Initial Toolset:** Focus on `nmap`, `aircrack-ng` suite (`airmon-ng`, `airodump-ng`, `aireplay-ng`), `john`, and `hashcat`.

## Proposed Architecture

### 1. Project Structure
```
james-linux/
├── james/                 # Main package
│   ├── gui/               # PyQt6 Desktop UI
│   ├── core/              # Orchestration and AI logic
│   ├── layers/            # Execution layers (Linux Native)
│   ├── tools/             # Wrappers for Parrot OS tools
│   └── skills/            # JSON skill definitions for pentesting
├── main.py                # Application entry point
├── requirements.txt       # Dependencies (PyQt6, etc.)
└── README.md
```

### 2. Linux Native Execution Layer (`layers/native.py`)
- We will implement a `NativeLayer` that exclusively uses `subprocess` to execute Bash commands.
- Include built-in privilege escalation handling (e.g., prompting for `sudo` or utilizing `pkexec` for GUI root execution).

### 3. Tool Wrappers (`tools/parrot.py`)
Python wrappers to parse the output of common Parrot OS tools into structured JSON.
- **Example:** Parsing `nmap -oX -` XML output into a structured dictionary.

### 4. Native Desktop GUI (`gui/`)
- **Main Window:** Dashboard showing system status, interfaces, and active tasks.
- **Task Launcher:** UI to launch complex pentesting workflows.
- **AI Chat/Terminal:** Integrated view to converse with James and see underlying commands.

### 5. AI Integration
- The orchestrator will utilize the AI backend to plan multi-step attacks, executing strictly via the Linux toolset.
