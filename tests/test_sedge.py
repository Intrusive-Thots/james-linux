import unittest
from james.core.sedge import Node, Edge, DecisionGraph, LearningEngine, DecisionEngine, SelfEvolvingAgent

class TestSedge(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()

        # Add some nodes
        self.graph.add_node(Node("START", "state"))
        self.graph.add_node(Node("SCAN", "action"))
        self.graph.add_node(Node("ANALYZE", "analysis"))
        self.graph.add_node(Node("ATTACK", "action"))

        # Add some edges
        self.graph.add_edge(Edge("START", "SCAN"))
        self.graph.add_edge(Edge("SCAN", "ANALYZE"))
        self.graph.add_edge(Edge("ANALYZE", "ATTACK"))
        self.graph.add_edge(Edge("ATTACK", "START"))

    def test_decision_graph(self):
        best = self.graph.get_best_next("START")
        self.assertIsNotNone(best)
        self.assertEqual(best.to_node, "SCAN")

    def test_learning_engine(self):
        engine = LearningEngine()
        path = ["START", "SCAN", "ANALYZE"]

        # Initial score
        scan_edge = self.graph.edges["START"][0]
        self.assertEqual(scan_edge.success_weight, 1.0)
        self.assertEqual(scan_edge.failure_weight, 1.0)

        # Update with success
        engine.update(self.graph, path, True)
        self.assertEqual(scan_edge.success_weight, 2.0)
        self.assertEqual(scan_edge.failure_weight, 1.0)
        self.assertEqual(scan_edge.visits, 1)

        # Update with failure
        engine.update(self.graph, path, False)
        self.assertEqual(scan_edge.success_weight, 2.0)
        self.assertEqual(scan_edge.failure_weight, 2.0)
        self.assertEqual(scan_edge.visits, 2)

    def test_decision_engine(self):
        engine = DecisionEngine(self.graph)
        next_node = engine.decide("START")
        self.assertEqual(next_node, "SCAN")

    def test_self_evolving_agent(self):
        agent = SelfEvolvingAgent(self.graph)

        self.assertEqual(agent.current_node, "START")

        next_node = agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        next_node = agent.step()
        self.assertEqual(next_node, "ANALYZE")

        agent.feedback(True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Check weights updated
        scan_edge = self.graph.edges["START"][0]
        self.assertEqual(scan_edge.success_weight, 2.0)
        self.assertEqual(scan_edge.failure_weight, 1.0)

if __name__ == '__main__':
    unittest.main()
