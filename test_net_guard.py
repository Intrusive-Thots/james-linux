import unittest
from unittest.mock import patch
from james.core.net_guard import NetworkGuard, ActiveConnection

class TestNetworkGuard(unittest.TestCase):

    @patch('james.core.net_guard.subprocess.run')
    def test_detect_via_nmcli_file_not_found(self, mock_subprocess_run):
        mock_subprocess_run.side_effect = FileNotFoundError()
        guard = NetworkGuard()
        conn = guard._detect_via_nmcli()

        self.assertIsInstance(conn, ActiveConnection)
        self.assertEqual(conn.interface, "")
        self.assertEqual(conn.ssid, "")
        self.assertEqual(conn.bssid, "")
        self.assertEqual(conn.gateway, "")
        self.assertEqual(conn.ip, "")
        self.assertFalse(conn.is_wifi)

if __name__ == '__main__':
    unittest.main()
