import unittest
from collections import Counter
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
)
from james.tools.constants import OUTCOME_SUCCESS, OUTCOME_FAILURE


class TestSedgeMathematicalProof(unittest.TestCase):
    """
    Mathematical proofs demonstrating the self-evolving properties
    of the Self-Evolving Decision Graph Engine (SEDGE).
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()
        self.decision_engine = DecisionEngine(self.graph)

    def test_stochastic_selection_convergence(self):
        """
        Prove that stochastic weighted selection converges to expected
        probabilities based on edge utility scores.
        """
        # Node A branches to B and C
        self.graph.add_node(Node(id="A", state_type="state"))
        self.graph.add_node(Node(id="B", state_type="action"))
        self.graph.add_node(Node(id="C", state_type="action"))

        # Edge A->B has a utility score of 4.0 (4.0 / 1.0)
        edge_b = Edge("A", "B", success_weight=4.0, failure_weight=1.0)

        # Edge A->C has a utility score of 1.0 (1.0 / 1.0)
        edge_c = Edge("A", "C", success_weight=1.0, failure_weight=1.0)

        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        # Expected probabilities:
        # P(B) = score(B) / (score(B) + score(C)) = 4.0 / 5.0 = 0.80
        # P(C) = score(C) / (score(B) + score(C)) = 1.0 / 5.0 = 0.20

        iterations = 10000
        selections = Counter()

        for _ in range(iterations):
            choice = self.decision_engine.decide("A")
            selections[choice] += 1

        prob_b = selections["B"] / iterations
        prob_c = selections["C"] / iterations

        # Allow for statistical variance (law of large numbers)
        self.assertAlmostEqual(prob_b, 0.80, delta=0.03)
        self.assertAlmostEqual(prob_c, 0.20, delta=0.03)

    def test_learning_feedback_weight_adjustment(self):
        """
        Prove that backpropagation of outcomes correctly adjusts edge
        weights along a traversal path.
        """
        self.graph.add_node(Node(id="Start", state_type="state"))
        self.graph.add_node(Node(id="Mid", state_type="state"))
        self.graph.add_node(Node(id="End", state_type="action"))

        edge_1 = Edge("Start", "Mid", success_weight=1.0, failure_weight=1.0)
        edge_2 = Edge("Mid", "End", success_weight=1.0, failure_weight=1.0)

        self.graph.add_edge(edge_1)
        self.graph.add_edge(edge_2)

        path = ["Start", "Mid", "End"]

        # Run 3 successful iterations
        for _ in range(3):
            self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        # Run 1 failed iteration
        for _ in range(1):
            self.learner.update(self.graph, path, OUTCOME_FAILURE)

        # Edges start with weight 1.0.
        # 3 successes -> +3.0 to success_weight
        # 1 failure -> +1.0 to failure_weight

        self.assertEqual(edge_1.success_weight, 4.0)
        self.assertEqual(edge_1.failure_weight, 2.0)
        self.assertEqual(edge_1.visits, 4)

        self.assertEqual(edge_2.success_weight, 4.0)
        self.assertEqual(edge_2.failure_weight, 2.0)
        self.assertEqual(edge_2.visits, 4)

        # New score = 4.0 / 2.0 = 2.0 (approx)
        self.assertAlmostEqual(edge_1.score(), 2.0, delta=0.001)

    def test_evolutionary_decay_and_dominance(self):
        """
        Prove that over continuous episodes, a consistently successful
        path exponentially out-competes a frequently failing path.
        """
        self.graph.add_node(Node(id="Start", state_type="state"))
        self.graph.add_node(Node(id="GoodPath", state_type="action"))
        self.graph.add_node(Node(id="BadPath", state_type="action"))

        # Initialize neutrally
        edge_good = Edge("Start", "GoodPath", success_weight=1.0, failure_weight=1.0)
        edge_bad = Edge("Start", "BadPath", success_weight=1.0, failure_weight=1.0)

        self.graph.add_edge(edge_good)
        self.graph.add_edge(edge_bad)

        iterations = 500

        for _ in range(iterations):
            choice = self.decision_engine.decide("Start")

            # Simulate real-world feedback
            if choice == "GoodPath":
                # Good path succeeds 90% of the time
                import random
                outcome = OUTCOME_SUCCESS if random.random() < 0.9 else OUTCOME_FAILURE
                self.learner.update(self.graph, ["Start", "GoodPath"], outcome)
            elif choice == "BadPath":
                # Bad path fails 90% of the time
                import random
                outcome = OUTCOME_SUCCESS if random.random() < 0.1 else OUTCOME_FAILURE
                self.learner.update(self.graph, ["Start", "BadPath"], outcome)

        # Mathematical convergence proof
        self.assertGreater(edge_good.score(), edge_bad.score() * 5)
        self.assertGreater(edge_good.visits, edge_bad.visits * 2)

if __name__ == "__main__":
    unittest.main()
