import unittest
import random
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
    build_parrot_wifi_graph,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeEngine(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="SCAN", state_type="action"))
        self.graph.add_node(Node(id="ATTACK", state_type="action"))

        self.graph.add_edge(Edge(from_node="START", to_node="SCAN"))
        self.graph.add_edge(Edge(from_node="SCAN", to_node="ATTACK"))

        self.learner = LearningEngine()
        self.decision_engine = DecisionEngine(self.graph)

    def test_learning_engine_success(self):
        path = ["START", "SCAN", "ATTACK"]
        self.learner.update(self.graph, path, OUTCOME_SUCCESS)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 2.0)
        self.assertEqual(start_scan_edge.failure_weight, 1.0)

    def test_learning_engine_failure(self):
        path = ["START", "SCAN", "ATTACK"]
        self.learner.update(self.graph, path, OUTCOME_FAILURE)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 1.0)
        self.assertEqual(start_scan_edge.failure_weight, 2.0)

    def test_learning_engine_partial(self):
        path = ["START", "SCAN"]
        self.learner.update(self.graph, path, OUTCOME_PARTIAL)

        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 1.5)
        self.assertEqual(start_scan_edge.failure_weight, 1.5)

    def test_decision_engine_decide(self):
        # With default weights (1.0 success, 1.0 failure), both score exactly 1.0.
        # But here START only has 1 edge.
        next_node = self.decision_engine.decide("START")
        self.assertEqual(next_node, "SCAN")

        # Add another edge to START
        self.graph.add_edge(Edge(from_node="START", to_node="ATTACK", success_weight=5.0))

        # With higher weight on ATTACK, stochastic selection favors it heavily.
        # Mock random to avoid flakiness, or just test fallback behavior.

        # Test zero total case
        self.graph.edges["START"][0].success_weight = 0.0
        self.graph.edges["START"][1].success_weight = 0.0

        # Now both have zero utility, fallback to random uniform selection.
        random.seed(42)
        next_node_zero = self.decision_engine.decide("START")
        self.assertIn(next_node_zero, ["SCAN", "ATTACK"])

    def test_decision_engine_no_candidates(self):
        next_node = self.decision_engine.decide("ATTACK")
        self.assertIsNone(next_node)

    def test_self_evolving_agent_step_and_feedback(self):
        agent = SelfEvolvingAgent(self.graph)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        # Take a step
        next_node = agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        # Take another step
        next_node2 = agent.step()
        self.assertEqual(next_node2, "ATTACK")
        self.assertEqual(agent.current_node, "ATTACK")
        self.assertEqual(agent.current_path, ["START", "SCAN", "ATTACK"])

        # No more edges from ATTACK
        next_node3 = agent.step()
        self.assertEqual(next_node3, "halt")

        # Apply feedback
        agent.feedback(OUTCOME_SUCCESS)

        # Check that learning engine updated weights
        start_scan_edge = self.graph.edges["START"][0]
        self.assertEqual(start_scan_edge.visits, 1)
        self.assertEqual(start_scan_edge.success_weight, 2.0)

        # Check that episode reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

    def test_build_parrot_wifi_graph(self):
        graph = build_parrot_wifi_graph()

        # Verify essential states and actions are nodes
        self.assertIn(STATE_START, graph.nodes)
        self.assertIn(STATE_NETWORK_DISCOVERY, graph.nodes)
        self.assertIn(STATE_TARGET_ANALYSIS, graph.nodes)
        self.assertIn(STATE_SECURITY_PROFILING, graph.nodes)

        self.assertIn(ACTION_PASSIVE_SCAN, graph.nodes)
        self.assertIn(ACTION_HANDSHAKE_CAPTURE, graph.nodes)
        self.assertIn(ACTION_DEAUTH_TEST, graph.nodes)
        self.assertIn(ACTION_EVIL_TWIN_SIMULATION, graph.nodes)

        # Verify edges from START
        start_edges = graph.edges.get(STATE_START, [])
        self.assertEqual(len(start_edges), 1)
        self.assertEqual(start_edges[0].to_node, STATE_NETWORK_DISCOVERY)

        # Verify edges from NETWORK_DISCOVERY
        discovery_edges = graph.edges.get(STATE_NETWORK_DISCOVERY, [])
        self.assertEqual(len(discovery_edges), 1)
        self.assertEqual(discovery_edges[0].to_node, ACTION_PASSIVE_SCAN)

        # Verify edges from PASSIVE_SCAN
        passive_scan_edges = graph.edges.get(ACTION_PASSIVE_SCAN, [])
        self.assertEqual(len(passive_scan_edges), 1)
        self.assertEqual(passive_scan_edges[0].to_node, STATE_TARGET_ANALYSIS)

        # Verify edges from TARGET_ANALYSIS
        target_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        self.assertEqual(len(target_edges), 2)
        to_nodes = [e.to_node for e in target_edges]
        self.assertIn(ACTION_HANDSHAKE_CAPTURE, to_nodes)
        self.assertIn(ACTION_DEAUTH_TEST, to_nodes)

        # Verify edges to SECURITY_PROFILING
        handshake_edges = graph.edges.get(ACTION_HANDSHAKE_CAPTURE, [])
        self.assertEqual(len(handshake_edges), 1)
        self.assertEqual(handshake_edges[0].to_node, STATE_SECURITY_PROFILING)

        deauth_edges = graph.edges.get(ACTION_DEAUTH_TEST, [])
        self.assertEqual(len(deauth_edges), 1)
        self.assertEqual(deauth_edges[0].to_node, STATE_SECURITY_PROFILING)

        # Verify edge from SECURITY_PROFILING
        sec_prof_edges = graph.edges.get(STATE_SECURITY_PROFILING, [])
        self.assertEqual(len(sec_prof_edges), 1)
        self.assertEqual(sec_prof_edges[0].to_node, ACTION_EVIL_TWIN_SIMULATION)


if __name__ == "__main__":
    unittest.main()
