import unittest
from james.core.sedge import Node, Edge


class TestSedgeEdgeCases(unittest.TestCase):
    def test_node_default_metadata(self):
        node = Node(id="TEST1", state_type="scan")
        self.assertEqual(node.id, "TEST1")
        self.assertEqual(node.state_type, "scan")
        self.assertEqual(node.metadata, {})

    def test_node_with_metadata(self):
        meta = {"target": "192.168.1.1"}
        node = Node(id="TEST2", state_type="analysis", metadata=meta)
        self.assertEqual(node.metadata, {"target": "192.168.1.1"})

    def test_edge_default_score(self):
        edge = Edge(from_node="A", to_node="B")
        # default success_weight is 1.0, failure_weight is 1.0
        # formula: 1.0 / (1.0 + 1e-6)
        expected_score = 1.0 / (1.0 + 1e-6)
        self.assertAlmostEqual(edge.score(), expected_score)

    def test_edge_zero_failure_weight(self):
        edge = Edge(from_node="A", to_node="B", failure_weight=0.0)
        # formula: 1.0 / (0.0 + 1e-6) = 1,000,000.0
        expected_score = 1.0 / 1e-6
        self.assertAlmostEqual(edge.score(), expected_score)

    def test_edge_zero_success_weight(self):
        edge = Edge(from_node="A", to_node="B", success_weight=0.0)
        self.assertEqual(edge.score(), 0.0)


if __name__ == "__main__":
    unittest.main()
