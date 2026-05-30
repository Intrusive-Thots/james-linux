import unittest
from james.core.sedge import (
    LearningEngine,
    DecisionGraph,
    Edge,
    DecisionEngine,
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


class TestSedgeDesignDocument(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_learning_engine_string_outcomes(self):
        """Verify LearningEngine.update handles string outcomes."""
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)
        path = ["A", "B"]

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        self.assertEqual(edge.visits, 3)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)

    def test_build_parrot_wifi_graph_mappings(self):
        """Validate build_parrot_wifi_graph() node/edge mappings."""
        graph = build_parrot_wifi_graph()

        # Verify states
        self.assertIn(STATE_START, graph.nodes)
        self.assertIn(STATE_NETWORK_DISCOVERY, graph.nodes)
        self.assertIn(STATE_TARGET_ANALYSIS, graph.nodes)
        self.assertIn(STATE_SECURITY_PROFILING, graph.nodes)

        # Verify actions
        self.assertIn(ACTION_PASSIVE_SCAN, graph.nodes)
        self.assertIn(ACTION_HANDSHAKE_CAPTURE, graph.nodes)
        self.assertIn(ACTION_DEAUTH_TEST, graph.nodes)
        self.assertIn(ACTION_EVIL_TWIN_SIMULATION, graph.nodes)

        # Verify edges (transitions)
        self.assertTrue(
            any(
                e.to_node == STATE_NETWORK_DISCOVERY
                for e in graph.edges[STATE_START]
            )
        )
        self.assertTrue(
            any(
                e.to_node == ACTION_PASSIVE_SCAN
                for e in graph.edges[STATE_NETWORK_DISCOVERY]
            )
        )
        self.assertTrue(
            any(
                e.to_node == STATE_TARGET_ANALYSIS
                for e in graph.edges[ACTION_PASSIVE_SCAN]
            )
        )
        self.assertTrue(
            any(
                e.to_node == ACTION_HANDSHAKE_CAPTURE
                for e in graph.edges[STATE_TARGET_ANALYSIS]
            )
        )
        self.assertTrue(
            any(
                e.to_node == ACTION_DEAUTH_TEST
                for e in graph.edges[STATE_TARGET_ANALYSIS]
            )
        )
        self.assertTrue(
            any(
                e.to_node == STATE_SECURITY_PROFILING
                for e in graph.edges[ACTION_HANDSHAKE_CAPTURE]
            )
        )
        self.assertTrue(
            any(
                e.to_node == STATE_SECURITY_PROFILING
                for e in graph.edges[ACTION_DEAUTH_TEST]
            )
        )
        self.assertTrue(
            any(
                e.to_node == ACTION_EVIL_TWIN_SIMULATION
                for e in graph.edges[STATE_SECURITY_PROFILING]
            )
        )

    def test_decision_engine_stochastic_selection(self):
        """Test the DecisionEngine stochastic weighted selection."""
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=9.0, failure_weight=1.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=9.0
        )

        # B score roughly 9.0
        # C score roughly 0.111

        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], counts["C"] * 10)


if __name__ == "__main__":
    unittest.main()
