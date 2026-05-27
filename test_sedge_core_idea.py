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


class TestSedgeCoreIdea(unittest.TestCase):
    """
    Tests for the SEDGE components to verify self-evolving behavior.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_state_node_model(self):
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
        # 1.0 / (1.0 + 1e-6)
        self.assertAlmostEqual(edge.score(), 0.999999, places=5)

    def test_decision_graph_core(self):
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge = Edge(from_node="A", to_node="B", success_weight=5.0)
        self.graph.add_edge(edge)

        self.assertIn("A", self.graph.nodes)
        self.assertIn("B", self.graph.nodes)
        self.assertEqual(len(self.graph.edges.get("A", [])), 1)

        best_next = self.graph.get_best_next("A")
        self.assertIsNotNone(best_next)
        self.assertEqual(best_next.to_node, "B")

        self.assertIsNone(self.graph.get_best_next("B"))

    def test_learning_engine(self):
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

    def test_decision_engine(self):
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0)
        edge_c = Edge(from_node="A", to_node="C", success_weight=1.0, failure_weight=90.0)
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], counts["C"] * 10)

    def test_self_evolving_loop_and_convergence(self):
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        iterations = 1000
        handshake_selections = 0
        deauth_selections = 0

        for _ in range(iterations):
            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    handshake_selections += 1
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    deauth_selections += 1
                    break

            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(handshake_edge.success_weight, deauth_edge.success_weight)
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        self.assertGreater(deauth_edge.failure_weight, handshake_edge.failure_weight)

        self.assertGreater(handshake_selections, deauth_selections)
        self.assertGreater(deauth_selections, 0)


if __name__ == "__main__":
    unittest.main()
