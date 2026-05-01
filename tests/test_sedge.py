import unittest
from james.core.sedge.graph import Node, Edge, DecisionGraph
from james.core.sedge.engine import LearningEngine, DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent

class TestSEDGE(unittest.TestCase):
    def test_graph_creation(self):
        graph = DecisionGraph()
        n1 = Node(id="START", state_type="start")
        n2 = Node(id="SCAN", state_type="scan")
        graph.add_node(n1)
        graph.add_node(n2)

        e1 = Edge(from_node="START", to_node="SCAN")
        graph.add_edge(e1)

        self.assertEqual(graph.nodes["START"], n1)
        self.assertEqual(len(graph.edges["START"]), 1)

    def test_engine_update_and_decide(self):
        graph = DecisionGraph()
        graph.add_node(Node(id="START", state_type="start"))
        graph.add_node(Node(id="SCAN", state_type="scan"))
        graph.add_edge(Edge(from_node="START", to_node="SCAN"))

        learning_engine = LearningEngine()
        learning_engine.update(graph, ["START", "SCAN"], True)

        self.assertEqual(graph.edges["START"][0].visits, 1)
        self.assertEqual(graph.edges["START"][0].success_weight, 2.0)

        decision_engine = DecisionEngine(graph)
        next_node = decision_engine.decide("START")
        self.assertEqual(next_node, "SCAN")

    def test_agent_step_and_feedback(self):
        graph = DecisionGraph()
        graph.add_node(Node(id="START", state_type="start"))
        graph.add_node(Node(id="SCAN", state_type="scan"))
        graph.add_edge(Edge(from_node="START", to_node="SCAN"))

        agent = SelfEvolvingAgent(graph)
        self.assertEqual(agent.current_node, "START")

        next_node = agent.step()
        self.assertEqual(next_node, "SCAN")
        self.assertEqual(agent.current_node, "SCAN")
        self.assertEqual(agent.current_path, ["START", "SCAN"])

        agent.feedback(True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])
        self.assertEqual(graph.edges["START"][0].visits, 1)

if __name__ == "__main__":
    unittest.main()
