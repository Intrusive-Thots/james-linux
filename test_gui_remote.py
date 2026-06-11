import unittest
from unittest.mock import patch
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    @patch('james.remote.gui_remote.get_local_ip')
    def test_url_property(self, mock_get_local_ip):
        mock_get_local_ip.return_value = "192.168.1.100"
        gui_remote = GUIRemote()

        self.assertEqual(gui_remote.url, "http://192.168.1.100:6080/vnc.html")
        mock_get_local_ip.assert_called_once()

if __name__ == '__main__':
    unittest.main()
