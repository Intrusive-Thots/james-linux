"""
Native Linux Execution Layer.

Provides subprocess-based command execution with privilege escalation,
timeout handling, and structured output capture. This is the ONLY
execution layer — no Windows abstractions exist in this codebase.
"""

import subprocess
import shlex
import os
import signal
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Structured result from a command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def as_dict(self) -> dict:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "success": self.success,
        }


class NativeLayer:
    """
    Executes commands on the local Linux system via subprocess.

    Features:
      - Optional sudo / pkexec privilege escalation
      - Configurable timeouts
      - Real-time streaming callback for long-running tools
      - Signal-safe process cleanup
    """

    def __init__(self, default_timeout: int = 120):
        self.default_timeout = default_timeout
        self._is_root = os.geteuid() == 0
        self._sudo_pass: Optional[str] = None
        self._bg_procs: list[subprocess.Popen] = []  # process registry

        # Allow sudo password from environment (never hardcode it)
        env_pass = os.environ.get("JAMES_SUDO_PASS")
        if env_pass:
            self._sudo_pass = env_pass

        # Ensure /sbin and /usr/sbin are in PATH for desktop launcher compatibility
        current_path = os.environ.get("PATH", "")
        for sbin_path in ["/sbin", "/usr/sbin", "/usr/local/sbin"]:
            if sbin_path not in current_path:
                current_path = (
                    f"{sbin_path}:{current_path}"
                    if current_path
                    else sbin_path
                )
        os.environ["PATH"] = current_path

    def set_sudo_password(self, password: str):
        """Set the sudo password for privilege escalation (stored in-memory only)."""
        self._sudo_pass = password

    # ── public API ──────────────────────────────────────────────

    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """
        Run a shell command and return a structured result.

        Args:
            command:   The command string to execute.
            sudo:      If True, prepend 'sudo' (skipped when already root).
            timeout:   Per-command timeout in seconds (None → default_timeout).
            cwd:       Working directory for the subprocess.
            env:       Extra environment variables (merged with os.environ).
            on_output: Optional callback invoked with each stdout line in
                       real-time (useful for streaming nmap / airodump output).
        """
        effective_timeout = (
            timeout if timeout is not None else self.default_timeout
        )
        cmd = self._prepare_command(command, sudo)
        merged_env = {**os.environ, **(env or {})}

        # Log short utility commands at DEBUG to avoid log flooding from polling
        log_level = logging.DEBUG if effective_timeout <= 5 else logging.INFO
        logger.log(
            log_level, "exec → %s  (timeout=%ss)", cmd, effective_timeout
        )

        if on_output:
            return self._run_streaming(
                cmd, effective_timeout, cwd, merged_env, on_output
            )
        return self._run_blocking(cmd, effective_timeout, cwd, merged_env)

    def run_background(
        self,
        command: str,
        *,
        sudo: bool = False,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> subprocess.Popen:
        """
        Launch a long-running process (e.g. airodump-ng) without blocking.

        Returns the Popen handle so the caller can read output / kill later.
        """
        cmd = self._prepare_command(command, sudo)
        merged_env = {**os.environ, **(env or {})}
        logger.info("exec (bg) → %s", cmd)
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
            env=merged_env,
            start_new_session=True,  # own process group for clean kill
        )
        self._bg_procs.append(proc)
        return proc

    def kill_background(self, proc: subprocess.Popen) -> None:
        """Kill an entire process group spawned by run_background."""
        if proc.poll() is not None:
            # Already dead — just clean up registry
            if proc in self._bg_procs:
                self._bg_procs.remove(proc)
            return
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        if proc in self._bg_procs:
            self._bg_procs.remove(proc)

    def kill_all_background(self) -> int:
        """Kill every tracked background process. Returns count killed."""
        killed = 0
        for proc in list(self._bg_procs):
            if proc.poll() is None:
                self.kill_background(proc)
                killed += 1
        self._bg_procs.clear()
        return killed

    def reap_dead(self) -> None:
        """Remove already-exited processes from the registry."""
        self._bg_procs = [p for p in self._bg_procs if p.poll() is None]

    def check_tool(self, tool_name: str) -> bool:
        """Return True if *tool_name* is available on PATH."""
        result = self.run(f"which {shlex.quote(tool_name)}", timeout=5)
        return result.success

    # ── internals ───────────────────────────────────────────────

    def _prepare_command(self, command: str, sudo: bool = False) -> str:
        """Optionally wrap command with sudo privilege escalation.

        If sudo is requested and we are not already root, pipes the
        stored password via stdin to ``sudo -S``. The password must
        have been set via ``set_sudo_password()`` or the
        ``JAMES_SUDO_PASS`` environment variable.
        """
        if not sudo or self._is_root:
            return command
        if not self._sudo_pass:
            logger.warning(
                "sudo requested but no password configured — "
                "set via set_sudo_password() or JAMES_SUDO_PASS env var. "
                "Attempting passwordless sudo."
            )
            return f"sudo -n {command}"
        return f"echo {shlex.quote(self._sudo_pass)} | sudo -S {command}"

    def _run_blocking(self, cmd, timeout, cwd, env) -> CommandResult:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env,
            start_new_session=True,  # own session for clean kill
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return CommandResult(
                command=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out after %ss: %s", timeout, cmd)
            # Kill the entire process group to avoid zombies
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
            return CommandResult(
                command=cmd,
                returncode=-1,
                stdout=stdout or "",
                stderr=stderr or "",
                timed_out=True,
            )

    def _run_streaming(
        self, cmd, timeout, cwd, env, on_output
    ) -> CommandResult:
        stdout_lines = []
        stderr_text = ""
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env,
        )
        try:
            for line in proc.stdout:
                stripped = line.rstrip("\n")
                stdout_lines.append(stripped)
                on_output(stripped)
            proc.wait(timeout=timeout)
            stderr_text = proc.stderr.read()
            return CommandResult(
                command=cmd,
                returncode=proc.returncode,
                stdout="\n".join(stdout_lines),
                stderr=stderr_text,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            # communicate() drains and closes both pipes, preventing FD leaks
            _, stderr_text = proc.communicate(timeout=5)
            return CommandResult(
                command=cmd,
                returncode=-1,
                stdout="\n".join(stdout_lines),
                stderr=stderr_text or "",
                timed_out=True,
            )
        finally:
            # Ensure pipes are closed even on unexpected exceptions
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
