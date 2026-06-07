import unittest
from unittest.mock import patch, MagicMock
from james.utils.net import get_local_ip

class TestNetUtils(unittest.TestCase):
    @patch('james.utils.net.socket.socket')
    def test_get_local_ip_success(self, mock_socket):
        # Setup mock socket instance
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.getsockname.return_value = ("192.168.1.100", 54321)

        # Call function
        ip = get_local_ip()

        # Assertions
        self.assertEqual(ip, "192.168.1.100")
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 80))

    @patch('james.utils.net.socket.socket')
    def test_get_local_ip_exception(self, mock_socket):
        # Setup mock socket to raise an exception on connect
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.connect.side_effect = Exception("Network error")

        # Call function
        ip = get_local_ip()

        # Assertions
        self.assertEqual(ip, "127.0.0.1")
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 80))

if __name__ == "__main__":
    unittest.main()
