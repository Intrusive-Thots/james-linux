# James Linux: Parrot OS Pentesting Agent

JAMES Linux is an autonomous AI pentesting agent designed specifically for Linux environments (tailored for Parrot OS). It features native integration directly with industry-standard security tools such as `aircrack-ng`, `nmap`, and `hashcat`.

> [!WARNING]
> This project is a completely independent native desktop application tailored for Linux. All Windows-specific code (PowerShell, WMI, WinReg) is omitted entirely.

## Features
- **Native Execution Layer:** Exclusively uses `subprocess` without `shell=True` for maximum security.
- **AI Orchestration:** Automates pentesting operations with a comprehensive reasoning loop and strict consent workflows.
- **CLI First:** Includes a beautiful CLI built with Typer and Rich.
- **Parrot OS Tools Integration:** Seamlessly wraps tools like `airmon-ng` and `airodump-ng`.

## Setup

1. Clone the repository on a Parrot OS or Kali Linux machine.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the CLI tool:
   ```bash
   python main.py --help
   ```

### Quick Start

Start an autonomous pentesting cycle against a target:
```bash
python main.py start <TARGET_SCOPE> --interface <INTERFACE>
```

View application information:
```bash
python main.py info
```

## Project Structure
```text
james-linux/
├── james/                 # Main package
│   ├── gui/               # PyQt6 Desktop UI
│   ├── core/              # Orchestration and AI logic
│   ├── layers/            # Execution layers (Linux Native)
│   ├── tools/             # Wrappers for Parrot OS tools
│   └── skills/            # JSON skill definitions for pentesting
├── tests/                 # Unit tests
├── main.py                # CLI Application entry point
├── requirements.txt       # Dependencies
└── README.md
```

*Note: This project is under active development. Ensure you have explicit legal permission to test any target.*