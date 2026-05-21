"""
JAMES GUI Remote — VNC + noVNC bridge.

Starts x11vnc to share the local X display, and noVNC/websockify
to proxy it through a browser.  The user opens
    http://<LAN_IP>:6080/vnc.html
on any device and gets the full JAMES PyQt5 GUI in their browser.

Usage:
    vnc = GUIRemote()
    vnc.start()       # → starts x11vnc + noVNC
    vnc.stop()
    vnc.url           # → http://192.168.1.x:6080/vnc.html
"""

import logging
import os
import secrets
import signal
import subprocess
import time
import threading

from james.utils.net import get_local_ip

logger = logging.getLogger(__name__)


class GUIRemote:
    """
    Stream the live JAMES GUI to a browser via VNC + noVNC.

    Architecture:
        X Display  →  x11vnc (:5900)  →  websockify (:6080)  →  Browser
    """

    VNC_PORT = 5900
    WEB_PORT = 6080

    def __init__(self):
        self._vnc_proc = None
        self._novnc_proc = None
        self.running = False
        self._display = os.environ.get("DISPLAY", ":0")
        self._vnc_password: str = ""  # generated per-session

    @property
    def url(self) -> str:
        ip = get_local_ip()
        return f"http://{ip}:{self.WEB_PORT}/vnc.html"

    @property
    def vnc_url(self) -> str:
        ip = get_local_ip()
        return f"{ip}:{self.VNC_PORT}"

    def _generate_vnc_password(self) -> str:
        """Generate a random 8-character alphanumeric VNC password."""
        return secrets.token_urlsafe(6)[:8]  # 8 chars, URL-safe alphabet

    def _ensure_deps(self) -> list[str]:
        """Install missing dependencies.  Returns list of actions taken."""
        actions = []

        # x11vnc
        if not self._which("x11vnc"):
            try:
                subprocess.run(
                    ["sudo", "-n", "apt-get", "install", "-y", "x11vnc"],
                    capture_output=True,
                    timeout=60,
                )
                actions.append("Installed x11vnc")
            except Exception as e:
                logger.warning("x11vnc install failed: %s", e)
                actions.append(f"x11vnc install failed: {e}")

        # noVNC + websockify
        novnc_path = self._find_novnc()
        if not novnc_path:
            try:
                subprocess.run(
                    [
                        "sudo",
                        "-n",
                        "apt-get",
                        "install",
                        "-y",
                        "novnc",
                        "websockify",
                    ],
                    capture_output=True,
                    timeout=60,
                )
                actions.append("Installed noVNC + websockify")
            except Exception as e:
                logger.warning("noVNC apt install failed: %s — trying pip", e)
                # Fallback: pip install websockify
                try:
                    subprocess.run(
                        [
                            "pip3",
                            "install",
                            "websockify",
                            "--break-system-packages",
                        ],
                        capture_output=True,
                        timeout=30,
                    )
                    actions.append("Installed websockify via pip")
                except Exception as e2:
                    logger.warning("websockify pip install failed: %s", e2)
                    actions.append(f"websockify install failed: {e2}")

        return actions

    def _which(self, cmd: str) -> str:
        """Find a command in PATH."""
        try:
            result = subprocess.run(
                ["which", cmd], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _find_novnc(self) -> str:
        """Find the noVNC web directory."""
        candidates = [
            "/usr/share/novnc",
            "/usr/share/noVNC",
            "/snap/novnc/current/utils",
            "/opt/noVNC",
        ]
        for p in candidates:
            if os.path.isdir(p):
                return p
        return ""

    def _create_vnc_password(self) -> str:
        """Create a VNC password file and return its path."""
        pw_dir = os.path.expanduser("~/.james")
        os.makedirs(pw_dir, exist_ok=True)
        pw_file = os.path.join(pw_dir, "vnc_passwd")

        # Generate a random password each session
        self._vnc_password = self._generate_vnc_password()

        try:
            proc = subprocess.run(
                ["x11vnc", "-storepasswd", self._vnc_password, pw_file],
                capture_output=True,
                timeout=5,
            )
            if proc.returncode == 0:
                os.chmod(pw_file, 0o600)  # owner-only
                return pw_file
        except Exception as e:
            logger.warning("Failed to create VNC password file: %s", e)
        return ""

    def start(self) -> dict:
        """
        Start VNC + noVNC.  Returns dict with status info.

        Returns:
            {
                "success": bool,
                "url": str,            # browser URL
                "vnc_url": str,        # raw VNC address
                "vnc_password": str,   # generated password for this session
                "actions": [str],      # setup steps taken
                "errors": [str],
            }
        """
        if self.running:
            return {
                "success": True,
                "url": self.url,
                "vnc_url": self.vnc_url,
                "vnc_password": self._vnc_password,
                "actions": ["Already running"],
                "errors": [],
            }

        actions = []
        errors = []

        # 1. Ensure dependencies
        dep_actions = self._ensure_deps()
        actions.extend(dep_actions)

        # 2. Kill any existing x11vnc / websockify
        for proc_name in ("x11vnc", "websockify"):
            try:
                subprocess.run(
                    ["sudo", "-n", "pkill", "-f", proc_name],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
        time.sleep(0.5)

        # 3. Create VNC password
        pw_file = self._create_vnc_password()
        if pw_file:
            actions.append(
                f"VNC password configured (password: {self._vnc_password})"
            )
        else:
            actions.append(
                "VNC running without password (password file creation failed)"
            )

        # 4. Open firewall ports
        for port in [self.VNC_PORT, self.WEB_PORT]:
            try:
                subprocess.run(
                    ["sudo", "-n", "ufw", "allow", str(port)],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
            try:
                subprocess.run(
                    [
                        "sudo",
                        "-n",
                        "iptables",
                        "-I",
                        "INPUT",
                        "-p",
                        "tcp",
                        "--dport",
                        str(port),
                        "-j",
                        "ACCEPT",
                    ],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
        actions.append(
            f"Firewall ports {self.VNC_PORT},{self.WEB_PORT} opened"
        )

        # 5. Start x11vnc
        vnc_cmd = [
            "x11vnc",
            "-display",
            self._display,
            "-forever",  # Don't exit after first disconnect
            "-shared",  # Allow multiple connections
            "-noxdamage",  # Compatibility
            "-rfbport",
            str(self.VNC_PORT),
            "-bg",  # Background after starting
        ]
        if pw_file:
            vnc_cmd.extend(["-rfbauth", pw_file])
        else:
            vnc_cmd.append("-nopw")

        try:
            self._vnc_proc = subprocess.Popen(
                vnc_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(1.5)

            # Check if it started
            if self._vnc_proc.poll() is not None:
                stderr = self._vnc_proc.stderr.read().decode(errors="replace")
                errors.append(f"x11vnc failed to start: {stderr[:200]}")
            else:
                actions.append(
                    f"x11vnc sharing {self._display} on :{self.VNC_PORT}"
                )
        except FileNotFoundError:
            errors.append(
                "x11vnc not found — install with: sudo apt install x11vnc"
            )
        except Exception as e:
            errors.append(f"x11vnc error: {e}")

        # 6. Start noVNC / websockify
        novnc_dir = self._find_novnc()

        if novnc_dir:
            # Use the bundled noVNC launch script
            launch_script = os.path.join(novnc_dir, "utils", "novnc_proxy")
            if not os.path.exists(launch_script):
                launch_script = os.path.join(novnc_dir, "utils", "launch.sh")

            if os.path.exists(launch_script):
                try:
                    self._novnc_proc = subprocess.Popen(
                        [
                            launch_script,
                            "--listen",
                            str(self.WEB_PORT),
                            "--vnc",
                            f"localhost:{self.VNC_PORT}",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    time.sleep(1)
                    actions.append(f"noVNC proxy on :{self.WEB_PORT}")
                except Exception as e:
                    errors.append(f"noVNC launch error: {e}")
            else:
                # Fall back to websockify with --web pointing to noVNC dir
                self._start_websockify(novnc_dir, actions, errors)
        else:
            # Use bare websockify (no pretty page, but still works)
            self._start_websockify(None, actions, errors)

        # Verify
        if not errors or (self._vnc_proc and self._vnc_proc.poll() is None):
            self.running = True
            logger.info(
                "GUI Remote active: %s (password: %s)",
                self.url,
                self._vnc_password,
            )
            return {
                "success": True,
                "url": self.url,
                "vnc_url": self.vnc_url,
                "vnc_password": self._vnc_password,
                "actions": actions,
                "errors": errors,
            }
        else:
            self.running = False
            return {
                "success": False,
                "url": "",
                "vnc_url": "",
                "vnc_password": "",
                "actions": actions,
                "errors": errors,
            }

    def _start_websockify(self, web_dir, actions, errors):
        """Start websockify as the WebSocket → VNC proxy."""
        ws_cmd = ["websockify"]
        if web_dir:
            ws_cmd.extend(["--web", web_dir])
        ws_cmd.extend(
            [
                str(self.WEB_PORT),
                f"localhost:{self.VNC_PORT}",
            ]
        )

        try:
            self._novnc_proc = subprocess.Popen(
                ws_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(1)
            if self._novnc_proc.poll() is not None:
                stderr = self._novnc_proc.stderr.read().decode(
                    errors="replace"
                )
                errors.append(f"websockify failed: {stderr[:200]}")
            else:
                actions.append(f"websockify proxy on :{self.WEB_PORT}")
        except FileNotFoundError:
            errors.append(
                "websockify not found — install: sudo apt install novnc websockify"
            )
        except Exception as e:
            errors.append(f"websockify error: {e}")

    def stop(self):
        """Stop VNC + noVNC."""
        for proc, name in [
            (self._novnc_proc, "noVNC/websockify"),
            (self._vnc_proc, "x11vnc"),
        ]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info("Stopped %s", name)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        # Also pkill to be thorough
        for pname in ("x11vnc", "websockify"):
            try:
                subprocess.run(
                    ["sudo", "-n", "pkill", "-f", pname],
                    capture_output=True,
                    timeout=3,
                )
            except Exception:
                pass

        self._vnc_proc = None
        self._novnc_proc = None
        self.running = False
        self._vnc_password = ""
        logger.info("GUI Remote stopped.")

    def is_running(self) -> bool:
        return self.running
