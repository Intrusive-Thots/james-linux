#!/usr/bin/env python3
"""
JAMES Linux — Application Entry Point.

Usage:
    python3 main.py                  Launch desktop GUI (default)
    python3 main.py --server         Run headless FastAPI web server
    python3 main.py --both           Run GUI + background FastAPI server
    python3 main.py --setup          Run first-time setup wizard
    python3 main.py --headless       Alias for --server
"""

import sys
import logging
import logging.handlers
import argparse
import fcntl
import os
from datetime import datetime
from pathlib import Path


def _setup_logging():
    """Configure logging to write to both console and persistent log files."""
    log_dir = Path.home() / ".james" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 1. Console handler — INFO and above
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # 2. Persistent rotating log — DEBUG and above, 5 x 5 MB
    rotating = logging.handlers.RotatingFileHandler(
        log_dir / "james.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    rotating.setLevel(logging.DEBUG)
    rotating.setFormatter(formatter)
    root.addHandler(rotating)

    # 3. Session log — one file per launch, keeps the last 10
    session_file = log_dir / f"session_{datetime.now():%Y%m%d_%H%M%S}.log"
    session = logging.FileHandler(session_file, encoding="utf-8")
    session.setLevel(logging.DEBUG)
    session.setFormatter(formatter)
    root.addHandler(session)

    # Prune old session files (keep the 10 most recent)
    sessions = sorted(
        log_dir.glob("session_*.log"), key=lambda p: p.stat().st_mtime
    )
    for old in sessions[:-10]:
        try:
            old.unlink()
        except OSError:
            pass

    return logging.getLogger("james")


logger = _setup_logging()

# ── Singleton lock ────────────────────────────────────────────
LOCK_FILE = "/tmp/.james.lock"
_lock_fd = None


def acquire_singleton_lock() -> bool:
    """
    Try to acquire an exclusive lock so only one JAMES instance runs.
    Returns True if lock acquired, False if another instance is running.
    The lock is held for the entire process lifetime and auto-released
    on crash/exit by the OS.
    """
    global _lock_fd
    try:
        _lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        return True
    except (IOError, OSError):
        # Another instance holds the lock
        try:
            with open(LOCK_FILE, "r") as f:
                other_pid = f.read().strip()
        except Exception:
            other_pid = "unknown"
        logger.warning("Another JAMES instance is running (PID %s)", other_pid)
        return False


def _show_already_running_dialog():
    """Show a GUI error dialog when another instance is running."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication(sys.argv)
        try:
            with open(LOCK_FILE, "r") as f:
                other_pid = f.read().strip()
        except Exception:
            other_pid = "?"
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("JAMES Already Running")
        msg.setText("Another JAMES instance is already running.")
        msg.setInformativeText(
            f"PID: {other_pid}\n\n"
            "Only one instance can run at a time.\n"
            "Close the other instance first, or kill it:\n\n"
            f"  kill {other_pid}"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #0b1120;
                color: #c8d6e5;
            }
            QMessageBox QLabel {
                color: #c8d6e5;
                font-size: 13px;
            }
            QPushButton {
                background: #141e30;
                color: #00f0ff;
                border: 1px solid #00f0ff40;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1a2940;
                border-color: #00f0ff;
            }
        """)
        msg.exec_()
    except Exception:
        pass


def run_gui():
    """Launch the PyQt5 desktop GUI."""
    from PyQt5.QtWidgets import QApplication
    from james.gui.main_window import MainWindow
    from james.gui.theme import DARK_STYLESHEET
    from james.core.orchestrator import Orchestrator

    app = QApplication(sys.argv)
    app.setApplicationName("JAMES Linux")
    app.setStyleSheet(DARK_STYLESHEET)

    orchestrator = Orchestrator()
    window = MainWindow(orchestrator)
    window.show()
    sys.exit(app.exec_())


def run_server():
    """Run the headless FastAPI web server."""
    try:
        import uvicorn
        from james.server.app import create_app

        logger.info("Starting JAMES headless server on :1337 ...")
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=1337, log_level="info")
    except ImportError as e:
        logger.error(
            "Server dependencies missing (%s). Install with: pip install uvicorn fastapi",
            e,
        )
        sys.exit(1)


def run_both():
    """Run PyQt5 GUI and start the FastAPI server in a background thread."""
    import threading

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    logger.info("Background API server started on :1337")
    run_gui()


def run_setup():
    """Launch the first-time setup wizard."""
    try:
        from PyQt5.QtWidgets import QApplication
        from james.gui.setup_wizard import SetupWizard

        app = QApplication(sys.argv)
        wizard = SetupWizard()
        wizard.show()
        sys.exit(app.exec_())
    except ImportError:
        logger.error("GUI dependencies not available. Run: pip install PyQt5")
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="james",
        description="JAMES — Just Another Multipurpose Exploitation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                 # Launch GUI (default)
  python3 main.py --server        # Headless API server on :1337
  python3 main.py --both          # GUI + background API server
  python3 main.py --setup         # First-time setup wizard
""",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--server",
        action="store_true",
        help="Run headless FastAPI web server on port 1337 (no GUI)",
    )
    mode.add_argument(
        "--headless",
        action="store_true",
        help="Alias for --server",
    )
    mode.add_argument(
        "--both",
        action="store_true",
        help="Run GUI and start background FastAPI server simultaneously",
    )
    mode.add_argument(
        "--setup",
        action="store_true",
        help="Launch first-time setup / configuration wizard",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.server or args.headless:
        # Headless mode — no singleton lock needed for API server
        run_server()
        return

    if args.setup:
        run_setup()
        return

    # GUI modes require singleton lock
    if not acquire_singleton_lock():
        _show_already_running_dialog()
        sys.exit(1)

    if args.both:
        run_both()
    else:
        run_gui()


if __name__ == "__main__":
    main()
