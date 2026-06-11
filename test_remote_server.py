import unittest
from unittest.mock import patch, MagicMock

from james.remote.server import RemoteServer

class TestRemoteServer(unittest.TestCase):
    @patch('james.remote.server.get_local_ip')
    def test_url_property(self, mock_get_local_ip):
        # Setup mock
        mock_get_local_ip.return_value = '192.168.1.100'

        # Initialize RemoteServer with a dummy agent and specific port
        dummy_agent = MagicMock()
        server = RemoteServer(agent=dummy_agent, port=8080)

        # Verify the url property returns the expected formatted string
        expected_url = 'http://192.168.1.100:8080/'
        self.assertEqual(server.url, expected_url)

        # Verify get_local_ip was called
        mock_get_local_ip.assert_called_once()

if __name__ == '__main__':
    unittest.main()
