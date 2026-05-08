import unittest
from james.core.sedge.models import Node, Edge, DecisionGraph
from james.core.sedge.agent import SelfEvolvingAgent


class TestSEDGE(unittest.TestCase):
    def test_node_and_edge_creation(self):
        node = Node(id="START", state_type="scan")
        self.assertEqual(node.id, "START")
        self.assertEqual(node.state_type, "scan")

        edge = Edge(from_node="START", to_node="NETWORK_DISCOVERY")
        self.assertEqual(edge.from_node, "START")
        self.assertEqual(edge.to_node, "NETWORK_DISCOVERY")
        self.assertTrue(edge.score() > 0)

    def test_decision_graph(self):
        graph = DecisionGraph()
        node1 = Node(id="START", state_type="state")
        node2 = Node(id="NETWORK_DISCOVERY", state_type="state")
        graph.add_node(node1)
        graph.add_node(node2)

        edge = Edge(from_node="START", to_node="NETWORK_DISCOVERY")
        graph.add_edge(edge)

        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)

        best_next = graph.get_best_next("START")
        self.assertIsNotNone(best_next)
        self.assertEqual(best_next.to_node, "NETWORK_DISCOVERY")

    def test_agent_and_learning(self):
        graph = DecisionGraph()
        graph.add_node(Node(id="START", state_type="state"))
        graph.add_node(Node(id="NETWORK_DISCOVERY", state_type="state"))
        graph.add_node(Node(id="END", state_type="state"))

        graph.add_edge(Edge(from_node="START", to_node="NETWORK_DISCOVERY"))
        graph.add_edge(Edge(from_node="NETWORK_DISCOVERY", to_node="END"))

        agent = SelfEvolvingAgent(graph)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])

        next_node = agent.step()
        self.assertEqual(next_node, "NETWORK_DISCOVERY")
        self.assertEqual(agent.current_path, ["START", "NETWORK_DISCOVERY"])

        next_node = agent.step()
        self.assertEqual(next_node, "END")
        self.assertEqual(
            agent.current_path,
            ["START", "NETWORK_DISCOVERY", "END"]
        )

        agent.feedback(success=True)

        # Check if weights are updated correctly
        edges1 = graph.edges.get("START", [])
        self.assertEqual(edges1[0].visits, 1)
        self.assertTrue(edges1[0].success_weight > 1.0)
        self.assertEqual(edges1[0].failure_weight, 1.0)

        edges2 = graph.edges.get("NETWORK_DISCOVERY", [])
        self.assertEqual(edges2[0].visits, 1)
        self.assertTrue(edges2[0].success_weight > 1.0)
        self.assertEqual(edges2[0].failure_weight, 1.0)

        # check that episode reset
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == '__main__':
    unittest.main()
