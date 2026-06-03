import unittest
import random
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


class TestSedgeCoreIdeaVerification(unittest.TestCase):
    """
    Comprehensive tests validating the core ideas of the
    Self-Evolving Decision Graph Engine (SEDGE).
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_directed_weighted_graph_construction(self):
        """
        Prove that the system builds a directed weighted decision graph where
        Nodes = states/actions, Edges = transitions, Weights = learned success scores.
        """
        node_start = Node(id="start", state_type="state")
        node_act1 = Node(id="action1", state_type="action")
        node_act2 = Node(id="action2", state_type="action")

        self.graph.add_node(node_start)
        self.graph.add_node(node_act1)
        self.graph.add_node(node_act2)

        edge1 = Edge(from_node="start", to_node="action1", success_weight=5.0, failure_weight=1.0)
        edge2 = Edge(from_node="start", to_node="action2", success_weight=1.0, failure_weight=5.0)

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        edges_from_start = self.graph.get_edges("start")
        self.assertEqual(len(edges_from_start), 2)

        # Verify directed nature
        edges_from_act1 = self.graph.get_edges("action1")
        self.assertEqual(len(edges_from_act1), 0)

        # Verify weights
        score1 = edge1.score()
        score2 = edge2.score()
        self.assertGreater(score1, score2)
        self.assertAlmostEqual(score1, 5.0, places=4)

    def test_learning_feedback_updates(self):
        """
        Prove that over time, successful paths become stronger and failed paths decay.
        """
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)
        path = ["A", "B"]

        initial_score = edge.score()

        # Success increases score
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        score_after_success = edge.score()
        self.assertGreater(score_after_success, initial_score)

        # Failure decreases score
        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        score_after_failure = edge.score()
        self.assertLess(score_after_failure, score_after_success)

        # Partial restores slightly
        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        score_after_partial = edge.score()
        self.assertGreater(score_after_partial, score_after_failure)


    def test_stochastic_exploration_exploitation(self):
        """
        Prove the policy layer uses stochastic weighted selections to naturally balance
        exploration (trying weak paths occasionally) and exploitation (using strong known paths).
        """
        engine = DecisionEngine(self.graph)

        edge_strong = Edge(from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0) # score ~ 90
        edge_weak = Edge(from_node="A", to_node="C", success_weight=10.0, failure_weight=1.0) # score ~ 10
        self.graph.add_edge(edge_strong)
        self.graph.add_edge(edge_weak)

        results = {"B": 0, "C": 0}
        trials = 10000

        for _ in range(trials):
            choice = engine.decide("A")
            results[choice] += 1

        # We expect a roughly 90/10 split
        # Verify exploitation (strong path chosen more)
        self.assertGreater(results["B"], results["C"] * 5)
        # Verify exploration (weak path chosen occasionally, not zero)
        self.assertGreater(results["C"], 500)

    def test_parrot_wifi_system_convergence(self):
        """
        Prove the graph converges toward optimal attack/analysis pipelines
        for the Parrot WiFi system. High-yield workflows become dominant.
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # Simulate environment where Handshake Capture is highly successful
        # and Deauth Test mostly fails

        for _ in range(500):
            agent.reset()
            while True:
                node = agent.step()
                if node == "halt":
                    break

                # Assign outcomes when action nodes are hit
                if node == ACTION_HANDSHAKE_CAPTURE:
                    agent.feedback(OUTCOME_SUCCESS)
                    break
                elif node == ACTION_DEAUTH_TEST:
                    # 90% chance of failure for deauth
                    if random.random() < 0.9:
                        agent.feedback(OUTCOME_FAILURE)
                    else:
                        agent.feedback(OUTCOME_SUCCESS)
                    break


        # Evaluate resulting graph edge scores
        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])

        edge_handshake = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        edge_deauth = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(edge_handshake)
        self.assertIsNotNone(edge_deauth)

        # Verify convergence: high-yield workflow became dominant
        self.assertGreater(edge_handshake.score(), edge_deauth.score() * 2)

if __name__ == '__main__':
    unittest.main()
