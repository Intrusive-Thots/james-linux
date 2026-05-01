import unittest

from james.core.sedge.models import Node, Edge
from james.core.sedge.graph import DecisionGraph
from james.core.sedge.engine import LearningEngine, DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent

class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.node_start = Node(id="START", state_type="scan")
        self.node_scan = Node(id="scan", state_type="scan")
        self.node_analysis = Node(id="analysis", state_type="analysis")

        self.graph.add_node(self.node_start)
        self.graph.add_node(self.node_scan)
        self.graph.add_node(self.node_analysis)

        self.edge_start_scan = Edge(from_node="START", to_node="scan")
        self.edge_scan_analysis = Edge(from_node="scan", to_node="analysis")

        self.graph.add_edge(self.edge_start_scan)
        self.graph.add_edge(self.edge_scan_analysis)

    def test_graph_add_get(self):
        best_edge = self.graph.get_best_next("START")
        self.assertEqual(best_edge.to_node, "scan")

        self.assertIsNone(self.graph.get_best_next("analysis"))

    def test_learning_engine_success(self):
        learner = LearningEngine()
        learner.update(self.graph, ["START", "scan", "analysis"], success=True)

        self.assertEqual(self.edge_start_scan.visits, 1)
        self.assertEqual(self.edge_start_scan.success_weight, 2.0)
        self.assertEqual(self.edge_start_scan.failure_weight, 1.0)

        self.assertEqual(self.edge_scan_analysis.visits, 1)
        self.assertEqual(self.edge_scan_analysis.success_weight, 2.0)
        self.assertEqual(self.edge_scan_analysis.failure_weight, 1.0)

    def test_learning_engine_failure(self):
        learner = LearningEngine()
        learner.update(self.graph, ["START", "scan"], success=False)

        self.assertEqual(self.edge_start_scan.visits, 1)
        self.assertEqual(self.edge_start_scan.success_weight, 1.0)
        self.assertEqual(self.edge_start_scan.failure_weight, 2.0)

    def test_decision_engine(self):
        engine = DecisionEngine(self.graph)
        next_node = engine.decide("START")
        self.assertEqual(next_node, "scan")

        next_node = engine.decide("analysis")
        self.assertIsNone(next_node)

    def test_agent_loop(self):
        agent = SelfEvolvingAgent(self.graph)

        # Step 1
        node1 = agent.step()
        self.assertEqual(node1, "scan")
        self.assertEqual(agent.current_path, ["START", "scan"])

        # Step 2
        node2 = agent.step()
        self.assertEqual(node2, "analysis")
        self.assertEqual(agent.current_path, ["START", "scan", "analysis"])

        # Step 3 (halt)
        node3 = agent.step()
        self.assertEqual(node3, "halt")

        # Feedback
        agent.feedback(success=True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Verify learning happened
        self.assertEqual(self.edge_start_scan.visits, 1)
        self.assertEqual(self.edge_start_scan.success_weight, 2.0)

if __name__ == "__main__":
    unittest.main()
