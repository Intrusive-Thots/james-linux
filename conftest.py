"""Isolate test state before root-level tests import the API or Qt modules."""

import os
import tempfile
from pathlib import Path


_test_state = tempfile.TemporaryDirectory(prefix="james-tests-")
_test_root = Path(_test_state.name)
_test_defaults = {
    "JAMES_DATA_DIR": str(_test_root / "data"),
    "JAMES_WIRELESS_SOC_DB": str(_test_root / "wireless-soc.sqlite3"),
    "QT_QPA_PLATFORM": "offscreen",
    "XDG_CACHE_HOME": str(_test_root / "cache"),
}
_added_defaults = {}
for name, value in _test_defaults.items():
    if name not in os.environ:
        os.environ[name] = value
        _added_defaults[name] = value


def pytest_unconfigure(config):
    for name, value in _added_defaults.items():
        if os.environ.get(name) == value:
            del os.environ[name]
    _test_state.cleanup()
