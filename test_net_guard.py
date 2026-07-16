import unittest
from unittest.mock import patch
from james.core.net_guard import NetworkGuard, ActiveConnection

class TestNetworkGuard(unittest.TestCase):
    def setUp(self):
        self.guard = NetworkGuard(enabled=True)

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_deauth_safe_blocks_own_bssid(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            ssid="MyWiFi",
            bssid="AA:BB:CC:DD:EE:FF",
            is_wifi=True
        )
        ok, reason = self.guard.check_deauth_safe("AA:BB:CC:DD:EE:FF")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", reason)
        self.assertIn("AA:BB:CC:DD:EE:FF", reason)

        # different case/format
        ok, reason = self.guard.check_deauth_safe("aa-bb-cc-dd-ee-ff")
        self.assertFalse(ok)

        # safe target
        ok, reason = self.guard.check_deauth_safe("11:22:33:44:55:66")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_monitor_safe_blocks_own_interface(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            is_wifi=True
        )
        ok, reason = self.guard.check_monitor_safe("wlan0")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", reason)
        self.assertIn("wlan0", reason)

        ok, reason = self.guard.check_monitor_safe("wlan1")
        self.assertTrue(ok)

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_evil_twin_safe(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            bssid="AA:BB:CC:DD:EE:FF",
            is_wifi=True
        )
        ok, reason = self.guard.check_evil_twin_safe("AA:BB:CC:DD:EE:FF")
        self.assertFalse(ok)

        ok, reason = self.guard.check_evil_twin_safe("11:22:33:44:55:66")
        self.assertTrue(ok)

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_check_kill_safe_warning(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            is_wifi=True
        )
        ok, reason = self.guard.check_check_kill_safe()
        self.assertTrue(ok)
        self.assertIn("WARNING", reason)
        self.assertIn("wlan0", reason)

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_mitm_safe(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="eth0",
            gateway="192.168.1.1",
            ip="192.168.1.10"
        )
        ok, reason = self.guard.check_mitm_safe("192.168.1.10", "192.168.1.2")
        self.assertFalse(ok)
        self.assertIn("BLOCKED", reason)

        ok, reason = self.guard.check_mitm_safe("192.168.1.20", "192.168.1.1")
        self.assertTrue(ok)
        self.assertIn("NOTE", reason)
        self.assertIn("YOUR default gateway", reason)

        ok, reason = self.guard.check_mitm_safe("192.168.1.20", "192.168.1.2")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_deauth_safe_allows_if_no_bssid(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            bssid="",
            is_wifi=True
        )
        ok, reason = self.guard.check_deauth_safe("AA:BB:CC:DD:EE:FF")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_monitor_safe_allows_if_no_interface(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="",
        )
        ok, reason = self.guard.check_monitor_safe("wlan0")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_check_check_kill_safe_allows_if_not_wifi(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="eth0",
            is_wifi=False
        )
        ok, reason = self.guard.check_check_kill_safe()
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    @patch('james.core.net_guard.NetworkGuard.get_active_connection')
    def test_get_status(self, mock_get_conn):
        mock_get_conn.return_value = ActiveConnection(
            interface="wlan0",
            is_wifi=True,
            ssid="TestNet",
            bssid="11:22:33:44:55:66",
            gateway="192.168.1.1",
            ip="192.168.1.10"
        )
        status = self.guard.get_status()
        self.assertTrue(status["enabled"])
        self.assertTrue(status["connected"])
        self.assertEqual(status["interface"], "wlan0")
        self.assertTrue(status["is_wifi"])
        self.assertEqual(status["ssid"], "TestNet")
        self.assertEqual(status["bssid"], "11:22:33:44:55:66")
        self.assertEqual(status["gateway"], "192.168.1.1")
        self.assertEqual(status["ip"], "192.168.1.10")

    def test_disabled_guard(self):
        guard = NetworkGuard(enabled=False)
        self.assertTrue(guard.check_deauth_safe("AA:BB:CC:DD:EE:FF")[0])
        self.assertTrue(guard.check_monitor_safe("wlan0")[0])
        self.assertTrue(guard.check_evil_twin_safe("AA:BB:CC:DD:EE:FF")[0])
        self.assertTrue(guard.check_check_kill_safe()[0])
        self.assertTrue(guard.check_mitm_safe("192.168.1.10", "192.168.1.1")[0])

if __name__ == '__main__':
    unittest.main()
