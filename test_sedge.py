import unittest
from james.core.sedge import Node, Edge, DecisionGraph, SelfEvolvingAgent
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
        self.graph = DecisionGraph()

        # Add Nodes
        self.graph.add_node(Node(id=STATE_START, state_type="start"))
        self.graph.add_node(
            Node(id=STATE_NETWORK_DISCOVERY, state_type="scan")
        )
        self.graph.add_node(
            Node(id=STATE_TARGET_ANALYSIS, state_type="analysis")
        )
        self.graph.add_node(
            Node(id=STATE_SECURITY_PROFILING, state_type="analysis")
        )
        self.graph.add_node(Node(id=ACTION_PASSIVE_SCAN, state_type="action"))
        self.graph.add_node(
            Node(id=ACTION_HANDSHAKE_CAPTURE, state_type="action")
        )
        self.graph.add_node(Node(id=ACTION_DEAUTH_TEST, state_type="action"))
        self.graph.add_node(
            Node(id=ACTION_EVIL_TWIN_SIMULATION, state_type="action")
        )

        # Add Edges
        self.graph.add_edge(
            Edge(from_node=STATE_START, to_node=STATE_NETWORK_DISCOVERY)
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_NETWORK_DISCOVERY,
                to_node=STATE_TARGET_ANALYSIS,
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_TARGET_ANALYSIS,
                to_node=STATE_SECURITY_PROFILING,
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_SECURITY_PROFILING, to_node=ACTION_PASSIVE_SCAN
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_SECURITY_PROFILING,
                to_node=ACTION_HANDSHAKE_CAPTURE,
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_SECURITY_PROFILING, to_node=ACTION_DEAUTH_TEST
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_SECURITY_PROFILING,
                to_node=ACTION_EVIL_TWIN_SIMULATION,
            )
        )

        self.agent = SelfEvolvingAgent(self.graph)

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
        self.assertIn(
            next_node, [ACTION_PASSIVE_SCAN, ACTION_HANDSHAKE_CAPTURE]
        )

    def test_stochastic_weighted_selection(self):
        # We'll set up two paths from START, one heavily favored
        self.graph.add_edge(
            Edge(
                from_node=STATE_START,
                to_node=ACTION_PASSIVE_SCAN,
                success_weight=9.0,
                failure_weight=1.0,
            )
        )
        self.graph.add_edge(
            Edge(
                from_node=STATE_START,
                to_node=ACTION_HANDSHAKE_CAPTURE,
                success_weight=1.0,
                failure_weight=1.0,
            )
        )

        counts = {
            ACTION_PASSIVE_SCAN: 0,
            ACTION_HANDSHAKE_CAPTURE: 0,
            STATE_NETWORK_DISCOVERY: 0,
        }
        iterations = 10000
        for _ in range(iterations):
            next_node = self.agent.decision_engine.decide(STATE_START)
            if next_node in counts:
                counts[next_node] += 1

        # With original graph START->NETWORK_DISCOVERY has score 1.0 (1/1)
        # PASSIVE_SCAN has score 9.0 (9/1)
        # HANDSHAKE_CAPTURE has score 1.0 (1/1)
        # Total score = 1 + 9 + 1 = 11.
        # PASSIVE_SCAN should be chosen roughly 9/11 times (~81.8%)
        # NETWORK_DISCOVERY roughly 1/11 times (~9.1%)
        # HANDSHAKE_CAPTURE roughly 1/11 times (~9.1%)

        passive_prob = counts[ACTION_PASSIVE_SCAN] / iterations
        handshake_prob = counts[ACTION_HANDSHAKE_CAPTURE] / iterations
        network_prob = counts[STATE_NETWORK_DISCOVERY] / iterations

        self.assertTrue(
            0.78 < passive_prob < 0.85, f"Expected ~0.818, got {passive_prob}"
        )
        self.assertTrue(
            0.07 < handshake_prob < 0.12,
            f"Expected ~0.091, got {handshake_prob}",
        )
        self.assertTrue(
            0.07 < network_prob < 0.12, f"Expected ~0.091, got {network_prob}"
        )

    def test_graph_convergence(self):
        # Simulate multiple agent runs and verify that optimal paths gain higher probability
        iterations = 100
        for _ in range(iterations):
            # Agent steps through the graph
            while True:
                next_node = self.agent.step()
                if next_node == "halt":
                    break

            # Simulate a scenario where EVIL_TWIN_SIMULATION always fails
            # and PASSIVE_SCAN path succeeds if it gets there (but in our setup, it's just reaching the end)
            last_node = self.agent.current_path[-1]
            if last_node == ACTION_EVIL_TWIN_SIMULATION:
                self.agent.feedback(outcome=OUTCOME_FAILURE)
            elif last_node == ACTION_PASSIVE_SCAN:
                self.agent.feedback(outcome=OUTCOME_SUCCESS)
            else:
                self.agent.feedback(outcome=OUTCOME_PARTIAL)

        # Check that EVIL_TWIN_SIMULATION failure weight is very high compared to success
        edges_to_evil_twin = [
            e
            for e in self.graph.edges[STATE_SECURITY_PROFILING]
            if e.to_node == ACTION_EVIL_TWIN_SIMULATION
        ]
        edges_to_passive = [
            e
            for e in self.graph.edges[STATE_SECURITY_PROFILING]
            if e.to_node == ACTION_PASSIVE_SCAN
        ]

        evil_twin_edge = edges_to_evil_twin[0]
        passive_edge = edges_to_passive[0]

        # The passive scan edge should have a higher score than the evil twin edge
        self.assertTrue(
            passive_edge.score() > evil_twin_edge.score(),
            f"Passive score {passive_edge.score()} should be greater than Evil Twin score {evil_twin_edge.score()}",
        )


if __name__ == "__main__":
    unittest.main()
