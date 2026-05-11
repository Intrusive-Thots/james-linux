import unittest
from james.core.sedge.models import DecisionGraph, Node, Edge
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSedge(unittest.TestCase):
    def test_graph_creation(self) -> None:
        graph = DecisionGraph()
        n1 = Node(id="START", state_type="state")
        n2 = Node(id="SCAN", state_type="action")

        graph.add_node(n1)
        graph.add_node(n2)

        e1 = Edge(from_node="START", to_node="SCAN")
        graph.add_edge(e1)

        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges["START"][0].to_node, "SCAN")

    def test_learning_updates(self) -> None:
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="START", to_node="SCAN"))
        graph.add_edge(Edge(from_node="SCAN", to_node="ANALYZE"))

        learner = LearningEngine()

        # Test success
        learner.update(graph, ["START", "SCAN", "ANALYZE"], success=True)
        self.assertEqual(graph.edges["START"][0].visits, 1)
        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["START"][0].failure_weight, 1.0)

        self.assertEqual(graph.edges["SCAN"][0].visits, 1)
        self.assertEqual(graph.edges["SCAN"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["SCAN"][0].failure_weight, 1.0)

        # Test failure
        learner.update(graph, ["START", "SCAN", "ANALYZE"], success=False)
        self.assertEqual(graph.edges["START"][0].visits, 2)
        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["START"][0].failure_weight, 2.0)

        self.assertEqual(graph.edges["SCAN"][0].visits, 2)
        self.assertEqual(graph.edges["SCAN"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["SCAN"][0].failure_weight, 2.0)

    def test_decision_policy(self) -> None:
        graph = DecisionGraph()
        e1 = Edge(
            from_node="START",
            to_node="GOOD_PATH",
            success_weight=100.0,
            failure_weight=1.0,
        )
        e2 = Edge(
            from_node="START",
            to_node="BAD_PATH",
            success_weight=1.0,
            failure_weight=100.0,
        )
        graph.add_edge(e1)
        graph.add_edge(e2)

        engine = DecisionEngine(graph)

        # Should highly prefer GOOD_PATH due to weights
        choices = [engine.decide("START") for _ in range(100)]
        good_count = choices.count("GOOD_PATH")
        bad_count = choices.count("BAD_PATH")

        self.assertGreater(good_count, bad_count)
        self.assertTrue(good_count > 90)

    def test_agent_workflow(self) -> None:
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="START", to_node="SCAN"))
        graph.add_edge(Edge(from_node="SCAN", to_node="ANALYZE"))

        agent = SelfEvolvingAgent(graph)

        # Step through graph
        next1 = agent.step()
        self.assertEqual(next1, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        next2 = agent.step()
        self.assertEqual(next2, "ANALYZE")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ANALYZE"])

        # Feedback resets and updates weights
        agent.feedback(success=True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["SCAN"][0].success_weight, 2.0)


if __name__ == "__main__":
    unittest.main()
