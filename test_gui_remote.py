import unittest
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    def test_is_running(self):
        """Test that is_running returns the current running state."""
        remote = GUIRemote()
        # Default state
        self.assertFalse(remote.is_running())

        # Modify state to True
        remote.running = True
        self.assertTrue(remote.is_running())

        # Modify state back to False
        remote.running = False
        self.assertFalse(remote.is_running())

if __name__ == '__main__':
    unittest.main()
