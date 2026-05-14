import unittest
from james.core.sedge import Node, Edge, DecisionGraph, LearningEngine, DecisionEngine, SelfEvolvingAgent

class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()

        # Nodes
        self.graph.add_node(Node("START", "state"))
        self.graph.add_node(Node("SCAN", "action"))
        self.graph.add_node(Node("ANALYZE", "analysis"))
        self.graph.add_node(Node("ATTACK", "action"))
        self.graph.add_node(Node("VALIDATE", "analysis"))

        # Edges
        self.graph.add_edge(Edge("START", "SCAN"))
        self.graph.add_edge(Edge("SCAN", "ANALYZE"))
        self.graph.add_edge(Edge("ANALYZE", "ATTACK"))
        self.graph.add_edge(Edge("ATTACK", "VALIDATE"))

    def test_node_and_edge_addition(self):
        self.assertIn("START", self.graph.nodes)
        self.assertEqual(len(self.graph.edges["START"]), 1)
        self.assertEqual(self.graph.edges["START"][0].to_node, "SCAN")

    def test_edge_scoring(self):
        edge = Edge("A", "B", success_weight=2.0, failure_weight=0.5)
        score = edge.score()
        self.assertAlmostEqual(score, 2.0 / (0.5 + 1e-6), places=4)

    def test_decision_graph_best_next(self):
        graph = DecisionGraph()
        graph.add_edge(Edge("A", "B", success_weight=1.0, failure_weight=1.0))
        graph.add_edge(Edge("A", "C", success_weight=5.0, failure_weight=1.0))

        best = graph.get_best_next("A")
        self.assertIsNotNone(best)
        self.assertEqual(best.to_node, "C")

    def test_learning_engine_success(self):
        learner = LearningEngine()
        path = ["START", "SCAN", "ANALYZE"]

        learner.update(self.graph, path, success=True)

        edge_start_scan = self.graph.edges["START"][0]
        self.assertEqual(edge_start_scan.visits, 1)
        self.assertEqual(edge_start_scan.success_weight, 2.0)
        self.assertEqual(edge_start_scan.failure_weight, 1.0)

        edge_scan_analyze = self.graph.edges["SCAN"][0]
        self.assertEqual(edge_scan_analyze.visits, 1)
        self.assertEqual(edge_scan_analyze.success_weight, 2.0)
        self.assertEqual(edge_scan_analyze.failure_weight, 1.0)

        # Untraversed edges should be untouched
        edge_analyze_attack = self.graph.edges["ANALYZE"][0]
        self.assertEqual(edge_analyze_attack.visits, 0)
        self.assertEqual(edge_analyze_attack.success_weight, 1.0)

    def test_learning_engine_failure(self):
        learner = LearningEngine()
        path = ["START", "SCAN", "ANALYZE"]

        learner.update(self.graph, path, success=False)

        edge_start_scan = self.graph.edges["START"][0]
        self.assertEqual(edge_start_scan.visits, 1)
        self.assertEqual(edge_start_scan.success_weight, 1.0)
        self.assertEqual(edge_start_scan.failure_weight, 2.0)

    def test_decision_engine_stochastic(self):
        graph = DecisionGraph()
        graph.add_edge(Edge("A", "B", success_weight=9.0, failure_weight=1.0)) # Score ~ 9
        graph.add_edge(Edge("A", "C", success_weight=1.0, failure_weight=1.0)) # Score ~ 1

        engine = DecisionEngine(graph)

        results = {"B": 0, "C": 0}
        for _ in range(1000):
            res = engine.decide("A")
            results[res] += 1

        # Due to stochastic nature, B should be chosen roughly 90% of the time, C roughly 10%
        self.assertGreater(results["B"], 800)
        self.assertLess(results["C"], 200)

    def test_decision_engine_halt(self):
        engine = DecisionEngine(self.graph)
        self.assertIsNone(engine.decide("VALIDATE"))

    def test_self_evolving_agent_loop(self):
        agent = SelfEvolvingAgent(self.graph)

        step1 = agent.step()
        self.assertEqual(step1, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        step2 = agent.step()
        self.assertEqual(step2, "ANALYZE")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ANALYZE"])

        agent.feedback(success=True)

        # State should reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Verify learning was applied
        self.assertEqual(self.graph.edges["START"][0].success_weight, 2.0)

if __name__ == '__main__':
    unittest.main()
