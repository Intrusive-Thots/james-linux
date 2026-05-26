import unittest
import random
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
)


class TestSedgeEngine(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="SCAN", state_type="action"))
        self.graph.add_node(Node(id="ATTACK", state_type="action"))

        self.graph.add_edge(Edge(from_node="START", to_node="SCAN"))
        self.graph.add_edge(Edge(from_node="SCAN", to_node="ATTACK"))

        self.learner = LearningEngine()
        self.decision_engine = DecisionEngine(self.graph)

    def test_learning_engine_success(self):
        path = ["START", "SCAN", "ATTACK"]
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 2.0)
        self.assertEqual(start_scan_edge.failure_weight, 1.0)

    def test_learning_engine_failure(self):
        path = ["START", "SCAN", "ATTACK"]
        self.learner.update(self.graph, path, OUTCOME_FAILURE)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 1.0)
        self.assertEqual(start_scan_edge.failure_weight, 2.0)

    def test_learning_engine_partial(self):
        path = ["START", "SCAN"]
        self.learner.update(self.graph, path, OUTCOME_PARTIAL)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 1.5)
        self.assertEqual(start_scan_edge.failure_weight, 1.5)

    def test_decision_engine_decide(self):
        # With default weights (1.0 success, 1.0 failure), both score exactly 1.0.
        # But here START only has 1 edge.
        next_node = self.decision_engine.decide("START")
        self.assertEqual(next_node, "SCAN")

        # Add another edge to START
        self.graph.add_edge(Edge(from_node="START", to_node="ATTACK", success_weight=5.0))

        # With higher weight on ATTACK, stochastic selection favors it heavily.
        # Mock random to avoid flakiness, or just test fallback behavior.

        # Test zero total case
        self.graph.edges["START"][0].success_weight = 0.0
        self.graph.edges["START"][1].success_weight = 0.0

        # Now both have zero utility, fallback to random uniform selection.
        random.seed(42)
        next_node_zero = self.decision_engine.decide("START")
        self.assertIn(next_node_zero, ["SCAN", "ATTACK"])

    def test_decision_engine_no_candidates(self):
        next_node = self.decision_engine.decide("ATTACK")
        self.assertIsNone(next_node)


if __name__ == "__main__":
    unittest.main()
