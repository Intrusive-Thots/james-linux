#!/usr/bin/env python3
"""
JAMES Linux — Application Entry Point.

Usage:
    python3 main.py                  Launch desktop GUI (default)
    python3 main.py --server         Launch API server only (headless)
    python3 main.py --both           Launch GUI + API server
    python3 main.py --setup          Interactive setup (API key, certs)
    python3 main.py --install-service Install as systemd service
    python3 main.py --remove-service  Remove systemd service
"""

import sys
import argparse
import logging
import threading
import getpass
import fcntl
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("james")

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
    from james.gui.setup_wizard import (
        SetupWizard, should_show_wizard, load_settings, apply_settings_to_env
    )

    app = QApplication(sys.argv)
    app.setApplicationName("JAMES Linux")
    app.setStyleSheet(DARK_STYLESHEET)

    # Apply any previously saved settings to the environment
    apply_settings_to_env(load_settings())

    # Show setup wizard on first launch
    if should_show_wizard():
        wizard = SetupWizard()
        wizard.exec_()

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


def run_server():
    """Launch the FastAPI server (headless)."""
    import uvicorn
    from james.server.config import load_config
    from james.server.tls import ensure_tls_certs
    from james.server.app import create_app

    config = load_config()
    app = create_app(config)

    ssl_kwargs = {}
    if config.tls_enabled:
        if ensure_tls_certs(config.tls_cert, config.tls_key):
            ssl_kwargs["ssl_certfile"] = config.tls_cert
            ssl_kwargs["ssl_keyfile"] = config.tls_key
            logger.info("TLS enabled")
        else:
            logger.warning("TLS cert generation failed — running without TLS")

    logger.info("Starting JAMES server on %s:%d", config.host, config.port)
    print(f"\n⚡ JAMES server running at {'https' if ssl_kwargs else 'http'}://{config.host}:{config.port}")
    print(f"   API docs: {'https' if ssl_kwargs else 'http'}://localhost:{config.port}/docs")
    print(f"   Dashboard: {'https' if ssl_kwargs else 'http'}://localhost:{config.port}/\n")

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
        **ssl_kwargs,
    )


def run_both():
    """Launch server in a background thread, then start GUI."""
    server_thread = threading.Thread(target=_server_thread, daemon=True)
    server_thread.start()
    run_gui()


def _server_thread():
    """Server thread for --both mode."""
    import uvicorn
    from james.server.config import load_config
    from james.server.tls import ensure_tls_certs
    from james.server.app import create_app

    config = load_config()
    app = create_app(config)

    ssl_kwargs = {}
    if config.tls_enabled:
        if ensure_tls_certs(config.tls_cert, config.tls_key):
            ssl_kwargs["ssl_certfile"] = config.tls_cert
            ssl_kwargs["ssl_keyfile"] = config.tls_key

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="warning",
        **ssl_kwargs,
    )


def run_setup():
    """Interactive setup wizard."""
    from james.server.config import load_config, save_config, generate_api_key, JAMES_HOME
    from james.server.auth import hash_api_key
    from james.server.tls import ensure_tls_certs

    print("\n⚡ JAMES Linux — Setup\n")

    config = load_config()

    # API key
    print("1. API Key (protects remote access)")
    choice = input("   Generate a new API key? [Y/n]: ").strip().lower()
    if choice != "n":
        raw_key = generate_api_key()
        config.api_key = hash_api_key(raw_key)
        print(f"\n   🔑 Your API key (save this!):\n   {raw_key}\n")
    else:
        custom = getpass.getpass("   Enter custom API key: ")
        if custom:
            config.api_key = hash_api_key(custom)
            print("   ✓ API key set.")
        else:
            print("   ⚠ No API key set — server will be open!")

    # Port
    port_input = input(f"2. Server port [{config.port}]: ").strip()
    if port_input.isdigit():
        config.port = int(port_input)

    # TLS
    tls_choice = input("3. Enable TLS/HTTPS? [Y/n]: ").strip().lower()
    config.tls_enabled = tls_choice != "n"
    if config.tls_enabled:
        ensure_tls_certs(config.tls_cert, config.tls_key)

    save_config(config)
    print(f"\n✅ Configuration saved to {JAMES_HOME / 'config.json'}")
    print(f"   Start server: python3 main.py --server")
    print(f"   Start both:   python3 main.py --both\n")


def main():
    parser = argparse.ArgumentParser(description="JAMES Linux — Autonomous AI Pentesting Agent")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--server", action="store_true", help="Run API server only (headless)")
    group.add_argument("--both", action="store_true", help="Run GUI + API server")
    group.add_argument("--setup", action="store_true", help="Interactive setup wizard")
    group.add_argument("--install-service", action="store_true", help="Install as systemd service")
    group.add_argument("--remove-service", action="store_true", help="Remove systemd service")

    args = parser.parse_args()

    # Setup doesn't need singleton lock
    if args.setup:
        run_setup()
        return
    if args.install_service:
        from james.server.service import install_service
        install_service()
        return
    if args.remove_service:
        from james.server.service import uninstall_service
        uninstall_service()
        return

    # ── Singleton check ───────────────────────────────────────
    if not acquire_singleton_lock():
        if args.server:
            print("❌ Another JAMES instance is already running. Exiting.", file=sys.stderr)
            sys.exit(1)
        else:
            _show_already_running_dialog()
            sys.exit(1)

    if args.server:
        run_server()
    elif args.both:
        run_both()
    else:
        run_gui()


if __name__ == "__main__":
    main()

