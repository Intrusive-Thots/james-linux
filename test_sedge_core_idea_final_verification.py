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


class TestSedgeCoreIdeaFinalVerification(unittest.TestCase):
    """
    Comprehensive verification tests specifically confirming the entire SEDGE
    Core Idea functionality, explicitly checking metadata, weight adjustments,
    and agent feedback convergence over time.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_node_metadata_and_attributes(self):
        """Verifies Node instantiates correctly with metadata."""
        node = Node(id="test_id", state_type="action", metadata={"auth": True})
        self.assertEqual(node.id, "test_id")
        self.assertEqual(node.state_type, "action")
        self.assertTrue(node.metadata.get("auth"))
        self.assertIn("test_id", repr(node))

    def test_edge_weight_learning_update_success(self):
        """Verifies that edges adjust weights properly based on successful outcomes."""
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)
        self.learner.update(self.graph, ["A", "B"], OUTCOME_SUCCESS)

        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertGreater(edge.score(), 1.0)

    def test_edge_weight_learning_update_failure(self):
        """Verifies that edges adjust weights properly based on failed outcomes."""
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)
        self.learner.update(self.graph, ["A", "B"], OUTCOME_FAILURE)

        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 2.0)
        self.assertLess(edge.score(), 1.0)

    def test_decision_engine_stochastic_selection(self):
        """Verifies DecisionEngine correctly utilizes weighted stochastic probabilities."""
        engine = DecisionEngine(self.graph)

        strong_edge = Edge(from_node="X", to_node="Y", success_weight=100.0, failure_weight=1.0)
        weak_edge = Edge(from_node="X", to_node="Z", success_weight=1.0, failure_weight=100.0)

        self.graph.add_edge(strong_edge)
        self.graph.add_edge(weak_edge)

        selections = {"Y": 0, "Z": 0}
        iterations = 1000

        for _ in range(iterations):
            choice = engine.decide("X")
            if choice:
                selections[choice] += 1

        self.assertGreater(selections["Y"], selections["Z"] * 10)

    def test_decision_engine_fallback_zero_utility(self):
        """Verifies DecisionEngine handles extreme zero-utility cases gracefully."""
        engine = DecisionEngine(self.graph)

        edge1 = Edge(from_node="X", to_node="Y", success_weight=0.0, failure_weight=0.0)
        edge2 = Edge(from_node="X", to_node="Z", success_weight=0.0, failure_weight=0.0)

        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)

        selections = {"Y": 0, "Z": 0}
        iterations = 1000

        for _ in range(iterations):
            choice = engine.decide("X")
            if choice:
                selections[choice] += 1

        self.assertGreater(selections["Y"], 100)
        self.assertGreater(selections["Z"], 100)

    def test_self_evolving_agent_loop_convergence(self):
        """Verifies the SelfEvolvingAgent correctly learns and converges across iterations."""
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # We will heavily bias HANDSHAKE as SUCCESS and DEAUTH as FAILURE
        for _ in range(1000):
            while True:
                node = agent.step()
                if node == "halt":
                    agent.reset()
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    agent.feedback(OUTCOME_SUCCESS)
                    break
                elif node == ACTION_DEAUTH_TEST:
                    agent.feedback(OUTCOME_FAILURE)
                    break

        # Extract the target analysis edges
        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next((e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        # Verify the agent evolved the weights
        self.assertGreater(handshake_edge.success_weight, 1.0)
        self.assertGreater(deauth_edge.failure_weight, 1.0)
        self.assertGreater(handshake_edge.score(), deauth_edge.score())


if __name__ == "__main__":
    unittest.main()
