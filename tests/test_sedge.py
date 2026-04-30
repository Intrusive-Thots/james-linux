import unittest
from james.core.sedge import Node, Edge, DecisionGraph, LearningEngine, DecisionEngine, SelfEvolvingAgent

class TestSedge(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.graph.add_node(Node("START", "state"))
        self.graph.add_node(Node("A", "action"))
        self.graph.add_node(Node("B", "action"))
        self.graph.add_edge(Edge("START", "A"))
        self.graph.add_edge(Edge("START", "B"))
        self.agent = SelfEvolvingAgent(self.graph)

    def test_node_creation(self):
        node = Node("TEST", "state", {"key": "value"})
        self.assertEqual(node.id, "TEST")
        self.assertEqual(node.state_type, "state")
        self.assertEqual(node.metadata, {"key": "value"})

    def test_edge_score(self):
        edge = Edge("A", "B", success_weight=2.0, failure_weight=1.0)
        self.assertAlmostEqual(edge.score(), 2.0 / (1.0 + 1e-6))

    def test_decision_graph(self):
        self.assertEqual(len(self.graph.nodes), 3)
        self.assertEqual(len(self.graph.edges["START"]), 2)

        # Test get_best_next with equal weights
        # It should return A because it's first and max() returns the first max
        self.assertEqual(self.graph.get_best_next("START"), "A")

    def test_learning_engine(self):
        engine = LearningEngine()
        engine.update(self.graph, ["START", "A"], success=True)
        edges = self.graph.edges["START"]
        edge_a = next(e for e in edges if e.to_node == "A")
        self.assertEqual(edge_a.success_weight, 2.0)
        self.assertEqual(edge_a.visits, 1)

        engine.update(self.graph, ["START", "B"], success=False)
        edge_b = next(e for e in edges if e.to_node == "B")
        self.assertEqual(edge_b.failure_weight, 2.0)
        self.assertEqual(edge_b.visits, 1)

    def test_decision_engine(self):
        engine = DecisionEngine(self.graph)

        # Make one path much more favorable
        self.graph.edges["START"][0].success_weight = 100.0 # Path to A
        self.graph.edges["START"][1].failure_weight = 100.0 # Path to B

        # With high probability it should pick A
        choices = [engine.decide("START") for _ in range(100)]
        self.assertTrue(choices.count("A") > choices.count("B"))

    def test_self_evolving_agent(self):
        self.assertEqual(self.agent.current_node, "START")

        # Step through the graph
        next_node = self.agent.step()
        self.assertIn(next_node, ["A", "B"])
        self.assertEqual(self.agent.current_node, next_node)

        # Provide feedback
        self.agent.feedback(success=True)

        # Check if episode reset
        self.assertEqual(self.agent.current_node, "START")
        self.assertEqual(self.agent.current_path, ["START"])

if __name__ == '__main__':
    unittest.main()
