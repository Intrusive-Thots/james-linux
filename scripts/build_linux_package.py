#!/usr/bin/env python3
"""Compile the desktop/API runtime and assemble a Debian installer, without root."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from james import __version__


def run(*args: str, **kwargs) -> None:
    subprocess.run(args, check=True, cwd=ROOT, **kwargs)


def build() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-web-build", action="store_true", help="Use an existing web/dist build")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("This package target requires Linux x86_64; build other architectures on their target host.")
    if not shutil.which("dpkg-deb"):
        parser.error("dpkg-deb is required (Debian package: dpkg-dev).")
    if not args.skip_web_build:
        run("pnpm", "--dir", str(ROOT / "web"), "run", "build")
    if not (ROOT / "web/dist/index.html").is_file():
        parser.error("Build web/dist first: cd web && pnpm install --frozen-lockfile && pnpm run build")
    work = ROOT / "build/linux-package"
    output = ROOT / "dist"
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=True)
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(work / "cache"))
    run(
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "james", "--distpath", str(work / "runtime"),
        "--workpath", str(work / "pyinstaller"), "--specpath", str(work),
        "--collect-submodules", "james", "--collect-submodules", "uvicorn",
        "--collect-submodules", "keyring.backends",
        "--copy-metadata", "google-antigravity", "--copy-metadata", "keyring",
        "--add-data", f"{ROOT / 'james/skills'}:james/skills",
        "--add-data", f"{ROOT / 'james/wordlists'}:james/wordlists",
        "--add-data", f"{ROOT / 'james/tools/evil_portals'}:james/tools/evil_portals",
        "--add-data", f"{ROOT / 'wordlists'}:wordlists",
        "--add-data", f"{ROOT / 'web/dist'}:web/dist",
        str(ROOT / "main.py"), env=env,
    )
    stage = work / "deb"
    if stage.exists():
        shutil.rmtree(stage)
    runtime = stage / "opt/james-linux"
    shutil.copytree(work / "runtime/james", runtime, symlinks=True)
    bin_dir = stage / "usr/bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "james").symlink_to("/opt/james-linux/james")
    apps = stage / "usr/share/applications"
    apps.mkdir(parents=True)
    (apps / "james-linux.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=JAMES Linux\n"
        "Comment=JAMES desktop and local API\nExec=james\nTerminal=false\n"
        "Categories=System;Network;\nKeywords=JAMES;wireless;\n"
    )
    docs = stage / "usr/share/doc/james-linux"
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", docs / "copyright")
    shutil.copy2(ROOT / "docs/LINUX_INSTALLER.md", docs / "README.md")
    # Record the actual source and dependency set used for this binary build.
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    (docs / "BUILD-INFO").write_text(
        f"Version: {__version__}\nSource-commit: {source}\nWorking-tree-changes: {dirty}\n"
        f"Build-platform: {platform.platform()}\nPython: {platform.python_version()}\n"
    )
    freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (docs / "python-dependencies.txt").write_text(freeze)
    control = stage / "DEBIAN"
    control.mkdir()
    size = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file()) // 1024
    (control / "control").write_text(
        f"Package: james-linux\nVersion: {__version__}\nArchitecture: amd64\n"
        "Maintainer: Intrusive-Thots <noreply@github.com>\nSection: net\nPriority: optional\n"
        f"Installed-Size: {size}\n"
        "Depends: libc6 (>= 2.41), libstdc++6 (>= 14), libgl1, libegl1, libglib2.0-0t64, "
        "libfontconfig1, libfreetype6, libx11-6, libx11-xcb1, libxcb1, "
        "libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, "
        "libxcb-xinerama0, libxcb-xkb1, libxkbcommon-x11-0\n"
        "Homepage: https://github.com/Intrusive-Thots/james-linux\n"
        "Description: JAMES Linux desktop and local web API\n"
        " Bundles Python, Qt, the API, and the compiled web client.\n"
        " External wireless hardware and security tools are optional host capabilities.\n"
    )
    # Checkouts can have owner-only source modes; installed data must be readable.
    for path in stage.rglob("*"):
        if path.is_symlink():
            continue
        path.chmod(0o755 if path.is_dir() or os.access(path, os.X_OK) else 0o644)
    artifact = output / f"james-linux_{__version__}_debian13_amd64.deb"
    run("dpkg-deb", "--root-owner-group", "--build", str(stage), str(artifact))
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / f"{artifact.name}.sha256").write_text(f"{digest}  {artifact.name}\n")
    print(f"Installer: {artifact}\nSHA256: {digest}")


if __name__ == "__main__":
    build()
