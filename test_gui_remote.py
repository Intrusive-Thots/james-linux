import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote

class TestGUIRemoteProperties(unittest.TestCase):
    @patch("james.remote.gui_remote.get_local_ip")
    def test_vnc_url(self, mock_get_local_ip):
        """Test that vnc_url correctly formats the IP and port."""
        mock_get_local_ip.return_value = "192.168.1.50"
        remote = GUIRemote()

        expected_url = f"192.168.1.50:{GUIRemote.VNC_PORT}"
        self.assertEqual(remote.vnc_url, expected_url)

    @patch("james.remote.gui_remote.get_local_ip")
    def test_url(self, mock_get_local_ip):
        """Test that url correctly formats the HTTP URL with IP and port."""
        mock_get_local_ip.return_value = "192.168.1.50"
        remote = GUIRemote()

        expected_url = f"http://192.168.1.50:{GUIRemote.WEB_PORT}/vnc.html"
        self.assertEqual(remote.url, expected_url)

if __name__ == "__main__":
    unittest.main()
