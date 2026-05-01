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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("james")


def run_gui():
    """Launch the PyQt6 desktop GUI."""
    from PyQt6.QtWidgets import QApplication
    from james.gui.main_window import MainWindow
    from james.gui.theme import DARK_STYLESHEET

    app = QApplication(sys.argv)
    app.setApplicationName("JAMES Linux")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


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

    if args.setup:
        run_setup()
    elif args.install_service:
        from james.server.service import install_service
        install_service()
    elif args.remove_service:
        from james.server.service import uninstall_service
        uninstall_service()
    elif args.server:
        run_server()
    elif args.both:
        run_both()
    else:
        run_gui()


if __name__ == "__main__":
    main()
