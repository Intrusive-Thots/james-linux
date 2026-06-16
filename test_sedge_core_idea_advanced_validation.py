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


class TestSedgeCoreIdeaAdvancedValidation(unittest.TestCase):
    """
    Advanced verification tests for the SEDGE (Self-Evolving Decision Graph Engine).
    Validates Node/Edge logic, learning outcomes, stochastic decision selection,
    and the domain specific Parrot Wi-Fi graph instance.
    """

    def setUp(self):
        """Prepare fresh graph components for each test."""
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_node_initialization(self):
        """Verifies correct initialization and property storage for Nodes."""
        node = Node(id="node_a", state_type="state", metadata={"key": "val"})
        self.assertEqual(node.id, "node_a")
        self.assertEqual(node.state_type, "state")
        self.assertEqual(node.metadata, {"key": "val"})

    def test_edge_initialization_and_scoring(self):
        """Validates edge logic, zero-division mitigation, and default scoring."""
        edge = Edge(from_node="n1", to_node="n2")
        self.assertEqual(edge.from_node, "n1")
        self.assertEqual(edge.to_node, "n2")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)

        # Verify base scoring behavior
        self.assertAlmostEqual(edge.score(), 0.9999990000010001, places=6)

        # Test safe handling when failure weight drops near 0
        edge_zero = Edge(from_node="n1", to_node="n2", failure_weight=0.0)
        self.assertAlmostEqual(edge_zero.score(), 1000000.0, delta=0.1)

    def test_learning_engine_updates_with_string_outcomes(self):
        """Ensures LearningEngine properly increments weights based on explicit string outcomes."""
        edge = Edge(from_node="n1", to_node="n2")
        self.graph.add_edge(edge)
        path = ["n1", "n2"]

        # Test OUTCOME_SUCCESS mapping
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        # Test OUTCOME_FAILURE mapping
        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

        # Test OUTCOME_PARTIAL mapping
        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        self.assertEqual(edge.visits, 3)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)

    def test_decision_engine_stochastic_selection(self):
        """Verifies probability-based selection favoring higher scoring edges."""
        decision_engine = DecisionEngine(self.graph)

        # Create two competing edges with starkly contrasted weights
        edge_win = Edge(from_node="n1", to_node="win_node", success_weight=100.0, failure_weight=1.0)
        edge_lose = Edge(from_node="n1", to_node="lose_node", success_weight=1.0, failure_weight=100.0)

        self.graph.add_edge(edge_win)
        self.graph.add_edge(edge_lose)

        selections = {"win_node": 0, "lose_node": 0}
        iterations = 1000

        for _ in range(iterations):
            choice = decision_engine.decide("n1")
            selections[choice] += 1

        # The higher weighted path should be heavily favored
        self.assertGreater(selections["win_node"], selections["lose_node"] * 50)

    def test_decision_engine_zero_utility_fallback(self):
        """Ensures DecisionEngine falls back to uniform choice when total utility is strictly 0.0."""
        decision_engine = DecisionEngine(self.graph)

        # Simulate edges whose combined probability evaluates to 0.0
        e1 = Edge(from_node="start", to_node="route_1", success_weight=0.0, failure_weight=0.0)
        e2 = Edge(from_node="start", to_node="route_2", success_weight=0.0, failure_weight=0.0)

        self.graph.add_edge(e1)
        self.graph.add_edge(e2)

        selections = {"route_1": 0, "route_2": 0}
        iterations = 1000

        for _ in range(iterations):
            choice = decision_engine.decide("start")
            selections[choice] += 1

        # Because total utility is 0.0, both routes should receive roughly 50% distribution
        self.assertGreater(selections["route_1"], 100)
        self.assertGreater(selections["route_2"], 100)

    def test_parrot_wifi_graph_factory(self):
        """Validates that the build_parrot_wifi_graph factory constructs the correct topology."""
        graph = build_parrot_wifi_graph()

        # Verify node existence
        self.assertIsNotNone(graph.get_node(STATE_START))
        self.assertIsNotNone(graph.get_node(ACTION_HANDSHAKE_CAPTURE))
        self.assertIsNotNone(graph.get_node(ACTION_EVIL_TWIN_SIMULATION))

        # Verify a specific structural edge
        start_edges = graph.get_edges(STATE_START)
        self.assertEqual(len(start_edges), 1)
        self.assertEqual(start_edges[0].to_node, STATE_NETWORK_DISCOVERY)

        # Verify metadata persistence in action nodes
        evil_twin_node = graph.get_node(ACTION_EVIL_TWIN_SIMULATION)
        self.assertTrue(evil_twin_node.metadata.get("authorized_only", False))


if __name__ == "__main__":
    unittest.main()
