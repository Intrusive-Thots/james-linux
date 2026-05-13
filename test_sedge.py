import unittest

from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()

        # Add basic states
        self.graph.add_node(Node(id="START", state_type="start"))
        self.graph.add_node(Node(id="A", state_type="action"))
        self.graph.add_node(Node(id="B", state_type="action"))
        self.graph.add_node(Node(id="END", state_type="end"))

        # Add edges
        self.graph.add_edge(Edge(from_node="START", to_node="A"))
        self.graph.add_edge(Edge(from_node="START", to_node="B"))
        self.graph.add_edge(Edge(from_node="A", to_node="END"))
        self.graph.add_edge(Edge(from_node="B", to_node="END"))

    def test_graph_creation(self):
        self.assertIn("START", self.graph.nodes)
        self.assertEqual(len(self.graph.edges["START"]), 2)

    def test_learning_weight_updates(self):
        learner = LearningEngine()

        # Simulate successful path START -> A -> END
        path = ["START", "A", "END"]
        learner.update(self.graph, path, success=True)

        # Verify success_weight is increased
        edges_start = self.graph.edges.get("START", [])
        edge_a = next(e for e in edges_start if e.to_node == "A")
        self.assertEqual(edge_a.success_weight, 2.0)
        self.assertEqual(edge_a.failure_weight, 1.0)
        self.assertEqual(edge_a.visits, 1)

        # Simulate failed path START -> B -> END
        path2 = ["START", "B", "END"]
        learner.update(self.graph, path2, success=False)

        # Verify failure_weight is increased
        edge_b = next(e for e in edges_start if e.to_node == "B")
        self.assertEqual(edge_b.success_weight, 1.0)
        self.assertEqual(edge_b.failure_weight, 2.0)
        self.assertEqual(edge_b.visits, 1)

    def test_agent_feedback_loop(self):
        agent = SelfEvolvingAgent(self.graph)

        # Step through
        next_node = agent.step()
        self.assertIn(next_node, ["A", "B"])

        agent.step()  # Reach END
        self.assertEqual(agent.current_node, "END")

        # Feedback success
        agent.feedback(success=True)

        # Verify reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == "__main__":
    unittest.main()
