#!/usr/bin/env python3
"""Exercise an extracted Debian package independently of its build checkout."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import websockets


def stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


async def check_websocket(port: int) -> None:
    async with asyncio.timeout(15):
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws") as ws:
            while True:
                message = json.loads(await ws.recv())
                if message.get("type") == "init":
                    assert isinstance(message["interfaces"], list), message
                    assert isinstance(message["loot"], dict), message
                    return


def validate(package: Path, source_commit: str) -> None:
    package = package.resolve()
    expected = package.with_name(package.name + ".sha256").read_text().split()
    with package.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert expected == [digest, package.name], "Installer checksum mismatch"
    logs = package.parent / "smoke-logs"
    logs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="james-package-") as name:
        root = Path(name)
        installed = root / "installed"
        subprocess.run(["dpkg-deb", "--extract", str(package), str(installed)], check=True)
        executable = installed / "opt/james-linux/james"
        info = (installed / "usr/share/doc/james-linux/BUILD-INFO").read_text()
        assert f"Source-commit: {source_commit}\n" in info, info
        assert "Working-tree-changes: False\n" in info, info
        print(info, flush=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {
            **os.environ,
            "JAMES_DATA_DIR": str(root / "state"),
            "JAMES_API_HOST": "127.0.0.1",
            "JAMES_API_PORT": str(port),
        }
        # The smoke test exercises the local browser workflow, with isolated state.
        for variable in ("JAMES_API_TOKEN", "JAMES_WIRELESS_SOC_DB", "JAMES_AUTO_AGENT",
                         "JAMES_API_SSL_CERTFILE", "JAMES_API_SSL_KEYFILE"):
            env.pop(variable, None)
        log = logs / "api.log"
        with log.open("w") as output:
            process = subprocess.Popen([str(executable), "--server"], cwd=root,
                                       env=env, stdout=output, stderr=subprocess.STDOUT)
            base = f"http://127.0.0.1:{port}"
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(log.read_text())
                    try:
                        with urllib.request.urlopen(base + "/api/health", timeout=1) as response:
                            assert json.load(response)["status"] == "ok"
                        break
                    except OSError:
                        time.sleep(0.25)
                else:
                    raise RuntimeError(log.read_text())
                with urllib.request.urlopen(base + "/", timeout=5) as response:
                    html = response.read().decode()
                asset = re.search(r'src="(/assets/[^\"]+\.js)"', html)
                assert asset, "No production JavaScript asset in index"
                with urllib.request.urlopen(base + asset.group(1), timeout=5) as response:
                    assert response.status == 200 and len(response.read()) > 1000
                with urllib.request.urlopen(base + "/api/wireless-soc/summary", timeout=5) as response:
                    assert json.load(response) == {
                        "assets_seen": 0, "approved_aps": 0,
                        "unreviewed_detections": 0, "observations": 0,
                    }
                try:
                    urllib.request.urlopen(base + "/api/missing", timeout=5)
                except urllib.error.HTTPError as error:
                    assert error.code == 404
                else:
                    raise AssertionError("Missing API endpoint unexpectedly succeeded")
                asyncio.run(check_websocket(port))
                print("PASS: extracted API, HTML, JS, empty SOC, missing API, custom-port WebSocket", flush=True)
            finally:
                stop(process)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env.update(QT_QPA_PLATFORM="offscreen", XDG_CACHE_HOME=str(root / "cache"),
                   XDG_RUNTIME_DIR=str(runtime))
        log = logs / "desktop.log"
        with log.open("w") as output:
            process = subprocess.Popen([str(executable)], cwd=root, env=env,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                for _ in range(24):
                    time.sleep(0.25)
                    if process.poll() is not None:
                        raise RuntimeError(log.read_text())
                text = log.read_text()
                assert text.count("[task] wifi_interfaces") >= 2, text
                assert "Traceback" not in text, text
                print("PASS: offscreen desktop processed Qt timer callbacks and stayed alive", flush=True)
            finally:
                stop(process)
    print(f"SHA256: {digest}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        parser.error("--source-commit must be a full Git SHA")
    validate(args.package, args.source_commit)
