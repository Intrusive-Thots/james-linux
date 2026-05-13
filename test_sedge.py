import unittest

from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGEModels(unittest.TestCase):
    def test_node_creation(self):
        node = Node(id="test_node", state_type="scan")
        self.assertEqual(node.id, "test_node")
        self.assertEqual(node.state_type, "scan")
        self.assertEqual(node.metadata, {})

    def test_edge_creation_and_score(self):
        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)

        # 1.0 / (1.0 + 1e-6) is roughly 0.999999
        self.assertAlmostEqual(edge.score(), 1.0, places=5)

    def test_decision_graph_add(self):
        graph = DecisionGraph()
        node_a = Node(id="A", state_type="scan")
        node_b = Node(id="B", state_type="scan")

        graph.add_node(node_a)
        graph.add_node(node_b)
        self.assertIn("A", graph.nodes)
        self.assertIn("B", graph.nodes)

        edge = Edge(from_node="A", to_node="B")
        graph.add_edge(edge)
        self.assertIn("A", graph.edges)
        self.assertEqual(len(graph.edges["A"]), 1)
        self.assertEqual(graph.edges["A"][0], edge)

    def test_decision_graph_best_next(self):
        graph = DecisionGraph()
        edge1 = Edge(
            from_node="A", to_node="B", success_weight=2.0, failure_weight=1.0
        )
        edge2 = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=2.0
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        best = graph.get_best_next("A")
        self.assertIsNotNone(best)
        self.assertEqual(best.to_node, "B")

        self.assertIsNone(graph.get_best_next("B"))


class TestSEDGELearning(unittest.TestCase):
    def test_learning_engine_success(self):
        graph = DecisionGraph()
        edge = Edge(from_node="A", to_node="B")
        graph.add_edge(edge)

        learner = LearningEngine()
        learner.update(graph, ["A", "B"], success=True)

        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

    def test_learning_engine_failure(self):
        graph = DecisionGraph()
        edge = Edge(from_node="A", to_node="B")
        graph.add_edge(edge)

        learner = LearningEngine()
        learner.update(graph, ["A", "B"], success=False)

        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 2.0)


class TestSEDGEPolicy(unittest.TestCase):
    def test_decision_engine_decide(self):
        graph = DecisionGraph()
        edge1 = Edge(
            from_node="A", to_node="B", success_weight=1.0, failure_weight=1.0
        )
        graph.add_edge(edge1)

        engine = DecisionEngine(graph)
        next_node = engine.decide("A")
        self.assertEqual(next_node, "B")

        self.assertIsNone(engine.decide("B"))


class TestSEDGEAgent(unittest.TestCase):
    def test_self_evolving_agent_flow(self):
        graph = DecisionGraph()
        graph.add_node(Node(id="START", state_type="start"))
        graph.add_node(Node(id="A", state_type="action"))
        graph.add_node(Node(id="B", state_type="action"))

        edge1 = Edge(
            from_node="START", to_node="A",
            success_weight=1.0, failure_weight=1.0
        )
        edge2 = Edge(
            from_node="A", to_node="B",
            success_weight=1.0, failure_weight=1.0
        )
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        agent = SelfEvolvingAgent(graph)

        # Step 1: START -> A
        next_node = agent.step()
        self.assertEqual(next_node, "A")
        self.assertEqual(agent.current_node, "A")
        self.assertEqual(agent.current_path, ["START", "A"])

        # Step 2: A -> B
        next_node = agent.step()
        self.assertEqual(next_node, "B")
        self.assertEqual(agent.current_node, "B")
        self.assertEqual(agent.current_path, ["START", "A", "B"])

        # Provide feedback (success)
        agent.feedback(success=True)

        # Weights should be updated
        self.assertEqual(edge1.visits, 1)
        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge2.visits, 1)
        self.assertEqual(edge2.success_weight, 2.0)

        # Agent should reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == "__main__":
    unittest.main()
