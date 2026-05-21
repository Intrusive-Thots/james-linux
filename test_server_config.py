import unittest
import json
import tempfile
from pathlib import Path
import james.server.config as config_mod


class TestServerConfig(unittest.TestCase):
    def setUp(self):
        # We must avoid mocking by using actual disk files
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dummy_dir = Path(self.tmpdir.name)
        self.dummy_file = self.dummy_dir / "config.json"

        # Save the original CONFIG_PATH
        self.orig_config_path = config_mod.CONFIG_PATH
        # Replace the global module variable to point to our real temp file
        config_mod.CONFIG_PATH = self.dummy_file

    def tearDown(self):
        # Restore the original CONFIG_PATH
        config_mod.CONFIG_PATH = self.orig_config_path
        self.tmpdir.cleanup()

    def test_load_config_from_file(self):
        """Test loading configuration from an actual JSON file."""
        dummy_data = {
            "host": "127.0.0.1",
            "port": 9999,
            "api_key": "dummy_api_key",
            "tls_enabled": False,
            "jwt_secret": "dummy_jwt_secret",
        }

        with open(self.dummy_file, "w") as f:
            json.dump(dummy_data, f)

        cfg = config_mod.load_config()

        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.port, 9999)
        self.assertEqual(cfg.api_key, "dummy_api_key")
        self.assertFalse(cfg.tls_enabled)
        self.assertEqual(cfg.jwt_secret, "dummy_jwt_secret")

    def test_load_config_defaults(self):
        """Test loading defaults when the file does not exist."""
        if self.dummy_file.exists():
            self.dummy_file.unlink()

        cfg = config_mod.load_config()
        self.assertEqual(cfg.host, "0.0.0.0")
        self.assertEqual(cfg.port, 8443)
        self.assertTrue(cfg.tls_enabled)
        self.assertTrue(
            len(cfg.jwt_secret) > 0
        )  # auto-generated secrets.token_hex(32)


if __name__ == "__main__":
    unittest.main()
