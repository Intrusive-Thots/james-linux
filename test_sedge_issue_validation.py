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
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeIssueValidation(unittest.TestCase):
    """
    Validates SEDGE components and behavior exactly as defined in the issue.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_node_model(self):
        node = Node(id="test_node", state_type="action")
        self.assertEqual(node.id, "test_node")
        self.assertEqual(node.state_type, "action")
        self.assertEqual(node.metadata, {})

    def test_edge_model(self):
        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)
        # Check epsilon logic is roughly correct
        self.assertAlmostEqual(edge.score(), 1.0, places=5)

    def test_decision_graph_core(self):
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge = Edge(from_node="A", to_node="B", success_weight=5.0)
        self.graph.add_edge(edge)

        self.assertIn("A", self.graph.nodes)
        self.assertIn("B", self.graph.nodes)
        self.assertEqual(len(list(self.graph.edges.get("A", {}).values())), 1)

        best_next = self.graph.get_best_next("A")
        self.assertIsNotNone(best_next)
        self.assertEqual(best_next.to_node, "B")

        self.assertIsNone(self.graph.get_best_next("B"))

    def test_learning_engine(self):
        # The prompt says: "In james/core/sedge.py, LearningEngine.update specifically expects a string outcome..."
        # We ensure it handles string outcomes.
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)

        path = ["A", "B"]

        # Test success
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        # Test failure
        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

    def test_decision_engine(self):
        # We need a predictable behavior to test the stochastic nature.
        # We'll use law of large numbers.
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0
        )  # Highly favored
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=90.0
        )  # Not favored
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(
            counts["B"], counts["C"] * 10
        )  # B should be picked significantly more often

    def test_self_evolving_agent_and_convergence(self):
        # Build the graph mapped to Parrot WiFi System as requested
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # Let's run a simulation to see it evolve over time
        iterations = 1000
        handshake_selections = 0
        deauth_selections = 0

        for _ in range(iterations):
            # We want to trace it.
            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break

                # As defined in issue, successful paths become stronger, failed paths decay.
                # "Optimal path: scan -> analyze -> handshake_capture -> validate" (gain: higher success weight)
                # "Failed path: scan -> aggressive_attack -> fail" (gain: higher failure weight)
                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    handshake_selections += 1
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    deauth_selections += 1
                    break

            agent.feedback(outcome)

        # We verify that optimal paths became dominant.
        analysis_edges = list(graph.edges.get(STATE_TARGET_ANALYSIS, {}).values())
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

        # High yield workflow (handshake) became dominant
        self.assertGreater(
            handshake_edge.success_weight, deauth_edge.success_weight
        )
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        # Unstable technique (deauth) decayed automatically
        self.assertGreater(
            deauth_edge.failure_weight, handshake_edge.failure_weight
        )

        # Exploration vs Exploitation balance
        self.assertGreater(handshake_selections, deauth_selections)
        self.assertGreater(
            deauth_selections, 0
        )  # Weak path should still be explored occasionally


if __name__ == "__main__":
    unittest.main()
