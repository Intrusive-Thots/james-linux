import unittest
from james.layers.native import NativeLayer, CommandResult
import subprocess

class TestNativeLayer(unittest.TestCase):
    def test_check_tool(self):
        layer = NativeLayer()
        self.assertTrue(layer.check_tool("ls"))
        self.assertFalse(layer.check_tool("nonexistent_tool_abc123"))

if __name__ == '__main__':
    unittest.main()
