import unittest
import math
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


class TestSedgeCoreIdeaMathematicalProof(unittest.TestCase):
    """
    Mathematical proof and comprehensive test suite for the SEDGE behavior.
    Proves that successful paths strengthen, failed paths decay, and optimal
    strategies automatically emerge.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_mathematical_edge_scoring(self):
        """
        Proof of scoring mathematically mitigating zero division and scaling properly.
        """
        edge = Edge(from_node="A", to_node="B", success_weight=1.0, failure_weight=1.0)
        self.assertAlmostEqual(edge.score(), 0.999999, places=5)

        edge.success_weight = 5.0
        edge.failure_weight = 2.0
        self.assertAlmostEqual(edge.score(), 2.49999, places=4)

        edge.success_weight = 0.0
        edge.failure_weight = 0.0
        self.assertAlmostEqual(edge.score(), 0.0, places=5)

        edge.success_weight = 1.0
        edge.failure_weight = 0.0
        self.assertGreater(edge.score(), 999999)

    def test_mathematical_probability_convergence(self):
        """
        Proves that stochastic selection converges optimally with law of large numbers.
        """
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(from_node="A", to_node="B", success_weight=80.0, failure_weight=1.0)
        edge_c = Edge(from_node="A", to_node="C", success_weight=20.0, failure_weight=1.0)

        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 10000

        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        ratio_b = counts["B"] / iterations
        ratio_c = counts["C"] / iterations

        # Expected ratios based on scores:
        # B score ~ 80, C score ~ 20. Total ~ 100
        # Prob B ~ 0.8, Prob C ~ 0.2
        self.assertAlmostEqual(ratio_b, 0.8, delta=0.05)
        self.assertAlmostEqual(ratio_c, 0.2, delta=0.05)

    def test_learning_engine_backpropagation(self):
        """
        Mathematical validation of weight adjustment across nodes.
        """
        edge1 = Edge(from_node="A", to_node="B")
        edge2 = Edge(from_node="B", to_node="C")

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        path = ["A", "B", "C"]

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge2.success_weight, 2.0)

        self.learner.update(self.graph, path, OUTCOME_PARTIAL)

        self.assertEqual(edge1.success_weight, 2.5)
        self.assertEqual(edge1.failure_weight, 1.5)
        self.assertEqual(edge2.success_weight, 2.5)
        self.assertEqual(edge2.failure_weight, 1.5)

    def test_sedge_parrot_system_emergent_optimal_strategy(self):
        """
        Mathematical proof of SEDGE behavior on the real domain map.
        Simulates 2000 runs to guarantee mathematical dominance of the successful path.
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        handshake_selections = 0
        deauth_selections = 0

        import random
        for _ in range(2000):
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
                    outcome = OUTCOME_SUCCESS if random.random() < 0.90 else OUTCOME_FAILURE
                    break
                elif node == ACTION_DEAUTH_TEST:
                    # Simulate 10% true mathematical success rate
                    outcome = OUTCOME_SUCCESS if random.random() < 0.10 else OUTCOME_FAILURE
                    break

            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        # Mathematical Proof asserts
        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(handshake_edge.success_weight, 100)
        self.assertGreaterEqual(deauth_edge.failure_weight, 2)

        # Verify edge score mathematical dominance
        self.assertGreater(handshake_edge.score(), deauth_edge.score() * 10)

if __name__ == '__main__':
    unittest.main()
