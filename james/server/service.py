"""
Systemd Service Installer.

Generates and installs a systemd unit file so JAMES runs
as a background service that starts on boot.
"""

import os
import sys
import textwrap
import subprocess
import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "james-agent"
SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}.service"


def generate_unit_file() -> str:
    """Generate the systemd unit file content."""
    python = sys.executable
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
    )
    work_dir = os.path.dirname(main_py)
    user = os.environ.get("USER", "root")

    return textwrap.dedent(f"""\
        [Unit]
        Description=JAMES Linux — Autonomous AI Pentesting Agent
        After=network.target

        [Service]
        Type=simple
        User={user}
        WorkingDirectory={work_dir}
        ExecStart={python} {main_py} --server
        Restart=on-failure
        RestartSec=5
        Environment=PYTHONUNBUFFERED=1

        [Install]
        WantedBy=multi-user.target
    """)


def install_service() -> bool:
    """Install and enable the systemd service."""
    unit = generate_unit_file()

    try:
        # write unit file (requires root)
        with open(SERVICE_PATH, "w") as f:
            f.write(unit)

        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
        subprocess.run(["systemctl", "start", SERVICE_NAME], check=True)

        logger.info("✓ Service '%s' installed and started", SERVICE_NAME)
        print(f"\n✅ Service installed: {SERVICE_NAME}")
        print(f"   Status:  systemctl status {SERVICE_NAME}")
        print(f"   Logs:    journalctl -u {SERVICE_NAME} -f")
        print(f"   Stop:    sudo systemctl stop {SERVICE_NAME}")
        print(f"   Disable: sudo systemctl disable {SERVICE_NAME}")
        return True
    except PermissionError:
        print(f"\n❌ Permission denied. Run with sudo:")
        print(f"   sudo python3 main.py --install-service")
        return False
    except subprocess.CalledProcessError as e:
        logger.error("Service installation failed: %s", e)
        return False


def uninstall_service() -> bool:
    """Stop, disable, and remove the systemd service."""
    try:
        subprocess.run(["systemctl", "stop", SERVICE_NAME], check=False)
        subprocess.run(["systemctl", "disable", SERVICE_NAME], check=False)
        if os.path.exists(SERVICE_PATH):
            os.remove(SERVICE_PATH)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print(f"✅ Service '{SERVICE_NAME}' removed.")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
