"""
Test suite for the SEDGE (Self-Evolving Decision Graph Engine) architecture.
"""

import unittest
from james.core.sedge.models import DecisionGraph, Node, Edge
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.agent import SelfEvolvingAgent

class TestSEDGE(unittest.TestCase):

    def setUp(self):
        self.graph = DecisionGraph()
        self.node_a = Node("A", "State A")
        self.node_b = Node("B", "State B")
        self.node_c = Node("C", "State C", is_terminal=True)

        self.graph.add_node(self.node_a)
        self.graph.add_node(self.node_b)
        self.graph.add_node(self.node_c)

    def test_decision_graph_creation(self):
        """Verify DecisionGraph node and edge creation."""
        edge_ab = Edge("A", "B", "ACTION_1")
        self.graph.add_edge(edge_ab)

        self.assertEqual(len(self.graph.nodes), 3)
        self.assertEqual(len(self.graph.get_outgoing_edges("A")), 1)
        self.assertEqual(self.graph.get_edge("A", "ACTION_1"), edge_ab)
        self.assertIsNone(self.graph.get_edge("A", "NON_EXISTENT_ACTION"))

    def test_learning_engine_weight_update_success(self):
        """Verify LearningEngine increases weight on SUCCESS."""
        edge_ab = Edge("A", "B", "ACTION_1", weight=0.5)
        self.graph.add_edge(edge_ab)

        learning_engine = LearningEngine(learning_rate=0.5, discount_factor=0.0)
        initial_weight = edge_ab.weight

        learning_engine.update_weight(self.graph, edge_ab, outcome="SUCCESS")

        self.assertGreater(edge_ab.weight, initial_weight)

    def test_learning_engine_weight_update_failure(self):
        """Verify LearningEngine decreases weight on FAILURE."""
        edge_ab = Edge("A", "B", "ACTION_1", weight=1.0)
        self.graph.add_edge(edge_ab)

        learning_engine = LearningEngine(learning_rate=0.5, discount_factor=0.0)
        initial_weight = edge_ab.weight

        learning_engine.update_weight(self.graph, edge_ab, outcome="FAILURE")

        self.assertLess(edge_ab.weight, initial_weight)

    def test_decision_engine_exploitation(self):
        """Verify DecisionEngine selects highest weight edge when exploiting."""
        edge1 = Edge("A", "B", "ACTION_1", weight=1.0)
        edge2 = Edge("A", "C", "ACTION_2", weight=5.0)
        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        # Set epsilon to 0 to force exploitation
        decision_engine = DecisionEngine(epsilon=0.0)
        selected_edge = decision_engine.select_action(self.graph, "A")

        self.assertEqual(selected_edge.action_name, "ACTION_2")

    def test_self_evolving_agent_workflow(self):
        """Verify the full agent workflow from IDLE to ATTACK_EXECUTION."""
        # Force exploitation for predictable tests
        agent = SelfEvolvingAgent(epsilon=0.0)

        self.assertEqual(agent.current_state, "IDLE")

        action = agent.get_next_action()
        self.assertEqual(action, "START_SCAN")

        agent.execute_action(action)
        self.assertEqual(agent.current_state, "NETWORK_DISCOVERY")

        action = agent.get_next_action()
        self.assertEqual(action, "SELECT_TARGET")

        agent.execute_action(action)
        self.assertEqual(agent.current_state, "TARGET_ANALYSIS")

        # In TARGET_ANALYSIS, PASSIVE_SCAN has higher default weight (1.0) than DEAUTH_TEST (0.8)
        action = agent.get_next_action()
        self.assertEqual(action, "PASSIVE_SCAN")

        agent.execute_action(action)
        self.assertEqual(agent.current_state, "ATTACK_EXECUTION")

if __name__ == "__main__":
    unittest.main()
