import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    SelfEvolvingAgent,
    DecisionEngine,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
)


class TestSedgeLearningPaths(unittest.TestCase):
    """
    Test how SEDGE learns from specific optimal and failed sequences,
    balancing exploration and exploitation.
    """

    def setUp(self):
        self.graph = DecisionGraph()

        # Nodes
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="scan", state_type="action"))
        self.graph.add_node(Node(id="analyze", state_type="state"))
        self.graph.add_node(Node(id="handshake_capture", state_type="action"))
        self.graph.add_node(Node(id="validate", state_type="state"))
        self.graph.add_node(Node(id="aggressive_attack", state_type="action"))
        self.graph.add_node(Node(id="fail", state_type="state"))

        # Edges
        self.graph.add_edge(Edge(from_node="START", to_node="scan"))
        self.graph.add_edge(Edge(from_node="scan", to_node="analyze"))
        self.graph.add_edge(
            Edge(from_node="scan", to_node="aggressive_attack")
        )
        self.graph.add_edge(
            Edge(from_node="analyze", to_node="handshake_capture")
        )
        self.graph.add_edge(
            Edge(from_node="handshake_capture", to_node="validate")
        )
        self.graph.add_edge(
            Edge(from_node="aggressive_attack", to_node="fail")
        )

    def test_optimal_and_failed_sequences(self):
        """
        Verify that:
        - Successful sequence: scan -> analyze -> handshake_capture -> validate gains higher success_weight
        - Failed sequence: scan -> aggressive_attack -> fail gains higher failure_weight
        - The stronger path gains higher traversal probability compared to the failed path.
        """
        agent = SelfEvolvingAgent(self.graph)

        # We manually update weights to simulate learning the sequences
        path_success = [
            "START",
            "scan",
            "analyze",
            "handshake_capture",
            "validate",
        ]
        agent.learner.update(self.graph, path_success, OUTCOME_SUCCESS)

        path_fail = ["START", "scan", "aggressive_attack", "fail"]
        agent.learner.update(self.graph, path_fail, OUTCOME_FAILURE)

        # Check edges out of 'scan'
        scan_edges = self.graph.edges.get("scan", [])
        analyze_edge = next(e for e in scan_edges if e.to_node == "analyze")
        aggressive_edge = next(
            e for e in scan_edges if e.to_node == "aggressive_attack"
        )

        # Verify successful sequence gained higher success_weight
        self.assertEqual(analyze_edge.success_weight, 2.0)
        self.assertEqual(analyze_edge.failure_weight, 1.0)

        # Verify failed sequence gained higher failure_weight
        self.assertEqual(aggressive_edge.success_weight, 1.0)
        self.assertEqual(aggressive_edge.failure_weight, 2.0)

        # Verify stronger traversal probability for successful sequence vs failed sequence
        self.assertTrue(analyze_edge.score() > aggressive_edge.score())

    def test_exploration_vs_exploitation(self):
        """
        Verify that the DecisionEngine correctly balances exploration (trying weak paths occasionally)
        vs exploitation (using strong known paths) through stochastic weighted selection.
        """
        # Set up weights manually to simulate learned behavior
        scan_edges = self.graph.edges.get("scan", [])
        analyze_edge = next(e for e in scan_edges if e.to_node == "analyze")
        aggressive_edge = next(
            e for e in scan_edges if e.to_node == "aggressive_attack"
        )

        # Make "analyze" the strong known path (exploitation target)
        analyze_edge.success_weight = 10.0
        analyze_edge.failure_weight = 1.0

        # Make "aggressive_attack" the weak path (exploration target)
        aggressive_edge.success_weight = 1.0
        aggressive_edge.failure_weight = 10.0

        decision_engine = DecisionEngine(self.graph)

        counts = {"analyze": 0, "aggressive_attack": 0}
        iterations = 10000

        for _ in range(iterations):
            choice = decision_engine.decide("scan")
            if choice in counts:
                counts[choice] += 1

        # Exploitation: Strong known path should be used heavily
        self.assertTrue(counts["analyze"] > counts["aggressive_attack"] * 10)

        # Exploration: Weak path should still be tried occasionally
        self.assertTrue(counts["aggressive_attack"] > 0)


if __name__ == "__main__":
    unittest.main()
