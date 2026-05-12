import unittest
import random
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
)


class TestSedgeDecisionGraph(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.n1 = Node(id="START", state_type="start")
        self.n2 = Node(id="SCAN", state_type="action")
        self.n3 = Node(id="ATTACK", state_type="action")

        self.e1 = Edge(
            from_node="START",
            to_node="SCAN",
            success_weight=2.0,
            failure_weight=1.0,
        )
        self.e2 = Edge(
            from_node="START",
            to_node="ATTACK",
            success_weight=1.0,
            failure_weight=2.0,
        )

        self.graph.add_node(self.n1)
        self.graph.add_node(self.n2)
        self.graph.add_node(self.n3)

    def test_add_node_and_edge(self):
        self.graph.add_edge(self.e1)
        self.assertIn("START", self.graph.nodes)
        self.assertEqual(len(self.graph.edges["START"]), 1)

    def test_get_best_next(self):
        self.graph.add_edge(self.e1)
        self.graph.add_edge(self.e2)

        best_edge = self.graph.get_best_next("START")
        self.assertEqual(best_edge.to_node, "SCAN")


class TestSedgeLearningEngine(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.e1 = Edge(
            from_node="START",
            to_node="SCAN",
            success_weight=1.0,
            failure_weight=1.0,
        )
        self.e2 = Edge(
            from_node="SCAN",
            to_node="ANALYZE",
            success_weight=1.0,
            failure_weight=1.0,
        )
        self.graph.add_edge(self.e1)
        self.graph.add_edge(self.e2)
        self.learner = LearningEngine()

    def test_update_success(self):
        path = ["START", "SCAN", "ANALYZE"]
        self.learner.update(self.graph, path, success=True)

        self.assertEqual(self.e1.success_weight, 2.0)
        self.assertEqual(self.e1.failure_weight, 1.0)
        self.assertEqual(self.e1.visits, 1)

        self.assertEqual(self.e2.success_weight, 2.0)
        self.assertEqual(self.e2.failure_weight, 1.0)
        self.assertEqual(self.e2.visits, 1)

    def test_update_failure(self):
        path = ["START", "SCAN"]
        self.learner.update(self.graph, path, success=False)

        self.assertEqual(self.e1.success_weight, 1.0)
        self.assertEqual(self.e1.failure_weight, 2.0)
        self.assertEqual(self.e1.visits, 1)


class TestSedgeDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.e1 = Edge(
            from_node="START",
            to_node="A",
            success_weight=90.0,
            failure_weight=1.0,
        )
        self.e2 = Edge(
            from_node="START",
            to_node="B",
            success_weight=10.0,
            failure_weight=1.0,
        )
        self.graph.add_edge(self.e1)
        self.graph.add_edge(self.e2)
        self.engine = DecisionEngine(self.graph)

    def test_decide_stochastic(self):
        random.seed(42)

        results = {"A": 0, "B": 0}
        for _ in range(100):
            res = self.engine.decide("START")
            results[res] += 1

        self.assertGreater(results["A"], results["B"])


class TestSedgeSelfEvolvingAgent(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.e1 = Edge(
            from_node="START",
            to_node="SCAN",
            success_weight=1.0,
            failure_weight=1.0,
        )
        self.graph.add_edge(self.e1)
        self.agent = SelfEvolvingAgent(self.graph)

    def test_agent_step_and_feedback(self):
        self.assertEqual(self.agent.current_node, "START")

        next_node = self.agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(self.agent.current_node, "SCAN")
        self.assertEqual(self.agent.current_path, ["START", "SCAN"])

        halt_node = self.agent.step()
        self.assertEqual(halt_node, "halt")

        self.agent.feedback(success=True)
        self.assertEqual(self.agent.current_node, "START")
        self.assertEqual(self.agent.current_path, ["START"])

        self.assertEqual(self.e1.success_weight, 2.0)
        self.assertEqual(self.e1.visits, 1)


if __name__ == "__main__":
    unittest.main()
