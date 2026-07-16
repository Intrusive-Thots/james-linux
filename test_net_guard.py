import unittest
from unittest.mock import patch
from james.core.net_guard import NetworkGuard, ActiveConnection

class TestNetworkGuard(unittest.TestCase):

    @patch.object(NetworkGuard, 'get_active_connection')
    def test_check_deauth_safe_normalization(self, mock_get_active_connection):
        guard = NetworkGuard(enabled=True)

        mock_conn = ActiveConnection()
        mock_conn.bssid = "aa:bb:cc:dd:ee:ff"
        mock_conn.ssid = "MyHomeNetwork"
        mock_conn.interface = "wlan0"
        mock_get_active_connection.return_value = mock_conn

        # 1. Exact match
        is_safe, reason = guard.check_deauth_safe("aa:bb:cc:dd:ee:ff")
        self.assertFalse(is_safe)
        self.assertIn("BLOCKED", reason)

        # 2. Case difference
        is_safe, reason = guard.check_deauth_safe("AA:BB:CC:DD:EE:FF")
        self.assertFalse(is_safe)
        self.assertIn("BLOCKED", reason)

        # 3. Dashes instead of colons
        is_safe, reason = guard.check_deauth_safe("AA-BB-CC-DD-EE-FF")
        self.assertFalse(is_safe)
        self.assertIn("BLOCKED", reason)

        # 4. Leading/trailing whitespace
        is_safe, reason = guard.check_deauth_safe("  aa:bb:cc:dd:ee:ff  ")
        self.assertFalse(is_safe)
        self.assertIn("BLOCKED", reason)

        # 5. Different BSSID
        is_safe, reason = guard.check_deauth_safe("00:11:22:33:44:55")
        self.assertTrue(is_safe)
        self.assertEqual(reason, "")

if __name__ == '__main__':
    unittest.main()
