import unittest
from james.core.sedge import build_parrot_wifi_graph, SelfEvolvingAgent
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_PASSIVE_SCAN,
    STATE_SECURITY_PROFILING,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeParrotEvolution(unittest.TestCase):
    """
    Test that the SEDGE graph naturally converges toward optimal attack/analysis
    pipelines and balances exploration vs exploitation in the Parrot WiFi System.
    """

    def setUp(self):
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)

    def test_real_evolution_behavior_and_exploration(self):
        """
        Simulate 1000 iterations to verify:
        - Graph converges toward optimal attack/analysis pipelines
        - Unstable techniques decay automatically
        - High-yield workflows become dominant paths
        - The system balances exploration vs exploitation
        """
        iterations = 1000
        handshake_selections = 0
        deauth_selections = 0

        for _ in range(iterations):
            # Run the agent until it hits an action or halts
            outcome = OUTCOME_PARTIAL  # Default

            while True:
                node = self.agent.step()
                if node == "halt":
                    break

                # We map specific outcomes to specific actions
                if node == ACTION_HANDSHAKE_CAPTURE:
                    # High-yield optimal path
                    outcome = OUTCOME_SUCCESS
                    handshake_selections += 1
                    break
                elif node == ACTION_DEAUTH_TEST:
                    # Unstable technique that should decay
                    outcome = OUTCOME_FAILURE
                    deauth_selections += 1
                    break

            # Feedback loop
            self.agent.feedback(outcome)

        # Retrieve the edges from TARGET_ANALYSIS to compare weights
        target_analysis_edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next(
            e
            for e in target_analysis_edges
            if e.to_node == ACTION_HANDSHAKE_CAPTURE
        )
        deauth_edge = next(
            e for e in target_analysis_edges if e.to_node == ACTION_DEAUTH_TEST
        )

        # 1. High-yield workflows become dominant
        self.assertTrue(
            handshake_edge.success_weight > deauth_edge.success_weight,
            "Optimal path success weight should be higher.",
        )
        self.assertTrue(
            handshake_edge.score() > deauth_edge.score(),
            "Optimal path score should dominate.",
        )

        # 2. Unstable techniques decay automatically (higher failure weight)
        self.assertTrue(
            deauth_edge.failure_weight > handshake_edge.failure_weight,
            "Unstable path failure weight should be higher.",
        )

        # 3. Exploration vs Exploitation balance
        # The optimal path should be exploited (selected heavily)
        self.assertTrue(
            handshake_selections > deauth_selections * 5,
            "Exploitation should heavily favor the optimal path.",
        )
        # But the unstable path should still be explored occasionally
        self.assertTrue(
            deauth_selections > 0,
            "Exploration should ensure weak paths are tried occasionally.",
        )

    def test_partial_signal_outcome(self):
        """
        Verify that PARTIAL_SIGNAL distributes weight appropriately
        (both success and failure weights increase slightly).
        """
        # Step through to PASSIVE_SCAN
        node = self.agent.step()  # START -> NETWORK_DISCOVERY
        node = self.agent.step()  # NETWORK_DISCOVERY -> PASSIVE_SCAN
        self.assertEqual(node, ACTION_PASSIVE_SCAN)

        # Provide partial signal feedback
        self.agent.feedback(OUTCOME_PARTIAL)

        # Check weights for the path
        start_edges = self.graph.edges.get("START", [])
        start_edge = next(
            (e for e in start_edges if e.to_node == "NETWORK_DISCOVERY"),
            None,
        )

        # We also need to check the Passive scan edge
        discovery_edges = self.graph.edges.get("NETWORK_DISCOVERY", [])
        passive_scan_edge = next(
            (e for e in discovery_edges if e.to_node == ACTION_PASSIVE_SCAN),
            None,
        )

        if start_edge:
            self.assertEqual(start_edge.success_weight, 1.5)
            self.assertEqual(start_edge.failure_weight, 1.5)

        if passive_scan_edge:
            self.assertEqual(passive_scan_edge.success_weight, 1.5)
            self.assertEqual(passive_scan_edge.failure_weight, 1.5)


if __name__ == "__main__":
    unittest.main()
