import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
    build_parrot_wifi_graph,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
)


class TestSedgeArchitecture(unittest.TestCase):
    """
    Comprehensive tests to verify the core architecture and logic of SEDGE
    as defined in the feature request.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_node_and_edge_initialization(self):
        """Test Node and Edge model definitions."""
        node = Node(
            id="test_state", state_type="state", metadata={"key": "val"}
        )
        self.assertEqual(node.id, "test_state")
        self.assertEqual(node.state_type, "state")
        self.assertEqual(node.metadata, {"key": "val"})

        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)

    def test_edge_score_calculation(self):
        """Test the utility score calculation for an Edge."""
        edge = Edge(
            from_node="A", to_node="B", success_weight=5.0, failure_weight=2.0
        )
        # Expected: 5.0 / (2.0 + 1e-6) ~= 2.5
        self.assertAlmostEqual(edge.score(), 2.5, places=5)

        # Test zero division prevention
        edge_zero = Edge(
            from_node="C", to_node="D", success_weight=1.0, failure_weight=0.0
        )
        self.assertAlmostEqual(edge_zero.score(), 1000000.0, delta=0.1)

    def test_decision_graph_add_get_best_next(self):
        """Test DecisionGraph core operations."""
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge1 = Edge(from_node="A", to_node="B", success_weight=2.0)
        edge2 = Edge(from_node="A", to_node="C", success_weight=5.0)

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        self.assertIn("A", self.graph.nodes)
        self.assertEqual(len(self.graph.edges["A"]), 2)

        best = self.graph.get_best_next("A")
        self.assertIsNotNone(best)
        self.assertEqual(best.to_node, "C")

        self.assertIsNone(self.graph.get_best_next("B"))

    def test_learning_engine_updates_weights_correctly(self):
        """Test that the LearningEngine updates Edge weights based on string outcomes."""
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)
        path = ["A", "B"]

        # Test SUCCESS
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        # Test FAILURE
        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

        # Test PARTIAL
        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        self.assertEqual(edge.visits, 3)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)

    def test_decision_engine_stochastic_selection(self):
        """Test that the DecisionEngine selects paths stochastically based on weights."""
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=10.0, failure_weight=1.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], counts["C"])
        self.assertGreater(counts["C"], 0)  # ensure exploration happens

    def test_self_evolving_agent_loop_and_feedback(self):
        """Test the SelfEvolvingAgent execution feedback loop."""
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # Force a specific outcome for a few iterations to see evolution
        iterations = 500
        for _ in range(iterations):
            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break
                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    break
            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next(
            (
                e
                for e in analysis_edges
                if e.to_node == ACTION_HANDSHAKE_CAPTURE
            ),
            None,
        )
        deauth_edge = next(
            (e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST),
            None,
        )

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        # The handshake path should have become much stronger due to SUCCESS
        self.assertGreater(
            handshake_edge.success_weight, deauth_edge.success_weight
        )
        self.assertGreater(handshake_edge.score(), deauth_edge.score())


if __name__ == "__main__":
    unittest.main()
