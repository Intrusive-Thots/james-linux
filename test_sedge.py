import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
)


class TestSEDGE(unittest.TestCase):
    def test_node_edge_creation(self):
        graph = DecisionGraph()
        n1 = Node(id="START", state_type="start")
        n2 = Node(id="SCAN", state_type="scan")
        graph.add_node(n1)
        graph.add_node(n2)

        e1 = Edge(from_node="START", to_node="SCAN")
        graph.add_edge(e1)

        self.assertIn("START", graph.nodes)
        self.assertIn("SCAN", graph.nodes)
        self.assertEqual(len(graph.edges["START"]), 1)
        self.assertEqual(graph.edges["START"][0].to_node, "SCAN")

    def test_best_next_selection(self):
        graph = DecisionGraph()
        e1 = Edge(
            from_node="START",
            to_node="SCAN",
            success_weight=1.0,
            failure_weight=1.0,
        )
        e2 = Edge(
            from_node="START",
            to_node="ATTACK",
            success_weight=2.0,
            failure_weight=1.0,
        )
        graph.add_edge(e1)
        graph.add_edge(e2)

        best = graph.get_best_next("START")
        self.assertEqual(best, "ATTACK")

        self.assertIsNone(graph.get_best_next("EMPTY"))

    def test_learning_engine_updates(self):
        graph = DecisionGraph()
        e1 = Edge(from_node="A", to_node="B")
        e2 = Edge(from_node="B", to_node="C")
        graph.add_edge(e1)
        graph.add_edge(e2)

        learner = LearningEngine()

        # Test success update
        learner.update(graph, ["A", "B", "C"], success=True)
        self.assertEqual(e1.success_weight, 2.0)
        self.assertEqual(e1.visits, 1)
        self.assertEqual(e2.success_weight, 2.0)
        self.assertEqual(e2.visits, 1)

        # Test failure update
        learner.update(graph, ["A", "B", "C"], success=False)
        self.assertEqual(e1.failure_weight, 2.0)
        self.assertEqual(e1.visits, 2)
        self.assertEqual(e2.failure_weight, 2.0)
        self.assertEqual(e2.visits, 2)

    def test_stochastic_decision_engine(self):
        graph = DecisionGraph()
        e1 = Edge(
            from_node="START",
            to_node="A",
            success_weight=100.0,
            failure_weight=1.0,
        )
        e2 = Edge(
            from_node="START",
            to_node="B",
            success_weight=1.0,
            failure_weight=100.0,
        )
        graph.add_edge(e1)
        graph.add_edge(e2)

        engine = DecisionEngine(graph)

        # Due to stochasticity, we run it multiple times, A should be overwhelmingly selected
        choices = [engine.decide("START") for _ in range(100)]
        self.assertGreater(choices.count("A"), choices.count("B"))

    def test_self_evolving_agent_flow(self):
        graph = DecisionGraph()
        e1 = Edge(from_node="START", to_node="SCAN")
        e2 = Edge(from_node="SCAN", to_node="ATTACK")
        graph.add_edge(e1)
        graph.add_edge(e2)

        agent = SelfEvolvingAgent(graph)

        next1 = agent.step()
        self.assertEqual(next1, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        next2 = agent.step()
        self.assertEqual(next2, "ATTACK")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ATTACK"])

        next3 = agent.step()
        self.assertEqual(next3, "halt")

        agent.feedback(success=True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])
        self.assertEqual(e1.success_weight, 2.0)
        self.assertEqual(e2.success_weight, 2.0)


if __name__ == "__main__":
    unittest.main()
