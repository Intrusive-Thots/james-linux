#!/usr/bin/env python3
"""Prepare the local JAMES environment and open the Wi-Fi Lab tab."""

import argparse
import fcntl
import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from james.core.wifi_lab_setup import (
    find_tool,
    install_packages,
    missing_radio_packages,
)

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / "bin/python"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV / ".james-wifi-lab-requirements"
QT_LIBRARIES = {
    "libGL.so.1": "libgl1",
    "libdbus-1.so.3": "libdbus-1-3",
    "libX11-xcb.so.1": "libx11-xcb1",
    "libxcb-icccm.so.4": "libxcb-icccm4",
    "libxcb-image.so.0": "libxcb-image0",
    "libxcb-keysyms.so.1": "libxcb-keysyms1",
    "libxcb-randr.so.0": "libxcb-randr0",
    "libxcb-render-util.so.0": "libxcb-render-util0",
    "libxcb-shape.so.0": "libxcb-shape0",
    "libxcb-xfixes.so.0": "libxcb-xfixes0",
    "libxcb-xinerama.so.0": "libxcb-xinerama0",
    "libxcb-xkb.so.1": "libxcb-xkb1",
    "libxkbcommon-x11.so.0": "libxkbcommon-x11-0",
}


def missing_system_packages() -> list[str]:
    packages = set(missing_radio_packages())
    if not _python_imports("import pip") and importlib.util.find_spec("ensurepip") is None:
        packages.add("python3-venv")
    if ldconfig := find_tool("ldconfig"):
        libraries = subprocess.run(
            [ldconfig, "-p"], capture_output=True, text=True, timeout=5, check=True
        ).stdout
        available = {line.split()[0] for line in libraries.splitlines() if " => " in line}
        packages.update(
            package for library, package in QT_LIBRARIES.items() if library not in available
        )
    return sorted(packages)


def _python_imports(code: str) -> bool:
    return (
        PYTHON.exists()
        and subprocess.run(
            [str(PYTHON), "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        ).returncode
        == 0
    )


def environment_ready() -> bool:
    return _python_imports("import pip, keyring; from PyQt5 import QtWidgets")


def prepare_environment():
    VENV.mkdir(exist_ok=True)
    with (VENV / ".james-wifi-lab-setup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        install_packages(missing_system_packages())
        if not _python_imports("import pip"):
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        fingerprint = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
        if not (
            STAMP.is_file() and STAMP.read_text().strip() == fingerprint and environment_ready()
        ):
            print("Preparing the JAMES Python environment.", flush=True)
            subprocess.run(
                [str(PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True
            )
            if not environment_ready():
                raise RuntimeError(
                    "JAMES could not load PyQt5 or keyring after installing its requirements."
                )
            STAMP.write_text(fingerprint + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Report missing setup without installing packages"
    )
    args = parser.parse_args()
    if sys.version_info < (3, 10):  # noqa: UP036 - bootstrap may run on older system Python
        parser.error("JAMES Wi-Fi Lab requires Python 3.10 or newer.")
    try:
        if args.check:
            missing = missing_system_packages()
            ready = environment_ready()
            print("System packages: " + (", ".join(missing) if missing else "ready"))
            print("JAMES Python environment: " + ("ready" if ready else "setup required"))
            return int(bool(missing) or not ready)
        if os.geteuid() == 0:
            parser.error("Start Wi-Fi Lab as your regular desktop user.")
        if not any(
            os.environ.get(key) for key in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")
        ):
            parser.error("Start Wi-Fi Lab from a graphical desktop session.")
        prepare_environment()
        os.chdir(ROOT)
        os.execv(str(PYTHON), [str(PYTHON), str(ROOT / "main.py"), "--wifi-lab-ui"])
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Wi-Fi Lab setup failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
