import unittest
from james.core.sedge import (
    SelfEvolvingAgent,
    build_parrot_wifi_graph,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeParrotMapping(unittest.TestCase):
    """
    Tests the specific domain mapping of the SEDGE system to the Parrot WiFi application.
    Verifies that the factory function `build_parrot_wifi_graph` creates a valid living ecosystem
    and that an agent can navigate through the expected pipeline.
    """

    def setUp(self):
        # Create the domain-specific graph for Parrot WiFi
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)

    def test_parrot_wifi_agent_navigation_pipeline(self):
        """
        Simulates an agent traversing the Parrot WiFi graph to ensure all domain-specific
        states, actions, and transitions are correctly connected and accessible.
        """
        # Ensure agent starts at STATE_START
        self.assertEqual(self.agent.current_node, STATE_START)

        # Step 1: START -> NETWORK_DISCOVERY
        node = self.agent.step()
        self.assertEqual(node, STATE_NETWORK_DISCOVERY)

        # Step 2: NETWORK_DISCOVERY -> PASSIVE_SCAN
        node = self.agent.step()
        self.assertEqual(node, ACTION_PASSIVE_SCAN)

        # Step 3: PASSIVE_SCAN -> TARGET_ANALYSIS
        node = self.agent.step()
        self.assertEqual(node, STATE_TARGET_ANALYSIS)

        # Step 4: TARGET_ANALYSIS -> (HANDSHAKE_CAPTURE or DEAUTH_TEST)
        node = self.agent.step()
        self.assertIn(node, [ACTION_HANDSHAKE_CAPTURE, ACTION_DEAUTH_TEST])

        # Step 5: (Action) -> SECURITY_PROFILING
        node = self.agent.step()
        self.assertEqual(node, STATE_SECURITY_PROFILING)

        # Step 6: SECURITY_PROFILING -> EVIL_TWIN_SIMULATION
        node = self.agent.step()
        self.assertEqual(node, ACTION_EVIL_TWIN_SIMULATION)

        # Step 7: EVIL_TWIN_SIMULATION -> halt (end of pipeline)
        node = self.agent.step()
        self.assertEqual(node, "halt")

        # Verify the recorded path sequence
        expected_start_sequence = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
        ]

        # Verify the first few states of the current path match the expected pipeline
        self.assertEqual(self.agent.current_path[:4], expected_start_sequence)

        # Provide feedback and verify episode resets
        self.agent.feedback(OUTCOME_SUCCESS)
        self.assertEqual(self.agent.current_node, STATE_START)
        self.assertEqual(self.agent.current_path, [STATE_START])


if __name__ == "__main__":
    unittest.main()
