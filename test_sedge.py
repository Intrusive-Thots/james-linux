import unittest
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def setUp(self):
        self.graph = DecisionGraph()

        # Add Nodes
        self.graph.add_node(Node(id="START", state_type="start"))
        self.graph.add_node(Node(id="NETWORK_DISCOVERY", state_type="scan"))
        self.graph.add_node(Node(id="TARGET_ANALYSIS", state_type="analysis"))
        self.graph.add_node(Node(id="PASSIVE_SCAN", state_type="action"))
        self.graph.add_node(Node(id="HANDSHAKE_CAPTURE", state_type="action"))

        # Add Edges
        self.graph.add_edge(
            Edge(from_node="START", to_node="NETWORK_DISCOVERY")
        )
        self.graph.add_edge(
            Edge(from_node="NETWORK_DISCOVERY", to_node="TARGET_ANALYSIS")
        )
        self.graph.add_edge(
            Edge(from_node="TARGET_ANALYSIS", to_node="PASSIVE_SCAN")
        )
        self.graph.add_edge(
            Edge(from_node="TARGET_ANALYSIS", to_node="HANDSHAKE_CAPTURE")
        )

        self.agent = SelfEvolvingAgent(self.graph)

    def test_initial_state(self):
        self.assertEqual(self.agent.current_node, "START")
        self.assertEqual(self.agent.current_path, ["START"])

    def test_step_execution(self):
        next_node = self.agent.step()
        self.assertEqual(next_node, "NETWORK_DISCOVERY")
        self.assertEqual(self.agent.current_node, "NETWORK_DISCOVERY")
        self.assertEqual(
            self.agent.current_path, ["START", "NETWORK_DISCOVERY"]
        )

        next_node = self.agent.step()
        self.assertEqual(next_node, "TARGET_ANALYSIS")

        next_node = self.agent.step()
        self.assertIn(next_node, ["PASSIVE_SCAN", "HANDSHAKE_CAPTURE"])

        # Next step should halt because there are no outgoing edges
        next_node = self.agent.step()
        self.assertEqual(next_node, "halt")

    def test_feedback_learning_and_reset(self):
        self.agent.step()  # START -> NETWORK_DISCOVERY
        self.agent.step()  # NETWORK_DISCOVERY -> TARGET_ANALYSIS
        last_node = self.agent.step()  # -> PASSIVE_SCAN or HANDSHAKE_CAPTURE

        self.agent.feedback(success=True)

        self.assertEqual(self.agent.current_node, "START")
        self.assertEqual(self.agent.current_path, ["START"])

        # Check that edges got visits and updated weights
        edges = self.graph.edges["START"]
        self.assertEqual(edges[0].visits, 1)
        self.assertEqual(edges[0].success_weight, 2.0)
        self.assertEqual(edges[0].failure_weight, 1.0)

        edges = self.graph.edges["TARGET_ANALYSIS"]
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
        self.agent.step()  # -> PASSIVE_SCAN or HANDSHAKE_CAPTURE

        self.agent.feedback(success=False)

        edges = self.graph.edges["START"]
        self.assertEqual(edges[0].visits, 1)
        self.assertEqual(edges[0].success_weight, 1.0)
        self.assertEqual(edges[0].failure_weight, 2.0)


if __name__ == "__main__":
    unittest.main()
