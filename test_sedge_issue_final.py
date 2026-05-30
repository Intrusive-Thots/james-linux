import unittest
from james.core.sedge import (
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
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
)


class TestSedgeIssueFinal(unittest.TestCase):
    """
    Final comprehensive tests targeting the self-evolving graph engine
    logic specifically validating the probabilistic behavior across many
    iterations.
    """

    def setUp(self):
        self.graph = DecisionGraph()
        self.learner = LearningEngine()

    def test_probabilistic_behavior(self):
        decision_engine = DecisionEngine(self.graph)

        edge_b = Edge(
            from_node="A", to_node="B", success_weight=90.0, failure_weight=1.0
        )
        edge_c = Edge(
            from_node="A", to_node="C", success_weight=1.0, failure_weight=90.0
        )
        self.graph.add_edge(edge_b)
        self.graph.add_edge(edge_c)

        counts = {"B": 0, "C": 0}
        iterations = 1000
        for _ in range(iterations):
            choice = decision_engine.decide("A")
            counts[choice] += 1

        self.assertGreater(counts["B"], counts["C"] * 10)

    def test_learning_engine_weight_updates(self):
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)

        path = ["A", "B"]

        self.learner.update(self.graph, path, OUTCOME_SUCCESS)
        self.assertEqual(edge.visits, 1)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)

        self.learner.update(self.graph, path, OUTCOME_FAILURE)
        self.assertEqual(edge.visits, 2)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)

        self.learner.update(self.graph, path, OUTCOME_PARTIAL)
        self.assertEqual(edge.visits, 3)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)

    def test_agent_evolution_convergence(self):
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        iterations = 1000
        handshake_selections = 0
        deauth_selections = 0

        for _ in range(iterations):
            outcome = OUTCOME_PARTIAL
            while True:
                node = agent.step()
                if node == "halt":
                    break

                if node == ACTION_HANDSHAKE_CAPTURE:
                    outcome = OUTCOME_SUCCESS
                    handshake_selections += 1
                    break
                elif node == ACTION_DEAUTH_TEST:
                    outcome = OUTCOME_FAILURE
                    deauth_selections += 1
                    break

            agent.feedback(outcome)

        analysis_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])
        handshake_edge = next(
            (
                e
                for e in analysis_edges
                if e.to_node == ACTION_HANDSHAKE_CAPTURE
            ),
            None,
        )
        deauth_edge = next(
            (e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST),
            None,
        )

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        self.assertGreater(
            handshake_edge.success_weight, deauth_edge.success_weight
        )
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        self.assertGreater(
            deauth_edge.failure_weight, handshake_edge.failure_weight
        )

        self.assertGreater(handshake_selections, deauth_selections)
        self.assertGreater(deauth_selections, 0)


if __name__ == "__main__":
    unittest.main()
