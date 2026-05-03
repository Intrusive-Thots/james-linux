import unittest
from james.core.sedge import (
    Node, Edge, DecisionGraph, LearningEngine,
    DecisionEngine, SelfEvolvingAgent
)


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.node_start = Node(id="START", state_type="scan")
        self.node_a = Node(id="A", state_type="analysis")
        self.node_b = Node(id="B", state_type="action")
        self.graph.add_node(self.node_start)
        self.graph.add_node(self.node_a)
        self.graph.add_node(self.node_b)

        self.edge_start_a = Edge(from_node="START", to_node="A")
        self.edge_start_b = Edge(from_node="START", to_node="B")
        self.graph.add_edge(self.edge_start_a)
        self.graph.add_edge(self.edge_start_b)

    def test_decision_graph(self):
        self.assertEqual(len(self.graph.nodes), 3)
        self.assertEqual(len(self.graph.edges["START"]), 2)
        best_edge = self.graph.get_best_next("START")
        self.assertIsNotNone(best_edge)
        self.assertIn(best_edge.to_node, ["A", "B"])

    def test_learning_engine_success(self):
        learner = LearningEngine()
        learner.update(self.graph, ["START", "A"], success=True)
        self.assertEqual(self.edge_start_a.visits, 1)
        self.assertEqual(self.edge_start_a.success_weight, 2.0)
        self.assertEqual(self.edge_start_a.failure_weight, 1.0)
        self.assertEqual(self.edge_start_b.visits, 0)
        self.assertEqual(self.edge_start_b.success_weight, 1.0)

    def test_learning_engine_failure(self):
        learner = LearningEngine()
        learner.update(self.graph, ["START", "B"], success=False)
        self.assertEqual(self.edge_start_b.visits, 1)
        self.assertEqual(self.edge_start_b.success_weight, 1.0)
        self.assertEqual(self.edge_start_b.failure_weight, 2.0)

    def test_decision_engine(self):
        engine = DecisionEngine(self.graph)
        # Make 'A' highly preferable
        self.edge_start_a.success_weight = 1000.0
        self.edge_start_b.success_weight = 0.001
        # Due to weighted random choice, A should be chosen almost exclusively
        choices = [engine.decide("START") for _ in range(100)]
        self.assertIn("A", choices)

    def test_self_evolving_agent(self):
        agent = SelfEvolvingAgent(self.graph)
        # Step
        next_node = agent.step()
        self.assertIn(next_node, ["A", "B"])
        self.assertEqual(agent.current_path, ["START", next_node])
        # Feedback
        agent.feedback(success=True)
        # Verify reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Verify learning was applied
        if next_node == "A":
            edge_used = self.edge_start_a
        else:
            edge_used = self.edge_start_b

        self.assertEqual(edge_used.visits, 1)
        self.assertEqual(edge_used.success_weight, 2.0)


if __name__ == "__main__":
    unittest.main()
