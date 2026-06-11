import os
import sys
import unittest
from unittest.mock import MagicMock

# Add current directory to path
sys.path.insert(0, os.path.abspath("."))

from james.layers.native import NativeLayer, CommandResult  # noqa: E402


class TestNativeLayer(unittest.TestCase):
    def test_check_tool_success_and_cache(self):
        layer = NativeLayer()
        # Mock run method
        res = CommandResult("which ls", 0, "/usr/bin/ls", "")
        layer.run = MagicMock(return_value=res)

        # Test tool is reported installed and run is called
        self.assertTrue(layer.check_tool("ls"))
        layer.run.assert_called_once_with("which ls", timeout=5)

        # Test cache works by calling again and ensuring run is not called
        layer.run.reset_mock()
        self.assertTrue(layer.check_tool("ls"))
        layer.run.assert_not_called()

    def test_check_tool_failure_and_cache(self):
        layer = NativeLayer()
        # Mock run method
        res = CommandResult("which no_tool", 1, "", "")
        layer.run = MagicMock(return_value=res)

        # Test invalid tool returns False
        self.assertFalse(layer.check_tool("no_tool"))
        layer.run.assert_called_once_with("which no_tool", timeout=5)

        # Test negative cache works
        layer.run.reset_mock()
        self.assertFalse(layer.check_tool("no_tool"))
        layer.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
