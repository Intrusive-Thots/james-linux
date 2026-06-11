import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    @patch('james.remote.gui_remote.get_local_ip')
    def test_vnc_url(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "192.168.1.10"

        gui_remote = GUIRemote()
        # Verify the vnc_url is formatted correctly
        self.assertEqual(gui_remote.vnc_url, "192.168.1.10:5900")

if __name__ == '__main__':
    unittest.main()
