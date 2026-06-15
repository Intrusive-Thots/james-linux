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
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
)


class TestSedgeCoreIdea(unittest.TestCase):
    """
    Tests for the SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE) CORE IDEA
    components to verify self-evolving behavior.
    Validates state nodes, learning paths, execution feedback learning,
    the policy layer, and the self-evolution loop to ensure optimal
    strategies emerge automatically over time.
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

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=90.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 250000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        # Check probability ratios matching mathematical expectations
        ratio_b = counts["B"] / iterations
        ratio_c = counts["C"] / iterations

        score_b = edge_b.score()
        score_c = edge_c.score()
        total_score = score_b + score_c

        expected_b = score_b / total_score
        expected_c = score_c / total_score

        self.assertAlmostEqual(ratio_b, expected_b, delta=0.02)
        self.assertAlmostEqual(ratio_c, expected_c, delta=0.02)

    def test_self_evolving_loop_and_convergence(self):
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        import random

        for _ in range(250000):
            # In our simulation:
            # ACTION_HANDSHAKE_CAPTURE has 90% success probability
            # ACTION_DEAUTH_TEST has 10% success probability

            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    # Simulate 90% true mathematical success rate
                    if random.random() < 0.90:
                        outcome = OUTCOME_SUCCESS
                    else:
                        outcome = OUTCOME_FAILURE
                    break
                elif node == ACTION_DEAUTH_TEST:
                    # Simulate 10% true mathematical success rate
                    if random.random() < 0.10:
                        outcome = OUTCOME_SUCCESS
                    else:
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

        # Mathematical Proof asserts
        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(handshake_edge.success_weight, 100)
        self.assertGreaterEqual(deauth_edge.failure_weight, 2)

        # Now, test empirical selection probability on the static trained graph
        handshake_selections = 0
        deauth_selections = 0
        iterations = 250000

        # Test stochastic distribution over the trained nodes without updating
        # weights
        for _ in range(iterations):
            choice = agent.decision_engine.decide(STATE_TARGET_ANALYSIS)
            if choice == ACTION_HANDSHAKE_CAPTURE:
                handshake_selections += 1
            elif choice == ACTION_DEAUTH_TEST:
                deauth_selections += 1

        ratio_handshake = handshake_selections / iterations
        ratio_deauth = deauth_selections / iterations

        score_handshake = handshake_edge.score()
        score_deauth = deauth_edge.score()
        total_score = score_handshake + score_deauth

        expected_handshake = score_handshake / total_score
        expected_deauth = score_deauth / total_score

        # Verify edge score mathematical dominance vs empirical stochastic
        # ratio
        self.assertAlmostEqual(ratio_handshake, expected_handshake, delta=0.02)
        self.assertAlmostEqual(ratio_deauth, expected_deauth, delta=0.02)

    def test_edge_score_zero_division_prevention(self):
        edge = Edge(
            from_node="A", to_node="B", success_weight=1.0, failure_weight=0.0
        )
        # Should not raise ZeroDivisionError
        score = edge.score()
        self.assertAlmostEqual(score, 1000000.0, delta=0.1)  # 1.0 / 1e-6

    def test_decision_engine_zero_utility_fallback(self):
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=0.0, failure_weight=0.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=0.0, failure_weight=0.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        # When utility is zero for all, it should fallback to uniform random
        # selection
        counts = {"B": 0, "C": 0}
        iterations = 250000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        # Check that it falls back to uniform distribution roughly
        ratio_b = counts["B"] / iterations
        ratio_c = counts["C"] / iterations
        self.assertAlmostEqual(ratio_b, 0.5, delta=0.02)
        self.assertAlmostEqual(ratio_c, 0.5, delta=0.02)


if __name__ == "__main__":
    unittest.main()
