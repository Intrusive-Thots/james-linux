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


class TestSedgeCoreIdea(unittest.TestCase):
    """
    Tests for the SEDGE components to verify self-evolving behavior.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_state_node_model(self):
        node = Node(id="test_node", state_type="action")
        self.assertEqual(node.id, "test_node")
        self.assertEqual(node.state_type, "action")
        self.assertEqual(node.metadata, {})

    def test_edge_model(self):
        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)
        # 1.0 / (1.0 + 1e-6)
        self.assertAlmostEqual(edge.score(), 0.999999, places=5)

    def test_decision_graph_core(self):
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge = Edge(from_node="A", to_node="B", success_weight=5.0)
        self.graph.add_edge(edge)

        self.assertIn("A", self.graph.nodes)
        self.assertIn("B", self.graph.nodes)
        self.assertEqual(len(self.graph.edges.get("A", [])), 1)

        best_next = self.graph.get_best_next("A")
        self.assertIsNotNone(best_next)
        self.assertEqual(best_next.to_node, "B")

        self.assertIsNone(self.graph.get_best_next("B"))

    def test_learning_engine(self):
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)

        path = ["A", "B"]

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        self.assertEqual(edge.visits, 3)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)

    def test_decision_engine(self):
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=90.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], counts["C"] * 10)

    def test_self_evolving_loop_and_convergence(self):
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        iterations = 1000
        handshake_selections = 0
        deauth_selections = 0

        for _ in range(iterations):
            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    handshake_selections += 1
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    deauth_selections += 1
                    break

            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next(
            (
                e
                for e in analysis_edges
                if e.to_node == ACTION_HANDSHAKE_CAPTURE
            ),
            None,
        )
        deauth_edge = next(
            (e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST),
            None,
        )

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(
            handshake_edge.success_weight, deauth_edge.success_weight
        )
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        self.assertGreater(
            deauth_edge.failure_weight, handshake_edge.failure_weight
        )

        self.assertGreater(handshake_selections, deauth_selections)
        self.assertGreater(deauth_selections, 0)

    def test_edge_score_zero_division_prevention(self):
        edge = Edge(
            from_node="A", to_node="B", success_weight=1.0, failure_weight=0.0
        )
        # Should not raise ZeroDivisionError
        score = edge.score()
        self.assertGreater(score, 1000)  # Should be a very large number

    def test_decision_engine_zero_utility_fallback(self):
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=0.0, failure_weight=0.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=0.0, failure_weight=0.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        # When utility is zero for all, it should fallback to uniform random selection
        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        # Check that it falls back to uniform distribution roughly
        self.assertGreater(counts["B"], 100)
        self.assertGreater(counts["C"], 100)



    def test_learning_optimal_paths(self):
        """Test HOW IT LEARNS OPTIMAL PATHS - Over time successful sequences gain higher success_weight, failed gain higher failure_weight"""
        graph = DecisionGraph()
        agent = SelfEvolvingAgent(graph)

        node_a = Node(id="SCAN", state_type="state")
        node_b = Node(id="ANALYZE", state_type="state")
        node_c = Node(id="CAPTURE", state_type="action")
        node_d = Node(id="VALIDATE", state_type="action")
        node_e = Node(id="ATTACK", state_type="action")
        node_f = Node(id="FAIL", state_type="action")

        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_node(node_d)
        graph.add_node(node_e)
        graph.add_node(node_f)

        # Successful path edges
        graph.add_edge(Edge(from_node="SCAN", to_node="ANALYZE"))
        graph.add_edge(Edge(from_node="ANALYZE", to_node="CAPTURE"))
        graph.add_edge(Edge(from_node="CAPTURE", to_node="VALIDATE"))

        # Failed path edges
        graph.add_edge(Edge(from_node="SCAN", to_node="ATTACK"))
        graph.add_edge(Edge(from_node="ATTACK", to_node="FAIL"))

        # Train successful sequence
        for _ in range(10):
            agent.current_path = ["SCAN", "ANALYZE", "CAPTURE", "VALIDATE"]
            agent.feedback(OUTCOME_SUCCESS)

        # Train failed sequence
        for _ in range(10):
            agent.current_path = ["SCAN", "ATTACK", "FAIL"]
            agent.feedback(OUTCOME_FAILURE)

        scan_edges = graph.edges.get("SCAN", [])
        analyze_edge = next((e for e in scan_edges if e.to_node == "ANALYZE"), None)
        attack_edge = next((e for e in scan_edges if e.to_node == "ATTACK"), None)

        self.assertIsNotNone(analyze_edge)
        self.assertIsNotNone(attack_edge)

        # Successful path becomes stronger
        self.assertGreater(analyze_edge.success_weight, attack_edge.success_weight)
        # Failed path gains higher failure weight
        self.assertGreater(attack_edge.failure_weight, analyze_edge.failure_weight)
        # Higher score (stronger traversal probability) for successful path
        self.assertGreater(analyze_edge.score(), attack_edge.score())

    def test_exploration_exploitation_balance(self):
        """Test EXPLORATION vs EXPLOITATION - System naturally balances trying weak paths occasionally and using strong known paths"""
        graph = DecisionGraph()
        decision_engine = DecisionEngine(graph)

        node_a = Node(id="START", state_type="state")
        node_strong = Node(id="STRONG", state_type="action")
        node_weak = Node(id="WEAK", state_type="action")

        graph.add_node(node_a)
        graph.add_node(node_strong)
        graph.add_node(node_weak)

        # Strong path (exploitation candidate)
        edge_strong = Edge(from_node="START", to_node="STRONG", success_weight=90.0, failure_weight=1.0)
        # Weak path (exploration candidate)
        edge_weak = Edge(from_node="START", to_node="WEAK", success_weight=1.0, failure_weight=10.0)

        graph.add_edge(edge_strong)
        graph.add_edge(edge_weak)

        counts = {"STRONG": 0, "WEAK": 0}
        iterations = 10000
        for _ in range(iterations):
            choice = decision_engine.decide("START")
            counts[choice] += 1

        # Exploitation: Strong path should be chosen much more often
        self.assertGreater(counts["STRONG"], counts["WEAK"] * 5)
        # Exploration: Weak path should still be chosen occasionally (not zero)
        self.assertGreater(counts["WEAK"], 0)

if __name__ == "__main__":
    unittest.main()
