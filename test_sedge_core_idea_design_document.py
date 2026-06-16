import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
    build_parrot_wifi_graph
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    ACTION_PASSIVE_SCAN,
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    STATE_SECURITY_PROFILING,
)


class TestSEDGECoreIdeaDesignDocument(unittest.TestCase):
    """
    Comprehensive tests targeting the SEDGE CORE IDEA from the design document.
    Verifies that Node, Edge, DecisionGraph, LearningEngine, DecisionEngine,
    SelfEvolvingAgent, and build_parrot_wifi_graph work as intended.
    """

    def test_node_model(self):
        """Test STATE NODE MODEL from the design document."""
        node = Node(
            id="test_node",
            state_type="state",
            metadata={"key": "value"}
        )
        self.assertEqual(node.id, "test_node")
        self.assertEqual(node.state_type, "state")
        self.assertEqual(node.metadata, {"key": "value"})

    def test_edge_model(self):
        """Test EDGE MODEL (LEARNING PATHS) from the design document."""
        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)
        self.assertAlmostEqual(edge.score(), 0.9999990000010001, places=6)

    def test_decision_graph_core(self):
        """Test DECISION GRAPH CORE from the design document."""
        graph = DecisionGraph()
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        edge = Edge(from_node="A", to_node="B")

        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(edge)

        self.assertEqual(graph.get_node("A"), node_a)
        self.assertEqual(graph.get_node("B"), node_b)
        self.assertEqual(graph.get_edges("A"), [edge])
        self.assertEqual(graph.get_best_next("A"), edge)

    def test_execution_feedback_learning(self):
        """Test EXECUTION FEEDBACK LEARNING from the design document."""
        graph = DecisionGraph()
        graph.add_node(Node(id="A", state_type="state"))
        graph.add_node(Node(id="B", state_type="action"))
        graph.add_node(Node(id="C", state_type="state"))

        edge_ab = Edge(from_node="A", to_node="B")
        edge_bc = Edge(from_node="B", to_node="C")
        graph.add_edge(edge_ab)
        graph.add_edge(edge_bc)

        learner = LearningEngine()
        path = ["A", "B", "C"]

        # Test success update
        learner.update(graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge_ab.visits, 1)
        self.assertEqual(edge_ab.success_weight, 2.0)
        self.assertEqual(edge_bc.visits, 1)
        self.assertEqual(edge_bc.success_weight, 2.0)

        # Test failure update
        learner.update(graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge_ab.visits, 2)
        self.assertEqual(edge_ab.failure_weight, 2.0)
        self.assertEqual(edge_bc.visits, 2)
        self.assertEqual(edge_bc.failure_weight, 2.0)

    def test_decision_engine_policy_layer(self):
        """Test DECISION ENGINE (POLICY LAYER) from the design document."""
        graph = DecisionGraph()
        graph.add_node(Node(id="A", state_type="state"))
        graph.add_node(Node(id="B", state_type="action"))
        graph.add_node(Node(id="C", state_type="action"))

        # Edge A->B has high success, A->C has high failure
        edge_ab = Edge(
            from_node="A", to_node="B",
            success_weight=100.0, failure_weight=1.0
        )
        edge_ac = Edge(
            from_node="A", to_node="C",
            success_weight=1.0, failure_weight=100.0
        )

        graph.add_edge(edge_ab)
        graph.add_edge(edge_ac)

        engine = DecisionEngine(graph)

        # Stochastic selection should heavily favor B over C
        b_count = 0
        c_count = 0
        iterations = 1000
        for _ in range(iterations):
            decision = engine.decide("A")
            if decision == "B":
                b_count += 1
            elif decision == "C":
                c_count += 1

        self.assertGreater(b_count, c_count)

    def test_self_evolution_loop(self):
        """Test SELF-EVOLUTION LOOP from the design document."""
        graph = DecisionGraph()
        graph.add_node(Node(id=STATE_START, state_type="state"))
        graph.add_node(Node(id="B", state_type="action"))

        edge_start_b = Edge(from_node=STATE_START, to_node="B")
        graph.add_edge(edge_start_b)

        agent = SelfEvolvingAgent(graph)

        self.assertEqual(agent.current_node, STATE_START)
        self.assertEqual(agent.current_path, [STATE_START])

        next_node = agent.step()
        self.assertEqual(next_node, "B")
        self.assertEqual(agent.current_node, "B")
        self.assertEqual(agent.current_path, [STATE_START, "B"])

        agent.feedback(OUTCOME_SUCCESS)
        self.assertEqual(agent.current_node, STATE_START)
        self.assertEqual(agent.current_path, [STATE_START])

        self.assertEqual(edge_start_b.visits, 1)
        self.assertEqual(edge_start_b.success_weight, 2.0)

    def test_parrot_wifi_system_mapping(self):
        """Test HOW THIS MAPS TO PARROT WIFI SYSTEM from design document."""
        graph = build_parrot_wifi_graph()

        # Verify States
        self.assertIsNotNone(graph.get_node(STATE_START))
        self.assertIsNotNone(graph.get_node(STATE_NETWORK_DISCOVERY))
        self.assertIsNotNone(graph.get_node(STATE_TARGET_ANALYSIS))
        self.assertIsNotNone(graph.get_node(STATE_SECURITY_PROFILING))

        # Verify Actions
        self.assertIsNotNone(graph.get_node(ACTION_PASSIVE_SCAN))
        self.assertIsNotNone(graph.get_node(ACTION_HANDSHAKE_CAPTURE))

        # Verify Edge mapping (Sequence: START -> Network Discovery)
        edges = graph.get_edges(STATE_START)
        has_net = any(e.to_node == STATE_NETWORK_DISCOVERY for e in edges)
        self.assertTrue(has_net)


if __name__ == '__main__':
    unittest.main()
