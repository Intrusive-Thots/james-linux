import unittest
from james.core.sedge import Node, Edge, DecisionGraph, SelfEvolvingAgent, build_parrot_wifi_graph
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


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = build_parrot_wifi_graph()
        self.agent = SelfEvolvingAgent(self.graph)

    def test_build_parrot_wifi_graph(self):
        self.assertIn(STATE_START, self.graph.nodes)
        self.assertIn(STATE_NETWORK_DISCOVERY, self.graph.nodes)
        self.assertIn(ACTION_PASSIVE_SCAN, self.graph.nodes)

        edges = self.graph.edges.get(STATE_SECURITY_PROFILING, [])
        to_nodes = [e.to_node for e in edges]
        self.assertIn(ACTION_PASSIVE_SCAN, to_nodes)
        self.assertIn(ACTION_HANDSHAKE_CAPTURE, to_nodes)

    def test_initial_state(self):
        self.assertEqual(self.agent.current_node, STATE_START)
        self.assertEqual(self.agent.current_path, [STATE_START])

    def test_step_execution(self):
        next_node = self.agent.step()
        self.assertEqual(next_node, STATE_NETWORK_DISCOVERY)
        self.assertEqual(self.agent.current_node, STATE_NETWORK_DISCOVERY)
        self.assertEqual(
            self.agent.current_path, [STATE_START, STATE_NETWORK_DISCOVERY]
        )

        next_node = self.agent.step()
        self.assertEqual(next_node, STATE_TARGET_ANALYSIS)

        next_node = self.agent.step()
        self.assertEqual(next_node, STATE_SECURITY_PROFILING)

        next_node = self.agent.step()
        self.assertIn(
            next_node,
            [
                ACTION_PASSIVE_SCAN,
                ACTION_HANDSHAKE_CAPTURE,
                ACTION_DEAUTH_TEST,
                ACTION_EVIL_TWIN_SIMULATION,
            ],
        )

        # Next step should halt because there are no outgoing edges
        next_node = self.agent.step()
        self.assertEqual(next_node, "halt")

    def test_feedback_learning_and_reset(self):
        self.agent.step()  # START -> NETWORK_DISCOVERY
        self.agent.step()  # NETWORK_DISCOVERY -> TARGET_ANALYSIS
        self.agent.step()  # TARGET_ANALYSIS -> SECURITY_PROFILING
        last_node = (
            self.agent.step()
        )  # -> PASSIVE_SCAN or HANDSHAKE_CAPTURE ...

        self.agent.feedback(outcome=OUTCOME_SUCCESS)

        self.assertEqual(self.agent.current_node, STATE_START)
        self.assertEqual(self.agent.current_path, [STATE_START])

        # Check that edges got visits and updated weights
        edges = self.graph.edges[STATE_START]
        self.assertEqual(edges[0].visits, 1)
        self.assertEqual(edges[0].success_weight, 2.0)
        self.assertEqual(edges[0].failure_weight, 1.0)

        edges = self.graph.edges[STATE_SECURITY_PROFILING]
        for edge in edges:
            if edge.to_node == last_node:
                self.assertEqual(edge.visits, 1)
                self.assertEqual(edge.success_weight, 2.0)
                self.assertEqual(edge.failure_weight, 1.0)
            else:
                self.assertEqual(edge.visits, 0)
                self.assertEqual(edge.success_weight, 1.0)
                self.assertEqual(edge.failure_weight, 1.0)

    def test_learning_failure(self):
        self.agent.step()  # START -> NETWORK_DISCOVERY
        self.agent.step()  # NETWORK_DISCOVERY -> TARGET_ANALYSIS
        self.agent.step()  # TARGET_ANALYSIS -> SECURITY_PROFILING
        self.agent.step()  # -> PASSIVE_SCAN or HANDSHAKE_CAPTURE ...

        self.agent.feedback(outcome=OUTCOME_FAILURE)

        edges = self.graph.edges[STATE_START]
        self.assertEqual(edges[0].visits, 1)
        self.assertEqual(edges[0].success_weight, 1.0)
        self.assertEqual(edges[0].failure_weight, 2.0)

    def test_learning_partial_signal(self):
        self.agent.step()  # START -> NETWORK_DISCOVERY
        self.agent.step()  # NETWORK_DISCOVERY -> TARGET_ANALYSIS
        self.agent.step()  # TARGET_ANALYSIS -> SECURITY_PROFILING
        self.agent.step()  # -> PASSIVE_SCAN or HANDSHAKE_CAPTURE ...

        self.agent.feedback(outcome=OUTCOME_PARTIAL)

        edges = self.graph.edges[STATE_START]
        self.assertEqual(edges[0].visits, 1)
        self.assertEqual(edges[0].success_weight, 1.5)
        self.assertEqual(edges[0].failure_weight, 1.5)

    def test_get_best_next_no_edges(self):
        self.assertIsNone(self.graph.get_best_next("PASSIVE_SCAN"))

    def test_get_best_next_with_edges(self):
        # We know START has one edge
        best_edge = self.graph.get_best_next(STATE_START)
        self.assertIsNotNone(best_edge)
        self.assertEqual(best_edge.to_node, STATE_NETWORK_DISCOVERY)

    def test_get_best_next_no_edges_duplicate(self):
        self.assertIsNone(self.graph.get_best_next(ACTION_PASSIVE_SCAN))

    def test_get_best_next_with_edges(self):
        # We know START has one edge
        best_edge = self.graph.get_best_next(STATE_START)
        self.assertIsNotNone(best_edge)
        self.assertEqual(best_edge.to_node, STATE_NETWORK_DISCOVERY)

    def test_decide_zero_weights(self):
        # Reset graph edges to have zero success_weight (total score = 0)
        self.graph.edges[STATE_SECURITY_PROFILING] = [
            Edge(
                from_node=STATE_SECURITY_PROFILING,
                to_node=ACTION_PASSIVE_SCAN,
                success_weight=0.0,
            ),
            Edge(
                from_node=STATE_SECURITY_PROFILING,
                to_node=ACTION_HANDSHAKE_CAPTURE,
                success_weight=0.0,
            ),
        ]

        # Test that decision engine can handle this gracefully
        next_node = self.agent.decision_engine.decide(STATE_SECURITY_PROFILING)
        self.assertIn(next_node, [ACTION_PASSIVE_SCAN, ACTION_HANDSHAKE_CAPTURE])


if __name__ == "__main__":
    unittest.main()
