import unittest
import re
from unittest.mock import MagicMock, patch
from james.core.agent import Agent

class TestAgentSecurityFixes(unittest.TestCase):
    @patch('james.core.orchestrator.Orchestrator')
    def test_whois_injection(self, MockOrchestrator):
        orch = MockOrchestrator.return_value
        orch.layer = MagicMock()

        mock_result = MagicMock()
        mock_result.stdout = "Mocked whois output"
        orch.layer.run.return_value = mock_result

        agent = Agent(orch)

        # Test basic whois with safe domain
        m = MagicMock()
        m.group.return_value = "example.com"

        result = agent._do_whois(m, "whois example.com")
        self.assertIn("📋 WHOIS — example.com", result)

        # Test whois with injection payload
        m.group.return_value = "example.com; rm -rf /"

        result = agent._do_whois(m, "whois example.com; rm -rf /")

        # We'll assert that the command passed to run() is properly quoted
        call_args = orch.layer.run.call_args[0][0]
        self.assertIn("whois 'example.com; rm -rf /'", call_args)

    @patch('james.core.orchestrator.Orchestrator')
    def test_dns_enum_injection(self, MockOrchestrator):
        orch = MockOrchestrator.return_value
        orch.layer = MagicMock()

        mock_result = MagicMock()
        mock_result.stdout = "Mocked dig output"
        orch.layer.run.return_value = mock_result

        agent = Agent(orch)

        m = MagicMock()
        m.group.return_value = "example.com; rm -rf /"

        result = agent._do_dns_enum(m, "dns example.com; rm -rf /")

        call_args = orch.layer.run.call_args[0][0]
        self.assertIn("'example.com; rm -rf /'", call_args)

    @patch('james.core.orchestrator.Orchestrator')
    def test_sniff_injection(self, MockOrchestrator):
        orch = MockOrchestrator.return_value
        orch.layer = MagicMock()
        mock_result = MagicMock()
        mock_result.stdout = "Mocked tcpdump output"
        orch.layer.run.return_value = mock_result

        agent = Agent(orch)

        m = MagicMock()
        m.group.return_value = "wlan0; rm -rf /"

        agent._do_sniff(m, "sniff wlan0; rm -rf /")

        call_args = orch.layer.run.call_args[0][0]
        self.assertIn("'wlan0; rm -rf /'", call_args)

if __name__ == '__main__':
    unittest.main()
