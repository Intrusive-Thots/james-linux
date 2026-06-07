import unittest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import keyring

from james.core.orchestrator import Orchestrator

class TestSecurityPassword(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()

    @patch('keyring.get_password')
    @patch('pathlib.Path.exists')
    def test_load_sudo_from_keyring(self, mock_exists, mock_get_password):
        mock_get_password.return_value = "secret_pass"
        mock_exists.return_value = False

        self.orchestrator._load_sudo_from_settings()

        self.assertEqual(os.environ.get("JAMES_SUDO_PASS"), "secret_pass")
        mock_get_password.assert_called_once_with("james", "sudo_password")

    @patch('keyring.get_password')
    @patch('keyring.set_password')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.write_text')
    def test_migration_from_plaintext(self, mock_write_text, mock_read_text, mock_exists, mock_set_password, mock_get_password):
        mock_get_password.return_value = None
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps({"sudo_password": "plaintext_pass"})

        self.orchestrator._load_sudo_from_settings()

        mock_set_password.assert_called_once_with("james", "sudo_password", "plaintext_pass")
        self.assertEqual(os.environ.get("JAMES_SUDO_PASS"), "plaintext_pass")

        # Verify plaintext removal
        written_data = json.loads(mock_write_text.call_args[0][0])
        self.assertNotIn("sudo_password", written_data)

if __name__ == '__main__':
    unittest.main()
