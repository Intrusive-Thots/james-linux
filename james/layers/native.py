import subprocess
import shlex
import logging
import os
from enum import IntEnum
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class CustomReturnCode(IntEnum):
    SUCCESS = 0
    TIMEOUT = -1
    NOT_FOUND = -2
    EXECUTION_ERROR = -3

class NativeLayer:
    """
    Native Linux Execution Layer.
    Executes commands safely using subprocess without shell=True.
    Provides mechanism to request root privileges via sudo or pkexec.
    """

    def __init__(self, use_gui_auth: bool = False):
        self.use_gui_auth = use_gui_auth

    def _get_privilege_escalator(self) -> List[str]:
        """Returns the appropriate privilege escalator command list."""
        # We omit -n so that it can prompt the user for a password in the CLI if needed
        # In a GUI environment, we might switch to pkexec
        return ["sudo"]

    def execute(self, cmd: List[str], require_root: bool = False, timeout: Optional[float] = None) -> Tuple[int, str, str]:
        """
        Executes a command securely.

        Args:
            cmd (List[str]): Command and arguments as a list.
            require_root (bool): If True, prepends sudo.
            timeout (float): Execution timeout in seconds.

        Returns:
            Tuple[int, str, str]: Return code, standard output, standard error.
        """
        if require_root and os.geteuid() != 0:
            cmd = self._get_privilege_escalator() + cmd

        # We strictly do not use shell=True for security reasons.
        logger.info(f"Executing: {' '.join(shlex.quote(c) for c in cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timed out after {timeout} seconds, but capturing partial output.")
            # We return e.stdout and e.stderr because long-running commands like airodump-ng
            # will hit the timeout intentionally, and we still need their output.
            stdout_str = e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else (e.stderr or "")
            return CustomReturnCode.TIMEOUT, stdout_str, stderr_str
        except FileNotFoundError as e:
            logger.error(f"Command not found: {e}")
            return CustomReturnCode.NOT_FOUND, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return CustomReturnCode.EXECUTION_ERROR, "", str(e)
