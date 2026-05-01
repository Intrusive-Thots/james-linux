import unittest
from james.tools.parrot import Nmap, AircrackSuite, Hashcat, John
from james.layers.native import NativeLayer, CommandResult

class MockNativeLayer(NativeLayer):
    def __init__(self):
        super().__init__()
        self.mock_result = CommandResult("mock", 0, "", "")
    def run(self, *args, **kwargs):
        return self.mock_result

class TestTools(unittest.TestCase):
    def setUp(self):
        self.layer = MockNativeLayer()
        self.nmap = Nmap(self.layer)
        self.aircrack = AircrackSuite(self.layer)

    def test_nmap_quick_scan(self):
        self.layer.mock_result = CommandResult("nmap mock", 0, "<?xml version='1.0'?><nmaprun></nmaprun>", "")
        res = self.nmap.quick_scan("127.0.0.1")
        self.assertIn("hosts", res)

if __name__ == '__main__':
    unittest.main()
