import unittest
import random
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def test_decision_graph_add(self):
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

        # Test get_best_next
        e2 = Edge("START", "IDLE", success_weight=0.1)
        graph.add_edge(e2)

        best = graph.get_best_next("START")
        # SCAN score 1.0 vs IDLE score 0.1
        self.assertEqual(best.to_node, "SCAN")

        self.assertIsNone(graph.get_best_next("IDLE"))

    def test_learning_engine_update(self):
        graph = DecisionGraph()
        graph.add_edge(Edge("A", "B"))
        graph.add_edge(Edge("B", "C"))

        learner = LearningEngine()

        # Test success
        path = ["A", "B", "C"]
        learner.update(graph, path, True)

        self.assertEqual(graph.edges["A"][0].visits, 1)
        self.assertEqual(graph.edges["A"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["A"][0].failure_weight, 1.0)

        self.assertEqual(graph.edges["B"][0].visits, 1)
        self.assertEqual(graph.edges["B"][0].success_weight, 2.0)

        # Test failure
        learner.update(graph, path, False)

        self.assertEqual(graph.edges["A"][0].visits, 2)
        self.assertEqual(graph.edges["A"][0].success_weight, 2.0)
        self.assertEqual(graph.edges["A"][0].failure_weight, 2.0)

    def test_decision_engine_stochastic(self):
        graph = DecisionGraph()
        # Create edges where B is heavily weighted over C
        e1 = Edge("A", "B", success_weight=100.0, failure_weight=1.0)
        e2 = Edge("A", "C", success_weight=1.0, failure_weight=100.0)
        graph.add_edge(e1)
        graph.add_edge(e2)

        engine = DecisionEngine(graph)

        # We can't perfectly assert randomness, but we can verify it doesn't
        # crash and returns valid targets
        random.seed(42)  # Deterministic for test stability if possible

        results = [engine.decide("A") for _ in range(100)]
        self.assertTrue(all(r in ["B", "C"] for r in results))

        # Statistically, B should be chosen more often than C
        b_count = results.count("B")
        c_count = results.count("C")
        self.assertGreater(b_count, c_count)

        self.assertIsNone(engine.decide("D"))

    def test_self_evolving_agent_loop(self):
        graph = DecisionGraph()
        # Path: START -> SCAN -> TARGET -> HALT
        graph.add_edge(Edge("START", "SCAN"))
        graph.add_edge(Edge("SCAN", "TARGET"))

        agent = SelfEvolvingAgent(graph)

        self.assertEqual(agent.current_node, "START")

        # Force decision engine choices by only having one edge
        next1 = agent.step()
        self.assertEqual(next1, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        next2 = agent.step()
        self.assertEqual(next2, "TARGET")

        next3 = agent.step()
        self.assertEqual(next3, "halt")

        # Provide feedback
        agent.feedback(True)

        # Verify learning
        self.assertEqual(graph.edges["START"][0].visits, 1)
        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)

        self.assertEqual(graph.edges["SCAN"][0].visits, 1)
        self.assertEqual(graph.edges["SCAN"][0].success_weight, 2.0)

        # Verify reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == "__main__":
    unittest.main()
