import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    @patch('james.remote.gui_remote.get_local_ip')
    def test_url(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "192.168.1.100"
        remote = GUIRemote()

        expected_url = f"http://192.168.1.100:{GUIRemote.WEB_PORT}/vnc.html"
        self.assertEqual(remote.url, expected_url)
        mock_get_local_ip.assert_called_once()

    @patch('james.remote.gui_remote.get_local_ip')
    def test_vnc_url(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "192.168.1.100"
        remote = GUIRemote()

        expected_url = f"192.168.1.100:{GUIRemote.VNC_PORT}"
        self.assertEqual(remote.vnc_url, expected_url)
        mock_get_local_ip.assert_called_once()

if __name__ == '__main__':
    unittest.main()
