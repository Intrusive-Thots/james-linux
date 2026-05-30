import unittest
import collections
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    DecisionEngine,
)


class TestSedgeExploration(unittest.TestCase):
    """
    Tests the "EXPLORATION vs EXPLOITATION" behavior described in SEDGE.
    Verifies that the stochastic weighted selection naturally balances
    exploitation (using strong known paths) with exploration (trying weak paths).
    """

    def setUp(self):
        self.graph = DecisionGraph()

        # Add nodes
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="STRONG_PATH", state_type="action"))
        self.graph.add_node(Node(id="WEAK_PATH", state_type="action"))

        # Strong edge simulates a path with high success history
        self.strong_edge = Edge(
            from_node="START",
            to_node="STRONG_PATH",
            success_weight=90.0,
            failure_weight=1.0,
        )

        # Weak edge simulates a path with poor success history
        self.weak_edge = Edge(
            from_node="START",
            to_node="WEAK_PATH",
            success_weight=10.0,
            failure_weight=1.0,
        )

        self.graph.add_edge(self.strong_edge)
        self.graph.add_edge(self.weak_edge)

        self.decision_engine = DecisionEngine(self.graph)

    def test_exploration_vs_exploitation(self):
        """
        Simulate a large number of decisions and verify that both paths are chosen,
        but the strong path is chosen significantly more often.
        """
        iterations = 10000
        selections = collections.Counter()

        for _ in range(iterations):
            next_node = self.decision_engine.decide("START")
            selections[next_node] += 1

        strong_count = selections["STRONG_PATH"]
        weak_count = selections["WEAK_PATH"]

        # Ensure that both exploration and exploitation occurred
        self.assertGreater(
            strong_count,
            0,
            "Exploitation failed: strong path was never selected.",
        )
        self.assertGreater(
            weak_count, 0, "Exploration failed: weak path was never selected."
        )

        # Ensure that the strong path is heavily favored
        self.assertGreater(
            strong_count,
            weak_count * 5,
            "Exploitation failed: strong path was not favored enough.",
        )

        # Calculate approximate probabilities
        strong_prob = strong_count / iterations
        weak_prob = weak_count / iterations

        # Given the scores (90 vs 10), we expect ~90% strong and ~10% weak
        self.assertAlmostEqual(strong_prob, 0.9, delta=0.05)
        self.assertAlmostEqual(weak_prob, 0.1, delta=0.05)


if __name__ == "__main__":
    unittest.main()
