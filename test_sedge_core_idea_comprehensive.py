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


class TestSedgeCoreIdeaComprehensive(unittest.TestCase):
    """
    Comprehensive tests for the SEDGE CORE IDEA to verify self-evolving behavior,
    exploration vs exploitation, and optimal strategy emergence.
    """

    def setUp(self):
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)
        self.learner = LearningEngine()

    def test_get_path_score(self):
        """Verify the newly added get_path_score method calculates correctly."""
        path = [STATE_START, STATE_NETWORK_DISCOVERY, ACTION_PASSIVE_SCAN]
        # Initial score for all edges should be 1.0
        score = self.graph.get_path_score(path)
        self.assertAlmostEqual(score, 1.0, places=5)

        # Test broken path
        broken_path = [STATE_START, ACTION_PASSIVE_SCAN]
        self.assertEqual(self.graph.get_path_score(broken_path), 0.0)

        # Test short path
        self.assertEqual(self.graph.get_path_score([STATE_START]), 0.0)

    def test_failed_paths_decay(self):
        """Verify that failed paths decay over time."""
        path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_DEAUTH_TEST
        ]

        initial_score = self.graph.get_path_score(path)

        # Apply failure feedback multiple times
        for _ in range(5):
            self.learner.update(self.graph, path, OUTCOME_FAILURE)

        decayed_score = self.graph.get_path_score(path)

        self.assertLess(decayed_score, initial_score)

        # Verify the specific edge
        edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        deauth_edge = next((e for e in edges if e.to_node == ACTION_DEAUTH_TEST), None)
        self.assertIsNotNone(deauth_edge)
        self.assertEqual(deauth_edge.failure_weight, 6.0) # 1.0 init + 5.0 updates

    def test_successful_paths_become_stronger(self):
        """Verify that successful paths become stronger over time."""
        path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_HANDSHAKE_CAPTURE
        ]

        initial_score = self.graph.get_path_score(path)

        # Apply success feedback multiple times
        for _ in range(5):
            self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        stronger_score = self.graph.get_path_score(path)

        self.assertGreater(stronger_score, initial_score)

        # Verify the specific edge
        edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        self.assertIsNotNone(handshake_edge)
        self.assertEqual(handshake_edge.success_weight, 6.0) # 1.0 init + 5.0 updates

    def test_exploration_vs_exploitation(self):
        """Verify the system balances exploration and exploitation."""
        decision_engine = DecisionEngine(self.graph)

        # Make Handshake Capture strong (Exploitation target)
        # Make Deauth Test weak (Exploration target)
        edges = self.graph.edges.get(STATE_TARGET_ANALYSIS, [])
        for e in edges:
            if e.to_node == ACTION_HANDSHAKE_CAPTURE:
                e.success_weight = 10.0
                e.failure_weight = 1.0
            elif e.to_node == ACTION_DEAUTH_TEST:
                e.success_weight = 1.0
                e.failure_weight = 10.0

        # Run stochastic selection
        counts = {ACTION_HANDSHAKE_CAPTURE: 0, ACTION_DEAUTH_TEST: 0}
        iterations = 10000
        for _ in range(iterations):
            choice = decision_engine.decide(STATE_TARGET_ANALYSIS)
            if choice in counts:
                counts[choice] += 1

        # Handshake should be selected much more often (Exploitation)
        self.assertGreater(counts[ACTION_HANDSHAKE_CAPTURE], counts[ACTION_DEAUTH_TEST] * 50)

        # But Deauth should still be selected occasionally (Exploration)
        self.assertGreater(counts[ACTION_DEAUTH_TEST], 0)

    def test_real_evolution_behavior(self):
        """Verify optimal strategies emerge automatically over time."""
        iterations = 1000

        # Simulate an environment where handshake capture always works
        # and deauth always fails
        for _ in range(iterations):
            # Run until action is taken
            action_taken = None
            while True:
                node = self.agent.step()
                if node == "halt":
                    break
                if node in [ACTION_HANDSHAKE_CAPTURE, ACTION_DEAUTH_TEST]:
                    action_taken = node
                    break

            if action_taken == ACTION_HANDSHAKE_CAPTURE:
                self.agent.feedback(OUTCOME_SUCCESS)
            elif action_taken == ACTION_DEAUTH_TEST:
                self.agent.feedback(OUTCOME_FAILURE)
            else:
                self.agent.feedback(OUTCOME_PARTIAL)

        # After evolution, path favoring handshake should be dominant
        optimal_path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_HANDSHAKE_CAPTURE
        ]

        suboptimal_path = [
            STATE_START,
            STATE_NETWORK_DISCOVERY,
            ACTION_PASSIVE_SCAN,
            STATE_TARGET_ANALYSIS,
            ACTION_DEAUTH_TEST
        ]

        optimal_score = self.graph.get_path_score(optimal_path)
        suboptimal_score = self.graph.get_path_score(suboptimal_path)

        self.assertGreater(optimal_score, suboptimal_score)

if __name__ == '__main__':
    unittest.main()
