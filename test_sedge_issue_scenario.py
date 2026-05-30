import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
)

class TestSedgeIssueScenario(unittest.TestCase):
    """
    Tests the exact scenario described in the issue for SEDGE system.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

        # Add nodes
        self.graph.add_node(Node(id="scan", state_type="state"))
        self.graph.add_node(Node(id="analyze", state_type="state"))
        self.graph.add_node(Node(id="handshake_capture", state_type="action"))
        self.graph.add_node(Node(id="validate", state_type="action"))
        self.graph.add_node(Node(id="aggressive_attack", state_type="action"))
        self.graph.add_node(Node(id="fail", state_type="state"))

        # Add edges for the paths
        # scan -> analyze -> handshake_capture -> validate
        self.graph.add_edge(Edge(from_node="scan", to_node="analyze"))
        self.graph.add_edge(Edge(from_node="analyze", to_node="handshake_capture"))
        self.graph.add_edge(Edge(from_node="handshake_capture", to_node="validate"))

        # scan -> aggressive_attack -> fail
        self.graph.add_edge(Edge(from_node="scan", to_node="aggressive_attack"))
        self.graph.add_edge(Edge(from_node="aggressive_attack", to_node="fail"))

    def test_optimal_strategies_emerge(self):
        # Initial edges
        scan_to_analyze_edge = self.graph.edges["scan"][0] # scan -> analyze
        scan_to_aggressive_edge = self.graph.edges["scan"][1] # scan -> aggressive_attack

        self.assertEqual(scan_to_analyze_edge.to_node, "analyze")
        self.assertEqual(scan_to_aggressive_edge.to_node, "aggressive_attack")

        # Verify initial weights
        self.assertEqual(scan_to_analyze_edge.success_weight, 1.0)
        self.assertEqual(scan_to_analyze_edge.failure_weight, 1.0)

        self.assertEqual(scan_to_aggressive_edge.success_weight, 1.0)
        self.assertEqual(scan_to_aggressive_edge.failure_weight, 1.0)

        # Successful sequence: scan -> analyze -> handshake_capture -> validate
        success_path = ["scan", "analyze", "handshake_capture", "validate"]

        # Failed sequence: scan -> aggressive_attack -> fail
        failure_path = ["scan", "aggressive_attack", "fail"]

        # Simulate over time: success path happens and succeeds
        for _ in range(5):
            self.learner.update(self.graph, success_path, OUTCOME_SUCCESS)

        # Simulate over time: failure path happens and fails
        for _ in range(5):
            self.learner.update(self.graph, failure_path, OUTCOME_FAILURE)

        # Verify weights after learning
        self.assertEqual(scan_to_analyze_edge.success_weight, 6.0) # 1.0 + 5.0
        self.assertEqual(scan_to_analyze_edge.failure_weight, 1.0)

        self.assertEqual(scan_to_aggressive_edge.success_weight, 1.0)
        self.assertEqual(scan_to_aggressive_edge.failure_weight, 6.0) # 1.0 + 5.0

        # Successful path becomes stronger, failed path decays
        self.assertGreater(scan_to_analyze_edge.score(), scan_to_aggressive_edge.score())

if __name__ == "__main__":
    unittest.main()
