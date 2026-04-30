import unittest
from unittest.mock import MagicMock
from james.tools.parrot import AircrackSuite

class TestAircrackSuite(unittest.TestCase):

    def setUp(self):
        self.mock_layer = MagicMock()
        self.suite = AircrackSuite(self.mock_layer)

    def test_start_monitor_mode(self):
        self.mock_layer.execute.return_value = (0, "mac80211 monitor mode vif enabled for [phy0]wlan0mon", "")

        result = self.suite.start_monitor_mode("wlan0")

        self.assertTrue(result["success"])
        self.assertEqual(result["monitor_interface"], "wlan0mon")
        self.mock_layer.execute.assert_called_with(["airmon-ng", "start", "wlan0"], require_root=True)

    def test_stop_monitor_mode(self):
        self.mock_layer.execute.return_value = (0, "", "")

        result = self.suite.stop_monitor_mode("wlan0mon")

        self.assertTrue(result["success"])
        self.mock_layer.execute.assert_called_with(["airmon-ng", "stop", "wlan0mon"], require_root=True)

    def test_scan_networks(self):
        # Mock some dummy airodump-ng output
        self.mock_layer.execute.return_value = (0, "BSSID              PWR  Beacons    #Data, #/s  CH   MB   ENC CIPHER  AUTH ESSID\n\n AA:BB:CC:DD:EE:FF  -40       10        0    0   6   54e  WPA2 CCMP   PSK  MyNetwork", "")

        result = self.suite.scan_networks("wlan0mon", duration=1)

        self.assertEqual(result["interface"], "wlan0mon")
        self.assertTrue(len(result["networks_found_raw"]) > 0)
        self.assertIn("AA:BB:CC:DD:EE:FF", result["networks_found_raw"][0])

if __name__ == '__main__':
    unittest.main()
