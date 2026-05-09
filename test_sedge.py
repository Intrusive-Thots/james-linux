import unittest
import random
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGEModels(unittest.TestCase):
    def test_node_creation(self):
        node = Node(id="n1", state_type="scan")
        self.assertEqual(node.id, "n1")
        self.assertEqual(node.state_type, "scan")
        self.assertEqual(node.metadata, {})

    def test_edge_creation_and_score(self):
        edge = Edge(from_node="n1", to_node="n2")
        self.assertEqual(edge.from_node, "n1")
        self.assertEqual(edge.to_node, "n2")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 0)

        score = edge.score()
        self.assertAlmostEqual(score, 1.0 / (1.0 + 1e-6))

    def test_decision_graph(self):
        graph = DecisionGraph()
        node1 = Node(id="n1", state_type="scan")
        node2 = Node(id="n2", state_type="action")
        edge = Edge(from_node="n1", to_node="n2")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        self.assertIn("n1", graph.nodes)
        self.assertIn("n1", graph.edges)

        best_edge = graph.get_best_next("n1")
        self.assertIsNotNone(best_edge)
        if best_edge:
            self.assertEqual(best_edge.to_node, "n2")

        self.assertIsNone(graph.get_best_next("n2"))


class TestSEDGELearning(unittest.TestCase):
    def test_learning_engine_success(self):
        graph = DecisionGraph()
        edge1 = Edge(from_node="START", to_node="n1")
        edge2 = Edge(from_node="n1", to_node="n2")
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        learner = LearningEngine()
        learner.update(graph, ["START", "n1", "n2"], success=True)

        self.assertEqual(edge1.visits, 1)
        self.assertEqual(edge1.success_weight, 2.0)
        self.assertEqual(edge1.failure_weight, 1.0)

        self.assertEqual(edge2.visits, 1)
        self.assertEqual(edge2.success_weight, 2.0)
        self.assertEqual(edge2.failure_weight, 1.0)

    def test_learning_engine_failure(self):
        graph = DecisionGraph()
        edge1 = Edge(from_node="START", to_node="n1")
        graph.add_edge(edge1)

        learner = LearningEngine()
        learner.update(graph, ["START", "n1"], success=False)

        self.assertEqual(edge1.visits, 1)
        self.assertEqual(edge1.success_weight, 1.0)
        self.assertEqual(edge1.failure_weight, 2.0)


class TestSEDGEPolicy(unittest.TestCase):
    def test_decision_engine(self):
        random.seed(42)
        graph = DecisionGraph()
        e1 = Edge(from_node="START", to_node="n1", success_weight=10.0,
                  failure_weight=1.0)
        e2 = Edge(from_node="START", to_node="n2", success_weight=1.0,
                  failure_weight=10.0)
        graph.add_edge(e1)
        graph.add_edge(e2)

        engine = DecisionEngine(graph)

        decision = engine.decide("START")
        self.assertIn(decision, ["n1", "n2"])

        self.assertIsNone(engine.decide("n1"))


class TestSEDGEAgent(unittest.TestCase):
    def test_self_evolving_agent(self):
        graph = DecisionGraph()
        graph.add_edge(Edge(from_node="START", to_node="n1"))
        graph.add_edge(Edge(from_node="n1", to_node="END"))

        agent = SelfEvolvingAgent(graph)

        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        next_node = agent.step()
        self.assertEqual(next_node, "n1")
        self.assertEqual(agent.current_node, "n1")
        self.assertEqual(agent.current_path, ["START", "n1"])

        next_node = agent.step()
        self.assertEqual(next_node, "END")
        self.assertEqual(agent.current_node, "END")
        self.assertEqual(agent.current_path, ["START", "n1", "END"])

        next_node = agent.step()
        self.assertEqual(next_node, "halt")

        edge1 = graph.edges["START"][0]
        self.assertEqual(edge1.visits, 0)

        agent.feedback(success=True)

        self.assertEqual(edge1.visits, 1)
        self.assertEqual(edge1.success_weight, 2.0)

        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == "__main__":
    unittest.main()
