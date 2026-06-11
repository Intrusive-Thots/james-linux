import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    @patch('james.remote.gui_remote.get_local_ip')
    def test_url_property(self, mock_get_local_ip):
        mock_get_local_ip.return_value = '192.168.1.100'
        remote = GUIRemote()

        url = remote.url

        self.assertEqual(url, f"http://192.168.1.100:{GUIRemote.WEB_PORT}/vnc.html")
        mock_get_local_ip.assert_called_once()

    @patch('james.remote.gui_remote.get_local_ip')
    def test_vnc_url_property(self, mock_get_local_ip):
        mock_get_local_ip.return_value = '192.168.1.100'
        remote = GUIRemote()

        vnc_url = remote.vnc_url

        self.assertEqual(vnc_url, f"192.168.1.100:{GUIRemote.VNC_PORT}")
        mock_get_local_ip.assert_called_once()

if __name__ == '__main__':
    unittest.main()
