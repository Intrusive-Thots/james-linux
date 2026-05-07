import unittest
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGEArchitecture(unittest.TestCase):
    def test_decision_graph_addition(self) -> None:
        graph = DecisionGraph()
        n1 = Node("START", "state")
        n2 = Node("SCAN", "action")
        graph.add_node(n1)
        graph.add_node(n2)

        self.assertIn("START", graph.nodes)
        self.assertIn("SCAN", graph.nodes)

        e1 = Edge("START", "SCAN")
        graph.add_edge(e1)

        self.assertIn("START", graph.edges)
        self.assertEqual(len(graph.edges["START"]), 1)
        self.assertEqual(graph.edges["START"][0].to_node, "SCAN")

    def test_learning_engine_update_success(self) -> None:
        graph = DecisionGraph()
        graph.add_edge(Edge("START", "SCAN"))

        learner = LearningEngine()
        learner.update(graph, ["START", "SCAN"], success=True)

        edge = graph.edges["START"][0]
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

    def test_learning_engine_update_failure(self) -> None:
        graph = DecisionGraph()
        graph.add_edge(Edge("START", "SCAN"))

        learner = LearningEngine()
        learner.update(graph, ["START", "SCAN"], success=False)

        edge = graph.edges["START"][0]
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 2.0)

    def test_decision_engine_stochastic_selection(self) -> None:
        graph = DecisionGraph()
        e1 = Edge("START", "SCAN")
        e2 = Edge("START", "ANALYZE")
        e1.success_weight = 100.0
        e2.success_weight = 0.01

        graph.add_edge(e1)
        graph.add_edge(e2)

        engine = DecisionEngine(graph)
        selected_nodes = [engine.decide("START") for _ in range(100)]

        # High probability that SCAN is selected most of the time
        scan_count = selected_nodes.count("SCAN")
        self.assertGreater(scan_count, 90)

    def test_self_evolving_agent_step_and_feedback(self) -> None:
        graph = DecisionGraph()
        graph.add_edge(Edge("START", "SCAN"))
        graph.add_edge(Edge("SCAN", "ATTACK"))

        agent = SelfEvolvingAgent(graph)
        self.assertEqual(agent.current_node, "START")

        next_node = agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        next_node_2 = agent.step()
        self.assertEqual(next_node_2, "ATTACK")
        self.assertEqual(agent.current_node, "ATTACK")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ATTACK"])

        agent.feedback(success=True)

        # Verify learning update and episode reset
        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["SCAN"][0].success_weight, 2.0)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == "__main__":
    unittest.main()
