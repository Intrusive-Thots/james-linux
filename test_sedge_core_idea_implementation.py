import unittest
import random
from collections import Counter

from james.core.sedge import (
    Node, Edge, DecisionGraph, LearningEngine, DecisionEngine,
    SelfEvolvingAgent, build_parrot_wifi_graph
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
    ACTION_EVIL_TWIN_SIMULATION
)

class TestSedgeCoreIdeaImplementation(unittest.TestCase):

    def setUp(self):
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)

    def test_nodes_are_system_states_or_actions(self):
        """
        Verify that nodes properly represent system states or actions, mapping correctly.
        """
        start_node = self.graph.get_node(STATE_START)
        self.assertIsNotNone(start_node)
        self.assertEqual(start_node.state_type, "state")

        scan_action = self.graph.get_node(ACTION_PASSIVE_SCAN)
        self.assertIsNotNone(scan_action)
        self.assertEqual(scan_action.state_type, "action")

    def test_edges_are_transitions(self):
        """
        Verify that edges correctly act as transitions between decisions and store utility scores.
        """
        edges_from_discovery = self.graph.get_edges(STATE_NETWORK_DISCOVERY)
        self.assertTrue(any(e.to_node == ACTION_PASSIVE_SCAN for e in edges_from_discovery))

        # Check default weights
        edge = edges_from_discovery[0]
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertGreater(edge.score(), 0.0)

    def test_stochastic_learning_behavior(self):
        """
        Tests the stochastic weighted selection, validating that exploration and
        exploitation are naturally balanced over 1000 iterations to assure statistical stability.
        """
        graph = DecisionGraph()
        graph.add_node(Node("A", "state"))
        graph.add_node(Node("B", "action"))
        graph.add_node(Node("C", "action"))

        # B starts weak, C starts strong
        edge_ab = Edge("A", "B", success_weight=1.0, failure_weight=10.0)
        edge_ac = Edge("A", "C", success_weight=10.0, failure_weight=1.0)

        graph.add_edge(edge_ab)
        graph.add_edge(edge_ac)

        decision_engine = DecisionEngine(graph)

        choices = []
        iterations = 1000
        for _ in range(iterations):
            choices.append(decision_engine.decide("A"))

        counts = Counter(choices)

        # C should be chosen significantly more than B (Exploitation), but B should still be chosen occasionally (Exploration)
        self.assertGreater(counts["C"], counts["B"])
        self.assertGreater(counts["B"], 0, "Exploration path (B) was never chosen, missing stochastic property.")

    def test_optimal_strategies_emerge(self):
        """
        Simulates execution feedback to ensure successful paths become stronger
        and failed paths decay over time, validating optimal strategy emergence.
        """
        # Let's train the parrot graph
        # Path 1: START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS -> HANDSHAKE_CAPTURE -> SECURITY_PROFILING -> EVIL_TWIN
        # We will reward Path 1
        path1 = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_HANDSHAKE_CAPTURE,
            STATE_SECURITY_PROFILING,
            ACTION_EVIL_TWIN_SIMULATION
        ]

        # Path 2: START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS -> DEAUTH_TEST -> SECURITY_PROFILING -> EVIL_TWIN
        # We will punish Path 2
        path2 = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_DEAUTH_TEST,
            STATE_SECURITY_PROFILING,
            ACTION_EVIL_TWIN_SIMULATION
        ]

        learner = LearningEngine()

        # Train with 10 successes for Path 1 and 10 failures for Path 2
        for _ in range(10):
            learner.update(self.graph, path1, OUTCOME_SUCCESS)
            learner.update(self.graph, path2, OUTCOME_FAILURE)

        # After training, the best next from TARGET_ANALYSIS should definitively be HANDSHAKE_CAPTURE
        best_edge = self.graph.get_best_next(STATE_TARGET_ANALYSIS)
        self.assertEqual(best_edge.to_node, ACTION_HANDSHAKE_CAPTURE)

        # Check weights explicitly
        edges_from_analysis = self.graph.get_edges(STATE_TARGET_ANALYSIS)
        handshake_edge = next(e for e in edges_from_analysis if e.to_node == ACTION_HANDSHAKE_CAPTURE)
        deauth_edge = next(e for e in edges_from_analysis if e.to_node == ACTION_DEAUTH_TEST)

        self.assertGreater(handshake_edge.success_weight, deauth_edge.success_weight)
        self.assertGreater(deauth_edge.failure_weight, handshake_edge.failure_weight)
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

if __name__ == "__main__":
    unittest.main()
