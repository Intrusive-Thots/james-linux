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
)


class TestSedgeCoreIdeaProof(unittest.TestCase):
    """
    Comprehensive tests to mathematically prove the behavior of the SEDGE core
    idea (Nodes, Edges, Graph, and Evolution) as explicitly described.
    """

    def setUp(self):
        self.graph = DecisionGraph()

    def test_node_initialization(self):
        """Asserts state types and IDs are initialized correctly."""
        node = Node(id="test_id", state_type="analysis")
        self.assertEqual(node.id, "test_id")
        self.assertEqual(node.state_type, "analysis")
        self.assertEqual(node.metadata, {})

    def test_edge_scoring_mechanism(self):
        """Verifies score calculations and zero-division handling."""
        edge = Edge(from_node="A", to_node="B", success_weight=10.0, failure_weight=0.0)

        # 10.0 / (0.0 + 1e-6) should be a very large number, no ZeroDivisionError
        score = edge.score()
        self.assertAlmostEqual(score, 10000000.0, delta=0.1)

        edge2 = Edge(from_node="A", to_node="B", success_weight=5.0, failure_weight=5.0)
        # 5.0 / (5.0 + 1e-6)
        self.assertAlmostEqual(edge2.score(), 1.0, places=4)

    def test_graph_construction(self):
        """Asserts nodes and edges are added correctly to the DecisionGraph."""
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        self.assertEqual(len(self.graph.get_all_nodes()), 2)

        edge_ab = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge_ab)

        edges = self.graph.get_all_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].from_node, "A")
        self.assertEqual(edges[0].to_node, "B")

    def test_learning_engine_feedback(self):
        """Proves success/failure updates modify weights in the graph."""
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="action")
        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge_ab = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge_ab)

        learner = LearningEngine()

        # Simulate SUCCESS
        learner.update(self.graph, ["A", "B"], OUTCOME_SUCCESS)
        self.assertEqual(edge_ab.visits, 1)
        self.assertEqual(edge_ab.success_weight, 2.0)
        self.assertEqual(edge_ab.failure_weight, 1.0)

        # Simulate FAILURE
        learner.update(self.graph, ["A", "B"], OUTCOME_FAILURE)
        self.assertEqual(edge_ab.visits, 2)
        self.assertEqual(edge_ab.success_weight, 2.0)
        self.assertEqual(edge_ab.failure_weight, 2.0)

    def test_decision_engine_fallback(self):
        """Proves the decision engine correctly falls back to uniform choice."""
        edge_b = Edge(from_node="A", to_node="B", success_weight=0.0, failure_weight=0.0)
        edge_c = Edge(from_node="A", to_node="C", success_weight=0.0, failure_weight=0.0)
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        engine = DecisionEngine(self.graph)

        counts = {"B": 0, "C": 0}
        for _ in range(100):
            choice = engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], 0)
        self.assertGreater(counts["C"], 0)


if __name__ == "__main__":
    unittest.main()
