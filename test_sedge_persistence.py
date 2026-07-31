import unittest
import os
import json
from james.core.sedge import Node, Edge, DecisionGraph

class TestSedgePersistence(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="SCAN", state_type="action"))
        self.graph.add_edge(Edge(from_node="START", to_node="SCAN", success_weight=5.0, visits=3))
        self.filepath = "/tmp/test_sedge_graph.json"

    def tearDown(self):
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    def test_to_dict_from_dict(self):
        data = self.graph.to_dict()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

        new_graph = DecisionGraph.from_dict(data)
        self.assertIn("START", new_graph.nodes)
        self.assertEqual(len(new_graph.get_all_edges()), 1)
        self.assertEqual(new_graph.get_all_edges()[0].success_weight, 5.0)

    def test_save_load(self):
        self.graph.save(self.filepath)
        self.assertTrue(os.path.exists(self.filepath))

        new_graph = DecisionGraph()
        new_graph.load(self.filepath)

        self.assertIn("SCAN", new_graph.nodes)
        self.assertEqual(new_graph.get_all_edges()[0].visits, 3)

    def test_export_mermaid(self):
        mermaid = self.graph.export_mermaid()
        self.assertIn("stateDiagram-v2", mermaid)
        self.assertIn("START --> SCAN", mermaid)

if __name__ == "__main__":
    unittest.main()
