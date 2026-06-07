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
    """
    Tests for the deterministic structure of the SEDGE ecosystem graph mapped to Parrot WiFi.
    """

    def test_build_parrot_wifi_graph_deterministic_structure(self):
        """
        Verifies the exact deterministic instantiation of the Parrot WiFi decision graph,
        asserting the complete node registry, exact edge connections, default weights,
        and required metadata properties.
        """
        graph = build_parrot_wifi_graph()

        self.assertIsNotNone(graph)

        expected_nodes = {
            STATE_START: "state",
            STATE_NETWORK_DISCOVERY: "state",
            STATE_TARGET_ANALYSIS: "state",
            STATE_SECURITY_PROFILING: "state",
            ACTION_PASSIVE_SCAN: "action",
            ACTION_HANDSHAKE_CAPTURE: "action",
            ACTION_DEAUTH_TEST: "action",
            ACTION_EVIL_TWIN_SIMULATION: "action",
        }

        # Check exact number of nodes
        self.assertEqual(len(graph.nodes), len(expected_nodes))

        # Check each node type and presence
        for node_id, node_type in expected_nodes.items():
            self.assertIn(node_id, graph.nodes)
            self.assertEqual(graph.nodes[node_id].state_type, node_type)

        # Validate metadata specifically for EVIL_TWIN_SIMULATION
        self.assertTrue(
            graph.nodes[ACTION_EVIL_TWIN_SIMULATION].metadata.get("authorized_only", False)
        )

        expected_edges = {
            STATE_START: [STATE_NETWORK_DISCOVERY],
            STATE_NETWORK_DISCOVERY: [ACTION_PASSIVE_SCAN],
            ACTION_PASSIVE_SCAN: [STATE_TARGET_ANALYSIS],
            STATE_TARGET_ANALYSIS: [ACTION_HANDSHAKE_CAPTURE, ACTION_DEAUTH_TEST],
            ACTION_HANDSHAKE_CAPTURE: [STATE_SECURITY_PROFILING],
            ACTION_DEAUTH_TEST: [STATE_SECURITY_PROFILING],
            STATE_SECURITY_PROFILING: [ACTION_EVIL_TWIN_SIMULATION],
            ACTION_EVIL_TWIN_SIMULATION: [],
        }

        # Validate edges
        for from_node, to_nodes in expected_edges.items():
            edges_from_node = graph.edges.get(from_node, [])
            actual_to_nodes = [e.to_node for e in edges_from_node]
            self.assertCountEqual(actual_to_nodes, to_nodes)

            # Ensure default weights are exactly 1.0 for newly instantiated graph
            for edge in edges_from_node:
                self.assertEqual(edge.success_weight, 1.0)
                self.assertEqual(edge.failure_weight, 1.0)
                self.assertEqual(edge.visits, 0)


if __name__ == "__main__":
    unittest.main()
