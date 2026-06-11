import unittest
from unittest.mock import patch, MagicMock

from james.remote.server import RemoteServer

class TestRemoteServer(unittest.TestCase):
    @patch("james.remote.server.get_local_ip", return_value="192.168.1.50")
    def test_url_property(self, mock_get_local_ip):
        # Create a mock agent if needed
        mock_agent = MagicMock()

        # Instantiate RemoteServer with port 8080
        server = RemoteServer(agent=mock_agent, port=8080)

        # Assert url property
        self.assertEqual(server.url, "http://192.168.1.50:8080/")

        # Verify the mock was called
        mock_get_local_ip.assert_called_once()

if __name__ == "__main__":
    unittest.main()
