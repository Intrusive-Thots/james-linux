import unittest
from unittest.mock import MagicMock, patch
import re
from james.core.agent import Agent

class TestAgentSecurity(unittest.TestCase):
    def setUp(self):
        # Create a mock orchestrator with a mock layer
        self.mock_orch = MagicMock()
        self.mock_layer = MagicMock()
        self.mock_orch.layer = self.mock_layer

        # Agent init needs some config, we can mock it or provide minimal ones
        self.agent = Agent(self.mock_orch)

    def test_do_whois_command_injection_prevention(self):
        """Test that _do_whois sanitizes input to prevent command injection."""
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.stdout = "Mock WHOIS data"
        self.mock_layer.run.return_value = mock_result

        # Create a malicious input
        malicious_domain = "example.com; rm -rf /"

        # Mock regex match object
        mock_match = MagicMock()
        mock_match.group.return_value = malicious_domain

        # Call the method
        self.agent._do_whois(mock_match, f"whois {malicious_domain}")

        # Verify the command executed is properly sanitized
        # shlex.quote handles spaces and special characters
        # Expected: "whois 'example.com; rm -rf /' | head -40" (in bash/sh)
        self.mock_layer.run.assert_called_once()
        called_cmd = self.mock_layer.run.call_args[0][0]

        self.assertIn("whois ", called_cmd)
        self.assertIn("'example.com; rm -rf /'", called_cmd)
        self.assertNotIn("whois example.com;", called_cmd)

    def test_do_dns_enum_command_injection_prevention(self):
        """Test that _do_dns_enum sanitizes input to prevent command injection."""
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.stdout = "Mock DNS data"
        self.mock_layer.run.return_value = mock_result

        # Create a malicious input
        malicious_domain = "example.com $(reboot)"

        # Mock regex match object
        mock_match = MagicMock()
        mock_match.group.return_value = malicious_domain

        # Call the method
        self.agent._do_dns_enum(mock_match, f"dns {malicious_domain}")

        # Verify the command executed is properly sanitized
        self.mock_layer.run.assert_called_once()
        called_cmd = self.mock_layer.run.call_args[0][0]

        self.assertIn("dig ", called_cmd)
        self.assertIn("'example.com $(reboot)'", called_cmd)

        # Verify we didn't just inject the raw string
        self.assertNotIn("dig example.com $(reboot)", called_cmd)

if __name__ == "__main__":
    unittest.main()
