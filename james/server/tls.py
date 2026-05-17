"""
TLS Certificate Generation.

Auto-generates self-signed certs for HTTPS on first run.
"""

import subprocess
import logging
from pathlib import Path

from james.server.config import CERTS_DIR

logger = logging.getLogger(__name__)


def ensure_tls_certs(cert_path: str, key_path: str) -> bool:
    """
    Ensure TLS cert and key exist. Generate self-signed if missing.
    Returns True if certs are ready.
    """
    cert = Path(cert_path)
    key = Path(key_path)

    if cert.exists() and key.exists():
        logger.info("TLS certs found at %s", cert_path)
        return True

    logger.info("Generating self-signed TLS certificate…")
    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "365",
                "-nodes",
                "-subj",
                "/CN=james-agent/O=JAMES/C=US",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        # restrict permissions
        key.chmod(0o600)
        cert.chmod(0o644)

        logger.info("✓ Self-signed cert generated at %s", cert_path)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to generate TLS cert: %s", e.stderr)
        return False
    except FileNotFoundError:
        logger.error("openssl not found — cannot generate TLS cert")
        return False
