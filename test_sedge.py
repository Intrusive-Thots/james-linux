import unittest
import random
from james.core.sedge.models import DecisionGraph, Node, NodeType, Edge
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSedgeModels(unittest.TestCase):
    def test_graph_creation(self):
        graph = DecisionGraph()
        node = Node(id="STATE_1", type=NodeType.STATE)
        graph.add_node(node)
        self.assertIn("STATE_1", graph.nodes)

        edge = Edge("STATE_1", "ACTION_1")
        graph.add_edge(edge)
        self.assertEqual(len(graph.get_edges("STATE_1")), 1)


class TestSedgeLearning(unittest.TestCase):
    def test_weight_update(self):
        engine = LearningEngine(learning_rate=0.5, discount_factor=1.0)
        edge = Edge("S1", "A1", weight=1.0)
        engine.update_weight(edge, reward=2.0)
        # 1.0 + 0.5 * (2.0 - 1.0) = 1.5
        self.assertEqual(edge.weight, 1.5)

    def test_apply_feedback(self):
        engine = LearningEngine(learning_rate=0.5, discount_factor=0.5)
        graph = DecisionGraph()
        e1 = Edge("S1", "A1", weight=1.0)
        e2 = Edge("S2", "A2", weight=1.0)

        engine.apply_feedback(graph, [e1, e2], final_reward=4.0)
        # e2 gets full reward 4.0 -> 1.0 + 0.5*(4.0-1.0) = 2.5
        self.assertEqual(e2.weight, 2.5)
        # e1 gets discounted reward 2.0 -> 1.0 + 0.5*(2.0-1.0) = 1.5
        self.assertEqual(e1.weight, 1.5)


class TestSedgePolicy(unittest.TestCase):
    def test_epsilon_greedy(self):
        random.seed(42)  # fixed seed for predictability
        policy = DecisionEngine(epsilon=0.0)  # pure exploitation
        graph = DecisionGraph()
        e1 = Edge("S1", "A1", weight=1.0)
        e2 = Edge("S1", "A2", weight=2.0)
        graph.add_edge(e1)
        graph.add_edge(e2)

        best_edge = policy.select_edge(graph, "S1")
        self.assertIsNotNone(best_edge)
        self.assertEqual(best_edge.target, "A2")


class TestSedgeAgent(unittest.TestCase):
    def test_agent_initialization(self):
        agent = SelfEvolvingAgent()
        self.assertIn("NETWORK_DISCOVERY", agent.graph.nodes)
        self.assertIn("PASSIVE_SCAN", agent.graph.nodes)

        edges = agent.graph.get_edges("NETWORK_DISCOVERY")
        self.assertTrue(any(e.target == "PASSIVE_SCAN" for e in edges))

    def test_agent_decision(self):
        agent = SelfEvolvingAgent(epsilon=0.0)  # pure exploitation
        # Add a clear better path
        agent.graph.add_edge(
            Edge("NETWORK_DISCOVERY", "SUPER_SCAN", weight=5.0)
        )
        next_action = agent.decide_next_action("NETWORK_DISCOVERY")
        self.assertEqual(next_action, "SUPER_SCAN")


if __name__ == "__main__":
    unittest.main()
