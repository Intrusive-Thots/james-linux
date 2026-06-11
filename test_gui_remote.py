import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote


class TestGUIRemote(unittest.TestCase):
    @patch("james.remote.gui_remote.get_local_ip")
    def test_vnc_url(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "192.168.1.100"
        remote = GUIRemote()
        self.assertEqual(remote.vnc_url, "192.168.1.100:5900")

    @patch("james.remote.gui_remote.get_local_ip")
    def test_vnc_url_localhost(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "127.0.0.1"
        remote = GUIRemote()
        self.assertEqual(remote.vnc_url, "127.0.0.1:5900")


if __name__ == "__main__":
    unittest.main()
