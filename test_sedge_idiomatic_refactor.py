import unittest

from james.core.sedge import DecisionGraph, LearningEngine, Node, Edge
from james.tools.constants import OUTCOME_SUCCESS, OUTCOME_FAILURE


class TestSedgeIdiomaticRefactor(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

        # Add Nodes
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="A", state_type="action"))
        self.graph.add_node(Node(id="B", state_type="state"))
        self.graph.add_node(Node(id="C", state_type="action"))

        # Add Edges (testing the refactored add_edge)
        self.edge_start_a = Edge(from_node="START", to_node="A")
        self.edge_a_b = Edge(from_node="A", to_node="B")
        self.edge_b_c = Edge(from_node="B", to_node="C")

        self.graph.add_edge(self.edge_start_a)
        self.graph.add_edge(self.edge_a_b)
        self.graph.add_edge(self.edge_b_c)

    def test_add_edge_idiomatic(self):
        """Test that the setdefault logic in add_edge correctly handles dictionary insertions."""
        self.assertIn("START", self.graph.edges)
        self.assertEqual(len(self.graph.edges["START"]), 1)
        self.assertEqual(self.graph.edges["START"][0].to_node, "A")

        self.assertIn("A", self.graph.edges)
        self.assertEqual(len(self.graph.edges["A"]), 1)
        self.assertEqual(self.graph.edges["A"][0].to_node, "B")

        # Test adding another edge from START
        edge_start_b = Edge(from_node="START", to_node="B")
        self.graph.add_edge(edge_start_b)
        self.assertEqual(len(self.graph.edges["START"]), 2)
        self.assertEqual(self.graph.edges["START"][1].to_node, "B")

    def test_update_idiomatic_success(self):
        """Test that the zip() logic in update correctly iterates and updates edge weights on success."""
        path = ["START", "A", "B"]
        initial_visits = self.edge_start_a.visits
        initial_success = self.edge_start_a.success_weight

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        self.assertEqual(self.edge_start_a.visits, initial_visits + 1)
        self.assertEqual(self.edge_start_a.success_weight, initial_success + 1.0)

        self.assertEqual(self.edge_a_b.visits, initial_visits + 1)
        self.assertEqual(self.edge_a_b.success_weight, initial_success + 1.0)

        # Unvisited edge should remain unchanged
        self.assertEqual(self.edge_b_c.visits, 0)
        self.assertEqual(self.edge_b_c.success_weight, 1.0)

    def test_update_idiomatic_failure(self):
        """Test that the zip() logic in update correctly iterates and updates edge weights on failure."""
        path = ["START", "A", "B"]
        initial_visits = self.edge_start_a.visits
        initial_failure = self.edge_start_a.failure_weight

        self.learner.update(self.graph, path, OUTCOME_FAILURE)

        self.assertEqual(self.edge_start_a.visits, initial_visits + 1)
        self.assertEqual(self.edge_start_a.failure_weight, initial_failure + 1.0)

        self.assertEqual(self.edge_a_b.visits, initial_visits + 1)
        self.assertEqual(self.edge_a_b.failure_weight, initial_failure + 1.0)

        # Unvisited edge should remain unchanged
        self.assertEqual(self.edge_b_c.visits, 0)
        self.assertEqual(self.edge_b_c.failure_weight, 1.0)


if __name__ == "__main__":
    unittest.main()
