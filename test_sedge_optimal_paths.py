import unittest
from james.core.sedge import (
    SelfEvolvingAgent,
    build_parrot_wifi_graph,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeOptimalPaths(unittest.TestCase):
    """
    Tests proving that successful paths become stronger, failed paths decay,
    and optimal strategies emerge automatically.
    """

    def setUp(self):
        # Create a fresh graph for each test
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)

    def test_successful_sequence_strengthens(self):
        """
        Verify that a successful sequence (e.g., handshake capture) strengthens
        the traversal probability.
        """
        # Force a specific successful path:
        # START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS -> HANDSHAKE_CAPTURE -> SECURITY_PROFILING
        # Note: we don't need to force it by monkeypatching, we can just manually set the agent's path and feed it back.

        test_path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_HANDSHAKE_CAPTURE,
            STATE_SECURITY_PROFILING
        ]

        self.agent.current_path = test_path

        # Apply success feedback
        self.agent.feedback(OUTCOME_SUCCESS)

        # Verify success weights increased
        # TARGET_ANALYSIS -> HANDSHAKE_CAPTURE edge
        analysis_edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)

        self.assertIsNotNone(handshake_edge)
        self.assertEqual(handshake_edge.visits, 1)
        self.assertEqual(handshake_edge.success_weight, 2.0)
        self.assertEqual(handshake_edge.failure_weight, 1.0)

        # Verify edge score improved
        self.assertGreater(handshake_edge.score(), 1.0)

    def test_failed_sequence_decays(self):
        """
        Verify that a failed sequence (e.g., aggressive deauth test) increases
        failure weight, thus reducing traversal probability.
        """
        test_path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_DEAUTH_TEST,
            STATE_SECURITY_PROFILING
        ]

        self.agent.current_path = test_path

        # Apply failure feedback
        self.agent.feedback(OUTCOME_FAILURE)

        # Verify failure weights increased
        # TARGET_ANALYSIS -> DEAUTH_TEST edge
        analysis_edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(deauth_edge)
        self.assertEqual(deauth_edge.visits, 1)
        self.assertEqual(deauth_edge.success_weight, 1.0)
        self.assertEqual(deauth_edge.failure_weight, 2.0)

        # Verify edge score decreased
        self.assertLess(deauth_edge.score(), 1.0)

    def test_optimal_strategy_emerges(self):
        """
        Run multiple iterations to simulate outcomes where HANDSHAKE_CAPTURE succeeds
        and DEAUTH_TEST fails, and verify the graph converges toward the optimal pipeline.
        """
        import random
        random.seed(42)
        iterations = 1000

        for _ in range(iterations):
            # Let the agent walk the graph
            outcome = OUTCOME_PARTIAL
            while True:
                node = self.agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    break

            # Apply feedback based on what it chose
            self.agent.feedback(outcome)

        # Verify that optimal paths became dominant
        analysis_edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        # Handshake should be overwhelmingly preferred due to high success weight
        self.assertGreater(handshake_edge.success_weight, deauth_edge.success_weight)
        self.assertGreater(deauth_edge.failure_weight, handshake_edge.failure_weight)

        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        # Verify statistical selection via the DecisionEngine
        import random
        random.seed(42)
        handshake_selections = 0
        deauth_selections = 0

        test_iterations = 1000
        for _ in range(test_iterations):
            choice = self.agent.decision_engine.decide(STATE_TARGET_ANALYSIS)
            if choice == ACTION_HANDSHAKE_CAPTURE:
                handshake_selections += 1
            elif choice == ACTION_DEAUTH_TEST:
                deauth_selections += 1

        # The stochastic weighted selection should overwhelmingly pick handshake
        self.assertGreater(handshake_selections, deauth_selections * 10)


if __name__ == "__main__":
    unittest.main()
