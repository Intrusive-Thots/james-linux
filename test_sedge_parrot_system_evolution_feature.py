import unittest
from james.core.sedge import (
    LearningEngine,
    DecisionGraph,
    Edge,
    DecisionEngine,
    build_parrot_wifi_graph,
    SelfEvolvingAgent
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


class TestSedgeParrotSystemEvolutionFeature(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_parrot_wifi_system_metadata_mapping(self):
        """
        Verify that the specific mapping (e.g., ACTION_EVIL_TWIN_SIMULATION)
        has the required authorized_only metadata as described in the issue.
        """
        graph = build_parrot_wifi_graph()

        evil_twin_node = graph.nodes.get(ACTION_EVIL_TWIN_SIMULATION)
        self.assertIsNotNone(evil_twin_node)
        self.assertEqual(evil_twin_node.state_type, "action")
        self.assertEqual(evil_twin_node.metadata.get("authorized_only"), True)

    def test_successful_sequence_gains_weight(self):
        """
        Verify that successful sequences (e.g., scan -> analyze -> handshake_capture)
        gain higher success weight and stronger traversal probability.
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # Force a specific successful path: START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS -> HANDSHAKE_CAPTURE
        path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_HANDSHAKE_CAPTURE
        ]

        # Initial score of edge from TARGET_ANALYSIS to HANDSHAKE_CAPTURE
        analysis_edges = list(graph.edges.get(STATE_TARGET_ANALYSIS, {}).values())
        handshake_edge = next(e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE)
        initial_score = handshake_edge.score()
        initial_success_weight = handshake_edge.success_weight

        # Simulate success
        agent.learner.update(graph, path, OUTCOME_SUCCESS)

        # Check that it gained weight
        self.assertGreater(handshake_edge.success_weight, initial_success_weight)
        self.assertGreater(handshake_edge.score(), initial_score)

    def test_failed_sequence_gains_failure_weight(self):
        """
        Verify that failed sequences (e.g., scan -> aggressive_attack -> fail)
        gain higher failure weight and reduced probability.
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # Force a specific failed path: START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS -> DEAUTH_TEST
        path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_DEAUTH_TEST
        ]

        # Initial score of edge from TARGET_ANALYSIS to DEAUTH_TEST
        analysis_edges = list(graph.edges.get(STATE_TARGET_ANALYSIS, {}).values())
        deauth_edge = next(e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST)
        initial_score = deauth_edge.score()
        initial_failure_weight = deauth_edge.failure_weight

        # Simulate failure
        agent.learner.update(graph, path, OUTCOME_FAILURE)

        # Check that it gained failure weight and reduced overall probability (score)
        self.assertGreater(deauth_edge.failure_weight, initial_failure_weight)
        self.assertLess(deauth_edge.score(), initial_score)

    def test_exploration_vs_exploitation_balance(self):
        """
        Verify the Exploration vs Exploitation balance using stochastic weighted selection.
        """
        decision_engine = DecisionEngine(self.graph)

        # Create two competing edges from A
        # Edge B represents a strong, known successful path (exploitation)
        # Edge C represents a weak path (exploration)
        edge_b = Edge(from_node="A", to_node="B", success_weight=9.0, failure_weight=1.0)
        edge_c = Edge(from_node="A", to_node="C", success_weight=1.0, failure_weight=9.0)

        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 10000

        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        # We expect B to be chosen overwhelmingly more often than C (exploitation)
        self.assertGreater(counts["B"], counts["C"] * 10)

        # We also expect C to be chosen occasionally (exploration)
        self.assertGreater(counts["C"], 0)


if __name__ == "__main__":
    unittest.main()
