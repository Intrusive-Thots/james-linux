import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    SelfEvolvingAgent,
)
from james.tools.constants import STATE_START, STATE_NETWORK_DISCOVERY


class TestSedgeSelfEvolvingCore(unittest.TestCase):
    """
    Tests for the functionally expanded methods in the SEDGE core.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.node_a = Node(id="A", state_type="state")
        self.node_b = Node(id="B", state_type="action")
        self.edge_ab = Edge(from_node="A", to_node="B")

        self.graph.add_node(self.node_a)
        self.graph.add_node(self.node_b)
        self.graph.add_edge(self.edge_ab)

        self.agent = SelfEvolvingAgent(self.graph)

    def test_decision_graph_get_node(self):
        """Test getting a node by ID from DecisionGraph."""
        node = self.graph.get_node("A")
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "A")
        self.assertEqual(node.state_type, "state")

        missing_node = self.graph.get_node("MISSING")
        self.assertIsNone(missing_node)

    def test_decision_graph_get_edges(self):
        """Test getting edges by origin node ID from DecisionGraph."""
        edges = self.graph.get_edges("A")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].from_node, "A")
        self.assertEqual(edges[0].to_node, "B")

        missing_edges = self.graph.get_edges("B")
        self.assertEqual(len(missing_edges), 0)

    def test_self_evolving_agent_reset(self):
        """Test resetting the agent episode state."""
        self.agent.current_node = "SOME_NODE"
        self.agent.current_path = ["START", "SOME_NODE"]

        self.agent.reset()

        self.assertEqual(self.agent.current_node, STATE_START)
        self.assertEqual(self.agent.current_path, [STATE_START])

if __name__ == "__main__":
    unittest.main()
