import unittest
from unittest.mock import patch, MagicMock
from james.utils.net import get_local_ip

class TestNet(unittest.TestCase):

    @patch('james.utils.net.socket.socket')
    def test_get_local_ip_success(self, mock_socket):
        mock_instance = MagicMock()
        mock_instance.getsockname.return_value = ("192.168.1.100", 54321)
        mock_socket.return_value.__enter__.return_value = mock_instance

        ip = get_local_ip()

        self.assertEqual(ip, "192.168.1.100")
        mock_instance.connect.assert_called_with(("8.8.8.8", 80))
        mock_instance.getsockname.assert_called_once()

    @patch('james.utils.net.socket.socket')
    def test_get_local_ip_fallback(self, mock_socket):
        mock_socket.side_effect = Exception("Network is unreachable")

        ip = get_local_ip()

        self.assertEqual(ip, "127.0.0.1")

if __name__ == '__main__':
    unittest.main()
