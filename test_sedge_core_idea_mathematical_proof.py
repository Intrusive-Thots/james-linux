import unittest
import math
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


class TestSedgeCoreIdeaMathematicalProof(unittest.TestCase):
    """
    Mathematical proof and comprehensive test suite for the SEDGE CORE IDEA.
    Proves that successful sequences (e.g. scan -> analyze -> handshake_capture -> validate)
    gain higher success_weight, failed sequences gain higher failure_weight, and optimal
    attack/analysis pipelines emerge automatically within the living decision ecosystem.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_mathematical_edge_scoring(self):
        """
        Proof of scoring mathematically mitigating zero division and scaling properly.
        """
        edge = Edge(from_node="A", to_node="B", success_weight=1.0, failure_weight=1.0)
        self.assertAlmostEqual(edge.score(), 0.999999, places=5)

        edge.success_weight = 5.0
        edge.failure_weight = 2.0
        self.assertAlmostEqual(edge.score(), 2.49999, places=4)

        edge.success_weight = 0.0
        edge.failure_weight = 0.0
        self.assertAlmostEqual(edge.score(), 0.0, places=5)

        edge.success_weight = 1.0
        edge.failure_weight = 0.0
        self.assertGreater(edge.score(), 999999)

    def test_mathematical_path_scoring(self):
        """
        Mathematical proof of average utility score across traversal paths.
        """
        edge1 = Edge(from_node="A", to_node="B", success_weight=3.0, failure_weight=1.0) # score ~ 3.0
        edge2 = Edge(from_node="B", to_node="C", success_weight=5.0, failure_weight=1.0) # score ~ 5.0

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        path = ["A", "B", "C"]
        score = self.graph.get_path_score(path)

        # Expected score: (3.0 + 5.0) / 2 = 4.0
        self.assertAlmostEqual(score, 4.0, delta=0.01)

        # Invalid path (broken link)
        path = ["A", "C"]
        self.assertEqual(self.graph.get_path_score(path), 0.0)

        # Path with fewer than 2 nodes
        self.assertEqual(self.graph.get_path_score(["A"]), 0.0)

    def test_mathematical_probability_convergence(self):
        """
        Proves that stochastic selection converges optimally with law of large numbers.
        This balances exploration (trying weak paths) vs exploitation (strong known paths).
        """
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(from_node="A", to_node="B", success_weight=80.0, failure_weight=1.0)
        edge_c = Edge(from_node="A", to_node="C", success_weight=20.0, failure_weight=1.0)

        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 250000

        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        ratio_b = counts["B"] / iterations
        ratio_c = counts["C"] / iterations

        # Expected ratios based on calculated mathematical scores
        score_b = edge_b.score()
        score_c = edge_c.score()
        total_score = score_b + score_c
        expected_b = score_b / total_score
        expected_c = score_c / total_score

        self.assertAlmostEqual(ratio_b, expected_b, delta=0.02)
        self.assertAlmostEqual(ratio_c, expected_c, delta=0.02)

    def test_learning_engine_backpropagation(self):
        """
        Mathematical validation of weight adjustment across nodes (EXECUTION FEEDBACK LEARNING).
        """
        edge1 = Edge(from_node="A", to_node="B")
        edge2 = Edge(from_node="B", to_node="C")

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        path = ["A", "B", "C"]

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge2.success_weight, 2.0)

        self.learner.update(self.graph, path, OUTCOME_PARTIAL)

        self.assertEqual(edge1.success_weight, 2.5)
        self.assertEqual(edge1.failure_weight, 1.5)
        self.assertEqual(edge2.success_weight, 2.5)
        self.assertEqual(edge2.failure_weight, 1.5)

    def test_sedge_parrot_system_emergent_optimal_strategy(self):
        """
        Mathematical proof of SEDGE behavior on the real domain map.
        Simulates 250000 runs to guarantee mathematical dominance of the successful path.
        This verifies the REAL EVOLUTION BEHAVIOR principles from the design:
        - graph converges toward optimal attack pipelines
        - unstable techniques decay
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        handshake_selections = 0
        deauth_selections = 0

        import random
        for _ in range(250000):
            # In our simulation:
            # ACTION_HANDSHAKE_CAPTURE has 90% success probability
            # ACTION_DEAUTH_TEST has 10% success probability

            outcome = OUTCOME_PARTIAL

            while True:
                node = agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    # Simulate 90% true mathematical success rate
                    outcome = OUTCOME_SUCCESS if random.random() < 0.90 else OUTCOME_FAILURE
                    break
                elif node == ACTION_DEAUTH_TEST:
                    # Simulate 10% true mathematical success rate
                    outcome = OUTCOME_SUCCESS if random.random() < 0.10 else OUTCOME_FAILURE
                    break

            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        # Mathematical Proof asserts
        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(handshake_edge.success_weight, 100)
        self.assertGreaterEqual(deauth_edge.failure_weight, 2)

        # Verify edge score mathematical dominance
        self.assertGreater(handshake_edge.score(), deauth_edge.score() * 10)

        # Ensure the graph is static during the sampling loop to test distribution mathematically
        decision_engine = DecisionEngine(graph)
        counts = {ACTION_HANDSHAKE_CAPTURE: 0, ACTION_DEAUTH_TEST: 0}
        iterations = 250000

        for _ in range(iterations):
            choice = decision_engine.decide(STATE_TARGET_ANALYSIS)
            if choice in counts:
                counts[choice] += 1

        ratio_handshake = counts[ACTION_HANDSHAKE_CAPTURE] / iterations
        ratio_deauth = counts[ACTION_DEAUTH_TEST] / iterations

        score_handshake = handshake_edge.score()
        score_deauth = deauth_edge.score()
        total_score = score_handshake + score_deauth

        expected_handshake = score_handshake / total_score
        expected_deauth = score_deauth / total_score

        self.assertAlmostEqual(ratio_handshake, expected_handshake, delta=0.02)
        self.assertAlmostEqual(ratio_deauth, expected_deauth, delta=0.02)


    def test_zero_utility_fallback_distribution(self):
        """
        Proof of uniform random selection fallback when total weight is <= 0.0.
        """
        decision_engine = DecisionEngine(self.graph)

        edge_x = Edge(from_node="A", to_node="X", success_weight=0.0, failure_weight=1.0)
        edge_y = Edge(from_node="A", to_node="Y", success_weight=0.0, failure_weight=1.0)
        edge_z = Edge(from_node="A", to_node="Z", success_weight=0.0, failure_weight=1.0)

        self.graph.add_edge(edge_x)
        self.graph.add_edge(edge_y)
        self.graph.add_edge(edge_z)

        counts = {"X": 0, "Y": 0, "Z": 0}
        iterations = 250000

        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        ratio_x = counts["X"] / iterations
        ratio_y = counts["Y"] / iterations
        ratio_z = counts["Z"] / iterations

        # Expected ratio: ~0.333 each
        self.assertAlmostEqual(ratio_x, 1/3, delta=0.02)
        self.assertAlmostEqual(ratio_y, 1/3, delta=0.02)
        self.assertAlmostEqual(ratio_z, 1/3, delta=0.02)

    def test_stochastic_fallback(self):
        """
        Tests the fallback to uniform random selection when all edge utilities are <= 0.0.
        This explicitly verifies that SEDGE falls back to uniform random selection when
        all edge utilities result in a sum <= 0.0, distributing selections roughly equally
        over a large number of iterations to test statistical stability.
        """
        decision_engine = DecisionEngine(self.graph)

        # Create edges with zero or negative utility
        # Note: According to Edge.score(), success_weight / (failure_weight + epsilon)
        # We can simulate <= 0 utility by setting success_weight to 0 or negative.
        edge_1 = Edge(from_node="A", to_node="Path1", success_weight=-1.0, failure_weight=1.0)
        edge_2 = Edge(from_node="A", to_node="Path2", success_weight=0.0, failure_weight=1.0)
        edge_3 = Edge(from_node="A", to_node="Path3", success_weight=-2.0, failure_weight=1.0)

        self.graph.add_edge(edge_1)
        self.graph.add_edge(edge_2)
        self.graph.add_edge(edge_3)

        counts = {"Path1": 0, "Path2": 0, "Path3": 0}
        iterations = 250000

        # When all edges have score <= 0.0, total weight will be <= 0.0
        # DecisionEngine should fallback to uniform random choice
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        ratio_1 = counts["Path1"] / iterations
        ratio_2 = counts["Path2"] / iterations
        ratio_3 = counts["Path3"] / iterations

        # Verify roughly equal distribution (~33.3% each)
        self.assertAlmostEqual(ratio_1, 1/3, delta=0.02)
        self.assertAlmostEqual(ratio_2, 1/3, delta=0.02)
        self.assertAlmostEqual(ratio_3, 1/3, delta=0.02)

    def test_exploration_vs_exploitation_decay(self):
        """
        Mathematical proof that failing paths naturally decay over time to balance
        exploration vs exploitation. Simulates repeated paths with failures for one edge
        to explicitly test its failure weight increasing and selection probability decaying.
        """
        decision_engine = DecisionEngine(self.graph)

        edge_exploit = Edge(from_node="A", to_node="Exploit", success_weight=10.0, failure_weight=1.0)
        edge_explore = Edge(from_node="A", to_node="Explore", success_weight=2.0, failure_weight=1.0)

        self.graph.add_edge(edge_exploit)
        self.graph.add_edge(edge_explore)

        initial_score_exploit = edge_exploit.score()
        initial_score_explore = edge_explore.score()

        self.assertEqual(initial_score_explore, 2.0 / (1.0 + 1e-6))

        # Simulate failures on the exploration path to decay it
        learner = LearningEngine()
        for _ in range(5):
            learner.update(self.graph, ["A", "Explore"], OUTCOME_FAILURE)

        final_score_explore = edge_explore.score()

        self.assertGreater(initial_score_explore, final_score_explore)
        self.assertEqual(edge_explore.failure_weight, 6.0)
        self.assertEqual(edge_explore.success_weight, 2.0)

        # Verify probability decay
        counts = {"Exploit": 0, "Explore": 0}
        iterations = 250000

        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        ratio_exploit = counts["Exploit"] / iterations
        ratio_explore = counts["Explore"] / iterations

        # Expected ratios based on calculated mathematical scores
        score_exploit = edge_exploit.score()
        score_explore = edge_explore.score()
        total_score = score_exploit + score_explore
        expected_exploit = score_exploit / total_score
        expected_explore = score_explore / total_score

        self.assertAlmostEqual(ratio_exploit, expected_exploit, delta=0.02)
        self.assertAlmostEqual(ratio_explore, expected_explore, delta=0.02)


if __name__ == '__main__':
    unittest.main()
