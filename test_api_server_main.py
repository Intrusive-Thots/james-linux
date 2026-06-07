import unittest
from unittest.mock import patch
import os
import sys

from james.api.server import main

class TestApiServerMain(unittest.TestCase):
    @patch('james.api.server.uvicorn.run')
    def test_main_default_port(self, mock_run):
        """Test that main() correctly uses the default port 8745 when JAMES_API_PORT is unset."""
        # Ensure environment variable is not set
        with patch.dict(os.environ, clear=True):
            main()

        mock_run.assert_called_once_with(
            "james.api.server:app",
            host="0.0.0.0",
            port=8745,
            log_level="info",
            reload=False,
        )

    @patch('james.api.server.uvicorn.run')
    def test_main_custom_port(self, mock_run):
        """Test that main() correctly reads from the JAMES_API_PORT environment variable."""
        with patch.dict(os.environ, {'JAMES_API_PORT': '9000'}):
            main()

        mock_run.assert_called_once_with(
            "james.api.server:app",
            host="0.0.0.0",
            port=9000,
            log_level="info",
            reload=False,
        )

    @patch('james.api.server.uvicorn.run')
    def test_main_invalid_port(self, mock_run):
        """Test that main() raises ValueError when JAMES_API_PORT is non-numeric."""
        with patch.dict(os.environ, {'JAMES_API_PORT': 'invalid_port'}):
            with self.assertRaises(ValueError):
                main()

        # Ensure uvicorn.run is not called if port parsing fails
        mock_run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
