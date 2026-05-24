import unittest
from unittest.mock import patch, MagicMock
from james.core.orchestrator import Orchestrator

class TestOrchestrator(unittest.TestCase):
    @patch("james.core.orchestrator.Orchestrator._load_sudo_from_settings")
    @patch("james.core.orchestrator.NativeLayer")
    @patch("james.core.orchestrator.Orchestrator._load_loot")
    def setUp(self, mock_load_loot, mock_native_layer, mock_load_sudo):
        # Mock _load_loot to return an empty cache setup to avoid disk I/O
        mock_load_loot.return_value = {"cracked_keys": {}, "scan_history": [], "captured_hashes": []}
        # Initialize Orchestrator without heavy dependencies or disk writes
        self.orchestrator = Orchestrator()

        # We need to make sure we don't accidentally do disk writes in cache_cracked_key
        # We will mock `_save_loot` specifically for the test.

    @patch("james.core.orchestrator.datetime")
    def test_cache_cracked_key(self, mock_datetime):
        # Setup datetime mock
        mock_isoformat = "2023-10-10T12:00:00"
        mock_datetime.now.return_value.isoformat.return_value = mock_isoformat

        # Setup mock for _save_loot and _print
        self.orchestrator._save_loot = MagicMock()
        self.orchestrator._print = MagicMock()

        # Verify initial state
        self.assertEqual(self.orchestrator.loot_cache["cracked_keys"], {})

        # Test input
        bssid = "00:11:22:33:44:55"
        key = "supersecret"
        method = "wpa2"
        essid = "TestNetwork"

        # Call method
        self.orchestrator.cache_cracked_key(bssid, key, method, essid)

        # Verify loot_cache was updated correctly
        self.assertIn(bssid, self.orchestrator.loot_cache["cracked_keys"])
        entry = self.orchestrator.loot_cache["cracked_keys"][bssid]
        self.assertEqual(entry["key"], key)
        self.assertEqual(entry["method"], method)
        self.assertEqual(entry["essid"], essid)
        self.assertEqual(entry["cracked_at"], mock_isoformat)

        # Verify _save_loot was called
        self.orchestrator._save_loot.assert_called_once()

        # Verify _print was called
        self.orchestrator._print.assert_called_once_with(f"[LOOT] Cached key for {essid}: {key}")

    @patch("james.core.orchestrator.datetime")
    def test_cache_cracked_key_no_essid(self, mock_datetime):
        # Setup datetime mock
        mock_isoformat = "2023-10-10T12:00:00"
        mock_datetime.now.return_value.isoformat.return_value = mock_isoformat

        # Setup mock for _save_loot and _print
        self.orchestrator._save_loot = MagicMock()
        self.orchestrator._print = MagicMock()

        # Test input with default arguments (essid="", method="unknown")
        bssid = "AA:BB:CC:DD:EE:FF"
        key = "another_secret"

        # Call method
        self.orchestrator.cache_cracked_key(bssid, key)

        # Verify loot_cache was updated correctly
        self.assertIn(bssid, self.orchestrator.loot_cache["cracked_keys"])
        entry = self.orchestrator.loot_cache["cracked_keys"][bssid]
        self.assertEqual(entry["key"], key)
        self.assertEqual(entry["method"], "unknown")
        self.assertEqual(entry["essid"], "")
        self.assertEqual(entry["cracked_at"], mock_isoformat)

        # Verify _save_loot was called
        self.orchestrator._save_loot.assert_called_once()

        # Verify _print was called with bssid as fallback
        self.orchestrator._print.assert_called_once_with(f"[LOOT] Cached key for {bssid}: {key}")

if __name__ == "__main__":
    unittest.main()
