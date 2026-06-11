import unittest
from james.layers.native import NativeLayer

class TestNativeLayer(unittest.TestCase):
    def test_check_tool_installed(self):
        layer = NativeLayer()
        self.assertTrue(layer.check_tool("ls"))

    def test_check_tool_not_installed(self):
        layer = NativeLayer()
        self.assertFalse(layer.check_tool("nonexistent_tool_123456789"))

if __name__ == '__main__':
    unittest.main()
