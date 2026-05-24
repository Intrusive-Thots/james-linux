import tempfile
import json
from pathlib import Path
from james.core.orchestrator import Orchestrator

def test_cache_cracked_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator()

        # Override LOOT_DIR for this instance
        orch.LOOT_DIR = Path(tmpdir)

        # Reset loot_cache to a clean state for the test
        orch.loot_cache = {"cracked_keys": {}, "scan_history": [], "captured_hashes": []}

        bssid = "AA:BB:CC:DD:EE:FF"
        key = "supersecret"

        # Action
        orch.cache_cracked_key(bssid_or_id=bssid, key=key, method="wpa2", essid="TestNet")

        # Verify in memory
        assert bssid in orch.loot_cache["cracked_keys"]
        assert orch.loot_cache["cracked_keys"][bssid]["key"] == key
        assert orch.loot_cache["cracked_keys"][bssid]["method"] == "wpa2"
        assert orch.loot_cache["cracked_keys"][bssid]["essid"] == "TestNet"

        # Verify on disk
        results_file = Path(tmpdir) / "results.json"
        assert results_file.exists(), "results.json should be created"

        with open(results_file, "r") as f:
            data = json.load(f)

        assert "cracked_keys" in data
        assert bssid in data["cracked_keys"]
        assert data["cracked_keys"][bssid]["key"] == key

if __name__ == "__main__":
    test_cache_cracked_key()
    print("Test passed.")
