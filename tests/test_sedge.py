import unittest
from james.core.sedge.models import Node, Edge
from james.core.sedge.graph import DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSedge(unittest.TestCase):
    def test_edge_score(self):
        edge = Edge(
            from_node="A", to_node="B", success_weight=10.0, failure_weight=2.0
        )
        # Should be approx 10.0 / 2.0 = 5.0
        self.assertAlmostEqual(edge.score(), 5.0, places=4)

        edge_zero_fail = Edge(
            from_node="A", to_node="B", success_weight=5.0, failure_weight=0.0
        )
        # Should handle divide by zero with 1e-6: 5.0 / 1e-6 = 5000000.0
        self.assertAlmostEqual(edge_zero_fail.score(), 5000000.0, places=1)

    def test_decision_graph(self):
        graph = DecisionGraph()
        node_a = Node(id="A", state_type="start")
        node_b = Node(id="B", state_type="action")

        graph.add_node(node_a)
        graph.add_node(node_b)

        self.assertIn("A", graph.nodes)
        self.assertIn("B", graph.nodes)

        edge1 = Edge(from_node="A", to_node="B", success_weight=2.0)
        edge2 = Edge(from_node="A", to_node="C", success_weight=5.0)

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        self.assertEqual(len(graph.edges["A"]), 2)

        best = graph.get_best_next("A")
        self.assertEqual(best.to_node, "C")

        best_none = graph.get_best_next("C")
        self.assertIsNone(best_none)

    def test_learning_engine(self):
        graph = DecisionGraph()
        edge1 = Edge(from_node="START", to_node="SCAN")
        edge2 = Edge(from_node="SCAN", to_node="ATTACK")
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        learner = LearningEngine()
        path = ["START", "SCAN", "ATTACK"]

        learner.update(graph, path, success=True)
        self.assertEqual(edge1.visits, 1)
        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge1.failure_weight, 1.0)
        self.assertEqual(edge2.visits, 1)
        self.assertEqual(edge2.success_weight, 2.0)

        learner.update(graph, path, success=False)
        self.assertEqual(edge1.visits, 2)
        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge1.failure_weight, 2.0)

    def test_decision_engine(self):
        graph = DecisionGraph()
        edge1 = Edge(
            from_node="A", to_node="B", success_weight=1.0, failure_weight=1.0
        )
        edge2 = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=1.0
        )
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        policy = DecisionEngine(graph)

        # Test it returns one of the candidates
        next_node = policy.decide("A")
        self.assertIn(next_node, ["B", "C"])

        # Test empty candidates
        self.assertIsNone(policy.decide("B"))

    def test_self_evolving_agent(self):
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="START", to_node="SCAN"))
        graph.add_edge(Edge(from_node="SCAN", to_node="ATTACK"))

        agent = SelfEvolvingAgent(graph)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        step1 = agent.step()
        self.assertEqual(step1, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        step2 = agent.step()
        self.assertEqual(step2, "ATTACK")
        self.assertEqual(agent.current_node, "ATTACK")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ATTACK"])

        step3 = agent.step()
        self.assertEqual(step3, "halt")

        # Give feedback
        agent.feedback(success=True)

        # Verify reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Verify learning happened
        scan_edge = graph.edges["START"][0]
        self.assertEqual(scan_edge.visits, 1)
        self.assertEqual(scan_edge.success_weight, 2.0)


if __name__ == "__main__":
    unittest.main()
