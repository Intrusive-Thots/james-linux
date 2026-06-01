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


class TestSedgeCoreIdeaFeature(unittest.TestCase):
    """
    Comprehensive tests specifically validating the "SELF-EVOLVING DECISION
    GRAPH ENGINE (SEDGE) CORE IDEA" behavior.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

        # Build a test graph representing the issue scenario
        self.graph.add_node(Node(id="scan", state_type="state"))
        self.graph.add_node(Node(id="analysis", state_type="state"))
        self.graph.add_node(Node(id="handshake_capture", state_type="action"))
        self.graph.add_node(Node(id="validate", state_type="state"))
        self.graph.add_node(Node(id="aggressive_attack", state_type="action"))
        self.graph.add_node(Node(id="fail", state_type="state"))

        # Add edges
        self.graph.add_edge(Edge(from_node="scan", to_node="analysis"))
        self.graph.add_edge(Edge(from_node="analysis", to_node="handshake_capture"))
        self.graph.add_edge(Edge(from_node="handshake_capture", to_node="validate"))

        self.graph.add_edge(Edge(from_node="scan", to_node="aggressive_attack"))
        self.graph.add_edge(Edge(from_node="aggressive_attack", to_node="fail"))

    def test_optimal_strategy_emergence_successful_path(self):
        """
        Test that a successful sequence (scan -> analysis -> handshake_capture -> validate)
        gains higher success_weight over time.
        """
        path = ["scan", "analysis", "handshake_capture", "validate"]

        # Run multiple successful iterations
        iterations = 5
        for _ in range(iterations):
            self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        # Check the edges in the path
        edges = self.graph.get_all_edges()

        edge_scan_analysis = next(e for e in edges if e.from_node == "scan" and e.to_node == "analysis")
        self.assertEqual(edge_scan_analysis.success_weight, 1.0 + iterations)

        edge_analysis_handshake = next(e for e in edges if e.from_node == "analysis" and e.to_node == "handshake_capture")
        self.assertEqual(edge_analysis_handshake.success_weight, 1.0 + iterations)

        edge_handshake_validate = next(e for e in edges if e.from_node == "handshake_capture" and e.to_node == "validate")
        self.assertEqual(edge_handshake_validate.success_weight, 1.0 + iterations)

    def test_optimal_strategy_emergence_failed_path(self):
        """
        Test that a failed sequence (scan -> aggressive_attack -> fail)
        gains higher failure_weight over time.
        """
        path = ["scan", "aggressive_attack", "fail"]

        # Run multiple failed iterations
        iterations = 5
        for _ in range(iterations):
            self.learner.update(self.graph, path, OUTCOME_FAILURE)

        # Check the edges in the path
        edges = self.graph.get_all_edges()

        edge_scan_aggressive = next(e for e in edges if e.from_node == "scan" and e.to_node == "aggressive_attack")
        self.assertEqual(edge_scan_aggressive.failure_weight, 1.0 + iterations)

        edge_aggressive_fail = next(e for e in edges if e.from_node == "aggressive_attack" and e.to_node == "fail")
        self.assertEqual(edge_aggressive_fail.failure_weight, 1.0 + iterations)

    def test_graph_management_methods(self):
        """
        Test the new graph management methods added to DecisionGraph.
        """
        nodes = self.graph.get_all_nodes()
        self.assertEqual(len(nodes), 6)

        edges = self.graph.get_all_edges()
        self.assertEqual(len(edges), 5)

        self.graph.clear()
        self.assertEqual(len(self.graph.get_all_nodes()), 0)
        self.assertEqual(len(self.graph.get_all_edges()), 0)

    def test_node_and_edge_repr(self):
        """
        Test the __repr__ methods of Node and Edge.
        """
        node = Node(id="test_id", state_type="test_type")
        self.assertEqual(repr(node), "Node(id='test_id', type='test_type')")

        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(repr(edge), "Edge(A -> B, visits=0, score=1.00)")

if __name__ == "__main__":
    unittest.main()
