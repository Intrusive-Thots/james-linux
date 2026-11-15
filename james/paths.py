"""Writable application state, with an override for managed or portable installs."""
import os
from pathlib import Path


def data_dir() -> Path:
    """Use the normal per-user directory unless JAMES_DATA_DIR is configured."""
    configured = os.environ.get("JAMES_DATA_DIR", "").strip()
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".james"
