import unittest
from james.core.sedge import Node, Edge, DecisionGraph, SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()

        # Add nodes
        self.graph.add_node(Node("START", "start"))
        self.graph.add_node(Node("A", "action"))
        self.graph.add_node(Node("B", "action"))
        self.graph.add_node(Node("END", "end"))

        # Add edges
        self.graph.add_edge(Edge("START", "A"))
        self.graph.add_edge(Edge("START", "B"))
        self.graph.add_edge(Edge("A", "END"))
        self.graph.add_edge(Edge("B", "END"))

    def test_edge_score(self):
        edge = Edge("X", "Y", success_weight=2.0, failure_weight=1.0)
        self.assertAlmostEqual(edge.score(), 2.0 / (1.0 + 1e-6), places=4)

    def test_decision_graph_get_best_next(self):
        # By default weights are 1.0, so both A and B have same score
        # Let's artificially boost B
        for edge in self.graph.edges["START"]:
            if edge.to_node == "B":
                edge.success_weight = 5.0

        best_edge = self.graph.get_best_next("START")
        self.assertIsNotNone(best_edge)
        self.assertEqual(best_edge.to_node, "B")

    def test_agent_step_and_feedback(self):
        agent = SelfEvolvingAgent(self.graph)

        # Step through
        next_node = agent.step()
        self.assertIn(next_node, ["A", "B"])

        next_node2 = agent.step()
        self.assertEqual(next_node2, "END")

        # Provide feedback
        agent.feedback(success=True)

        # Check if weights were updated
        # Path should be START -> next_node -> END
        for edge in self.graph.edges["START"]:
            if edge.to_node == next_node:
                self.assertEqual(edge.visits, 1)
                self.assertEqual(edge.success_weight, 2.0)
            else:
                self.assertEqual(edge.visits, 0)
                self.assertEqual(edge.success_weight, 1.0)

        for edge in self.graph.edges[next_node]:
            if edge.to_node == "END":
                self.assertEqual(edge.visits, 1)
                self.assertEqual(edge.success_weight, 2.0)

    def test_agent_halt(self):
        agent = SelfEvolvingAgent(self.graph)
        # Manually navigate to end
        agent.current_node = "END"
        # END has no outgoing edges
        self.assertEqual(agent.step(), "halt")


if __name__ == "__main__":
    unittest.main()
