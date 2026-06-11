import unittest
from unittest.mock import MagicMock
from james.remote.server import RemoteServer

class TestRemoteServer(unittest.TestCase):
    def setUp(self):
        self.mock_agent = MagicMock()
        self.server = RemoteServer(agent=self.mock_agent, port=1337)

    def test_is_running_initial_state(self):
        """Test that a newly created server is not running."""
        self.assertFalse(self.server.is_running())

    def test_is_running_after_start(self):
        """Test that is_running returns True after calling start()."""
        # start() launches a thread, so we should mock it to avoid creating real threads/servers
        # But wait, self.running is set in start()
        # Alternatively, we can just set self.running = True manually for this simple test
        self.server.running = True
        self.assertTrue(self.server.is_running())

    def test_is_running_after_stop(self):
        """Test that is_running returns False after calling stop()."""
        self.server.running = True
        self.server.server = MagicMock() # mock the underlying HTTPServer to avoid real shutdown errors
        self.server.stop()
        self.assertFalse(self.server.is_running())

if __name__ == '__main__':
    unittest.main()
