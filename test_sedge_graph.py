import unittest

from james.core.sedge import build_parrot_wifi_graph
from james.tools.constants import (
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSedgeGraph(unittest.TestCase):
    def test_build_parrot_wifi_graph(self):
        graph = build_parrot_wifi_graph()

        self.assertIsNotNone(graph)

        # Check nodes
        self.assertIn(STATE_START, graph.nodes)
        self.assertIn(STATE_NETWORK_DISCOVERY, graph.nodes)
        self.assertIn(STATE_TARGET_ANALYSIS, graph.nodes)
        self.assertIn(STATE_SECURITY_PROFILING, graph.nodes)

        self.assertIn(ACTION_PASSIVE_SCAN, graph.nodes)
        self.assertIn(ACTION_HANDSHAKE_CAPTURE, graph.nodes)
        self.assertIn(ACTION_DEAUTH_TEST, graph.nodes)
        self.assertIn(ACTION_EVIL_TWIN_SIMULATION, graph.nodes)

        # Check types
        self.assertEqual(graph.nodes[STATE_START].state_type, "state")
        self.assertEqual(graph.nodes[ACTION_PASSIVE_SCAN].state_type, "action")

        # Check some edges
        start_edges = list(graph.edges.get(STATE_START, {}).values())
        self.assertTrue(
            any(e.to_node == STATE_NETWORK_DISCOVERY for e in start_edges)
        )

        analysis_edges = list(graph.edges.get(STATE_TARGET_ANALYSIS, {}).values())
        self.assertTrue(
            any(e.to_node == ACTION_HANDSHAKE_CAPTURE for e in analysis_edges)
        )
        self.assertTrue(
            any(e.to_node == ACTION_DEAUTH_TEST for e in analysis_edges)
        )

        profiling_edges = list(graph.edges.get(STATE_SECURITY_PROFILING, {}).values())
        self.assertTrue(
            any(
                e.to_node == ACTION_EVIL_TWIN_SIMULATION
                for e in profiling_edges
            )
        )


if __name__ == "__main__":
    unittest.main()
