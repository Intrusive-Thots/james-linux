import unittest
from unittest.mock import MagicMock
from james.remote.server import RemoteServer

class TestRemoteServer(unittest.TestCase):
    def test_is_running_initial_state(self):
        """Test that is_running returns False initially."""
        mock_agent = MagicMock()
        server = RemoteServer(mock_agent)
        self.assertFalse(server.is_running())
        self.assertFalse(server.running)

    def test_is_running_reflects_running_state(self):
        """Test that is_running accurately reflects the running state."""
        mock_agent = MagicMock()
        server = RemoteServer(mock_agent)

        # Simulate server started
        server.running = True
        self.assertTrue(server.is_running())

        # Simulate server stopped
        server.running = False
        self.assertFalse(server.is_running())

if __name__ == '__main__':
    unittest.main()
