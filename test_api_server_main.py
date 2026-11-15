import os
import unittest
from unittest.mock import patch

from james.api.server import main


class TestApiServerMain(unittest.TestCase):
    @patch("james.api.server.uvicorn.run")
    def test_main_default_port(self, mock_run):
        with patch.dict(os.environ, {}, clear=True):
            main()
        mock_run.assert_called_once_with(
            "james.api.server:app", host="127.0.0.1", port=8745,
            log_level="info", reload=False,
            ssl_certfile=None, ssl_keyfile=None,
        )

    @patch("james.api.server.uvicorn.run")
    def test_main_custom_port(self, mock_run):
        with patch.dict(os.environ, {"JAMES_API_PORT": "9000"}, clear=True):
            main()
        mock_run.assert_called_once_with(
            "james.api.server:app", host="127.0.0.1", port=9000,
            log_level="info", reload=False,
            ssl_certfile=None, ssl_keyfile=None,
        )

    @patch("james.api.server.uvicorn.run")
    def test_main_invalid_port(self, mock_run):
        with patch.dict(os.environ, {"JAMES_API_PORT": "invalid_port"}, clear=True):
            with self.assertRaises(ValueError):
                main()
        mock_run.assert_not_called()

    @patch("james.api.server.uvicorn.run")
    def test_remote_binding_requires_token_and_tls(self, mock_run):
        remote_env = {"JAMES_API_HOST": "0.0.0.0"}
        credentials = {
            "JAMES_API_TOKEN": "test-only-token",
            "JAMES_API_SSL_CERTFILE": "/tmp/test-cert.pem",
            "JAMES_API_SSL_KEYFILE": "/tmp/test-key.pem",
        }
        for missing in credentials:
            with self.subTest(missing=missing):
                values = {**remote_env, **credentials}
                del values[missing]
                with patch.dict(os.environ, values, clear=True):
                    with self.assertRaisesRegex(SystemExit, "Refusing remote API binding"):
                        main()
        mock_run.assert_not_called()

    @patch("james.api.server.uvicorn.run")
    def test_explicit_remote_mode_passes_tls_configuration(self, mock_run):
        with patch.dict(os.environ, {
            "JAMES_API_HOST": "0.0.0.0",
            "JAMES_API_TOKEN": "test-only-token",
            "JAMES_API_SSL_CERTFILE": "/tmp/test-cert.pem",
            "JAMES_API_SSL_KEYFILE": "/tmp/test-key.pem",
        }, clear=True):
            main()
        mock_run.assert_called_once_with(
            "james.api.server:app", host="0.0.0.0", port=8745,
            log_level="info", reload=False,
            ssl_certfile="/tmp/test-cert.pem", ssl_keyfile="/tmp/test-key.pem",
        )


if __name__ == "__main__":
    unittest.main()
