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
from typing import Optional

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
        
        # Ensure /sbin and /usr/sbin are in PATH for desktop launcher compatibility
        current_path = os.environ.get("PATH", "")
        for sbin_path in ["/sbin", "/usr/sbin", "/usr/local/sbin"]:
            if sbin_path not in current_path:
                current_path = f"{sbin_path}:{current_path}" if current_path else sbin_path
        os.environ["PATH"] = current_path

    # ── public API ──────────────────────────────────────────────

    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        on_output: Optional[callable] = None,
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
        effective_timeout = timeout if timeout is not None else self.default_timeout
        cmd = self._prepare_command(command, sudo)
        merged_env = {**os.environ, **(env or {})}

        logger.info("exec → %s  (timeout=%ss)", cmd, effective_timeout)

        if on_output:
            return self._run_streaming(cmd, effective_timeout, cwd, merged_env, on_output)
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
        return subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=merged_env,
            preexec_fn=os.setsid,  # own process group for clean kill
        )

    @staticmethod
    def kill_background(proc: subprocess.Popen) -> None:
        """Kill an entire process group spawned by run_background."""
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    def check_tool(self, tool_name: str) -> bool:
        """Return True if *tool_name* is available on PATH."""
        result = self.run(f"which {shlex.quote(tool_name)}", timeout=5)
        return result.success

    # ── internals ───────────────────────────────────────────────

    def _prepare_command(self, command: str, sudo: bool = True) -> str:
        """Always escalate to root via sudo with password piped in."""
        if self._is_root:
            return command
        return f"echo 'malcolm' | sudo -S {command}"

    def _run_blocking(self, cmd, timeout, cwd, env) -> CommandResult:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env,
            )
            return CommandResult(
                command=cmd,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out after %ss: %s", timeout, cmd)
            return CommandResult(
                command=cmd, returncode=-1, stdout="", stderr="", timed_out=True
            )

    def _run_streaming(self, cmd, timeout, cwd, env, on_output) -> CommandResult:
        stdout_lines = []
        stderr_text = ""
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env,
            )
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
            return CommandResult(
                command=cmd,
                returncode=-1,
                stdout="\n".join(stdout_lines),
                stderr=stderr_text,
                timed_out=True,
            )
