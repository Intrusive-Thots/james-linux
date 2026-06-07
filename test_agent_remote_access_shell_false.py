import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.abspath("."))

from james.core.agent import Agent

class TestAgentRemoteAccess(unittest.TestCase):
    @patch("subprocess.run")
    @patch("james.utils.net.get_local_ip", return_value="192.168.1.100")
    def test_do_remote_access_success(self, mock_get_ip, mock_run):
        def side_effect(*args, **kwargs):
            if kwargs.get("shell", True):
                raise ValueError("shell=True is not allowed")
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result

        mock_run.side_effect = side_effect

        with patch.object(Agent, '__init__', lambda x: None):
            agent = Agent()
            agent.context = {}
            output = agent._do_remote_access(MagicMock(), "")

        self.assertIn("SSH service enabled and running", output)
        self.assertIn("xRDP enabled", output)

if __name__ == "__main__":
    unittest.main()
