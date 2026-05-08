import unittest
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.graph.add_node(Node(id="START", state_type="start"))
        self.graph.add_node(Node(id="SCAN", state_type="action"))
        self.graph.add_node(Node(id="ATTACK_1", state_type="action"))
        self.graph.add_node(Node(id="ATTACK_2", state_type="action"))

        self.edge1 = Edge(from_node="START", to_node="SCAN")
        self.edge2 = Edge(from_node="SCAN", to_node="ATTACK_1")
        self.edge3 = Edge(from_node="SCAN", to_node="ATTACK_2")

        self.graph.add_edge(self.edge1)
        self.graph.add_edge(self.edge2)
        self.graph.add_edge(self.edge3)

        self.agent = SelfEvolvingAgent(self.graph)

    def test_graph_creation(self):
        self.assertIn("START", self.graph.nodes)
        self.assertEqual(len(self.graph.edges["SCAN"]), 2)

    def test_step_execution(self):
        next_node = self.agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(self.agent.current_path, ["START", "SCAN"])

        next_node = self.agent.step()
        self.assertIn(next_node, ["ATTACK_1", "ATTACK_2"])

    def test_feedback_learning(self):
        # Force a path
        self.agent.current_path = ["START", "SCAN", "ATTACK_1"]
        self.agent.feedback(success=True)

        self.assertEqual(self.agent.current_node, "START")
        self.assertEqual(self.agent.current_path, ["START"])

        # Check weights updated
        self.assertEqual(self.edge1.visits, 1)
        self.assertEqual(self.edge1.success_weight, 2.0)
        self.assertEqual(self.edge1.failure_weight, 1.0)

        self.assertEqual(self.edge2.visits, 1)
        self.assertEqual(self.edge2.success_weight, 2.0)
        self.assertEqual(self.edge2.failure_weight, 1.0)

        # Other edge shouldn't change
        self.assertEqual(self.edge3.visits, 0)
        self.assertEqual(self.edge3.success_weight, 1.0)

        # Let's test a failure case
        self.agent.current_path = ["START", "SCAN", "ATTACK_2"]
        self.agent.feedback(success=False)

        self.assertEqual(self.edge1.visits, 2)
        self.assertEqual(self.edge1.success_weight, 2.0)
        self.assertEqual(self.edge1.failure_weight, 2.0)

        self.assertEqual(self.edge3.visits, 1)
        self.assertEqual(self.edge3.success_weight, 1.0)
        self.assertEqual(self.edge3.failure_weight, 2.0)

    def test_policy_engine_preference(self):
        # Make ATTACK_1 much more successful than ATTACK_2
        self.edge2.success_weight = 100.0
        self.edge3.failure_weight = 100.0

        # Start from SCAN
        self.agent.current_node = "SCAN"

        # It should heavily prefer ATTACK_1 now
        choices = [self.agent.step() for _ in range(100)]
        self.agent.current_node = "SCAN"  # reset state for next steps
        attack_1_count = choices.count("ATTACK_1")
        attack_2_count = choices.count("ATTACK_2")

        self.assertGreater(attack_1_count, attack_2_count)


if __name__ == '__main__':
    unittest.main()
