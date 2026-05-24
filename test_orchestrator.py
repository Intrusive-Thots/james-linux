import unittest
import tempfile
import json
from pathlib import Path
from james.core.orchestrator import Orchestrator


class TestOrchestratorLoot(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.loot_dir = Path(self.tmpdir.name)

        self.orchestrator = Orchestrator()
        self.orchestrator.LOOT_DIR = self.loot_dir
        # Re-initialize loot_cache since __init__ loaded it from default dir
        self.orchestrator.loot_cache = {
            "cracked_keys": {},
            "scan_history": [],
            "captured_hashes": [],
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cache_cracked_key(self):
        bssid = "00:11:22:33:44:55"
        key = "supersecret"
        method = "test_method"
        essid = "TestSSID"

        self.orchestrator.cache_cracked_key(bssid, key, method, essid)

        # Verify memory cache is updated
        self.assertIn("cracked_keys", self.orchestrator.loot_cache)
        self.assertIn(bssid, self.orchestrator.loot_cache["cracked_keys"])
        cached_entry = self.orchestrator.loot_cache["cracked_keys"][bssid]
        self.assertEqual(cached_entry["key"], key)
        self.assertEqual(cached_entry["method"], method)
        self.assertEqual(cached_entry["essid"], essid)
        self.assertIn("cracked_at", cached_entry)

        # Verify disk persistence via _save_loot
        loot_file = self.loot_dir / "results.json"
        self.assertTrue(loot_file.exists())

        with open(loot_file, "r") as f:
            disk_data = json.load(f)

        self.assertIn("cracked_keys", disk_data)
        self.assertIn(bssid, disk_data["cracked_keys"])
        self.assertEqual(disk_data["cracked_keys"][bssid]["key"], key)
        self.assertEqual(disk_data["cracked_keys"][bssid]["method"], method)
        self.assertEqual(disk_data["cracked_keys"][bssid]["essid"], essid)
        self.assertIn("cracked_at", disk_data["cracked_keys"][bssid])


if __name__ == "__main__":
    unittest.main()
