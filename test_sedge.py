import unittest
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = DecisionGraph()
        self.graph.add_node(Node("START", "state"))
        self.graph.add_node(Node("NETWORK_DISCOVERY", "action"))
        self.graph.add_node(Node("TARGET_ANALYSIS", "action"))
        self.graph.add_node(Node("SUCCESS", "outcome"))
        self.graph.add_node(Node("FAILURE", "outcome"))

        self.graph.add_edge(Edge("START", "NETWORK_DISCOVERY"))
        self.graph.add_edge(Edge("NETWORK_DISCOVERY", "TARGET_ANALYSIS"))
        self.graph.add_edge(Edge("TARGET_ANALYSIS", "SUCCESS"))
        self.graph.add_edge(Edge("TARGET_ANALYSIS", "FAILURE"))

        self.agent = SelfEvolvingAgent(self.graph)

    def test_graph_construction(self) -> None:
        self.assertEqual(len(self.graph.nodes), 5)
        self.assertEqual(len(self.graph.edges), 3)
        self.assertIn("START", self.graph.edges)
        self.assertEqual(len(self.graph.edges["TARGET_ANALYSIS"]), 2)

    def test_agent_step_progression(self) -> None:
        next_node = self.agent.step()
        self.assertEqual(next_node, "NETWORK_DISCOVERY")

        next_node = self.agent.step()
        self.assertEqual(next_node, "TARGET_ANALYSIS")

        next_node = self.agent.step()
        self.assertIn(next_node, ["SUCCESS", "FAILURE"])

    def test_learning_feedback(self) -> None:
        # Initial score
        edges = self.graph.edges["TARGET_ANALYSIS"]
        success_edge = next(e for e in edges if e.to_node == "SUCCESS")
        failure_edge = next(e for e in edges if e.to_node == "FAILURE")

        initial_success_score = success_edge.score()
        initial_failure_score = failure_edge.score()

        # Force path
        self.agent.current_path = [
            "START",
            "NETWORK_DISCOVERY",
            "TARGET_ANALYSIS",
            "SUCCESS",
        ]
        self.agent.feedback(success=True)

        self.assertEqual(success_edge.visits, 1)
        self.assertTrue(success_edge.score() > initial_success_score)

        # Failure score is unaffected in this path
        self.assertEqual(failure_edge.visits, 0)
        self.assertEqual(failure_edge.score(), initial_failure_score)


if __name__ == "__main__":
    unittest.main()
