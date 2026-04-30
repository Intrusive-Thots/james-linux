import unittest
from james.core.sedge import Node, Edge, DecisionGraph, LearningEngine, DecisionEngine, SelfEvolvingAgent

class TestSEDGE(unittest.TestCase):
    def test_edge_score(self):
        edge = Edge(from_node="A", to_node="B", success_weight=2.0, failure_weight=1.0)
        self.assertAlmostEqual(edge.score(), 2.0, places=5)

        edge2 = Edge(from_node="B", to_node="C", success_weight=1.0, failure_weight=0.0)
        self.assertAlmostEqual(edge2.score(), 1.0 / 1e-6, places=1)

    def test_decision_graph(self):
        graph = DecisionGraph()
        node = Node(id="START", state_type="state")
        graph.add_node(node)
        self.assertIn("START", graph.nodes)

        edge = Edge(from_node="START", to_node="END")
        graph.add_edge(edge)
        self.assertIn("START", graph.edges)
        self.assertEqual(len(graph.edges["START"]), 1)
        self.assertEqual(graph.edges["START"][0].to_node, "END")

    def test_learning_engine_update(self):
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="A", to_node="B"))
        graph.add_edge(Edge(from_node="B", to_node="C"))

        learner = LearningEngine()

        # Test success update
        learner.update(graph, ["A", "B", "C"], success=True)
        self.assertEqual(graph.edges["A"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["A"][0].failure_weight, 1.0)
        self.assertEqual(graph.edges["A"][0].visits, 1)

        # Test failure update
        learner.update(graph, ["A", "B"], success=False)
        self.assertEqual(graph.edges["A"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["A"][0].failure_weight, 2.0)
        self.assertEqual(graph.edges["A"][0].visits, 2)

    def test_decision_engine(self):
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="A", to_node="B", success_weight=10.0, failure_weight=1.0))
        graph.add_edge(Edge(from_node="A", to_node="C", success_weight=1.0, failure_weight=10.0))

        engine = DecisionEngine(graph)
        next_node = engine.decide("A")
        # Due to stochastic selection, it might occasionally choose C, but B is highly probable.
        # It should return a valid node string anyway
        self.assertIn(next_node, ["B", "C"])

        self.assertIsNone(engine.decide("C"))

if __name__ == "__main__":
    unittest.main()
