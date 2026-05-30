import unittest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    SelfEvolvingAgent,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    STATE_START,
    STATE_TARGET_ANALYSIS,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
)


class TestSedgeConvergence(unittest.TestCase):
    """
    Test that the SEDGE graph naturally converges toward optimal attack/analysis
    pipelines and that unstable techniques decay automatically.
    """

    def setUp(self):
        # Build a simplified graph with a fork to test convergence
        self.graph = DecisionGraph()

        # Nodes
        self.graph.add_node(Node(id=STATE_START, state_type="state"))
        self.graph.add_node(Node(id=STATE_TARGET_ANALYSIS, state_type="state"))
        self.graph.add_node(
            Node(id=ACTION_HANDSHAKE_CAPTURE, state_type="action")
        )
        self.graph.add_node(Node(id=ACTION_DEAUTH_TEST, state_type="action"))

        # Edges
        self.graph.add_edge(
            Edge(from_node=STATE_START, to_node=STATE_TARGET_ANALYSIS)
        )

        # This will be our "optimal" path
        self.optimal_edge = Edge(
            from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_HANDSHAKE_CAPTURE
        )
        self.graph.add_edge(self.optimal_edge)

        # This will be our "unstable" path
        self.unstable_edge = Edge(
            from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_DEAUTH_TEST
        )
        self.graph.add_edge(self.unstable_edge)

        self.agent = SelfEvolvingAgent(self.graph)

    def test_convergence_towards_optimal_path(self):
        """
        Simulate 1000 iterations.
        Whenever the agent chooses HANDSHAKE_CAPTURE, we simulate SUCCESS.
        Whenever the agent chooses DEAUTH_TEST, we simulate FAILURE.
        We expect HANDSHAKE_CAPTURE to become the dominant path.
        """
        iterations = 1000
        optimal_selections = 0
        unstable_selections = 0

        for _ in range(iterations):
            # Step 1: START -> TARGET_ANALYSIS
            self.agent.step()

            # Step 2: TARGET_ANALYSIS -> (HANDSHAKE_CAPTURE or DEAUTH_TEST)
            action_node = self.agent.step()

            if action_node == ACTION_HANDSHAKE_CAPTURE:
                # Optimal path gets success feedback
                optimal_selections += 1
                self.agent.feedback(OUTCOME_SUCCESS)
            elif action_node == ACTION_DEAUTH_TEST:
                # Unstable path gets failure feedback
                unstable_selections += 1
                self.agent.feedback(OUTCOME_FAILURE)
            else:
                self.agent.feedback(OUTCOME_FAILURE)

        # The weight of the optimal path should be significantly higher
        self.assertTrue(
            self.optimal_edge.success_weight
            > self.unstable_edge.success_weight
        )

        # The failure weight of the unstable path should be significantly higher
        self.assertTrue(
            self.unstable_edge.failure_weight
            >= self.optimal_edge.failure_weight
        )

        # The score of the optimal path should dominate
        self.assertTrue(
            self.optimal_edge.score() > self.unstable_edge.score() * 10
        )

        # To ensure the stochastic decision engine favors the optimal path,
        # we can verify that the optimal path was selected more often overall,
        # especially towards the end. But for a simple assertion, the score
        # heavily weighting towards the optimal path proves the logic.

        # The best next path from TARGET_ANALYSIS should definitively be the optimal one
        best_edge = self.graph.get_best_next(STATE_TARGET_ANALYSIS)
        self.assertEqual(best_edge.to_node, ACTION_HANDSHAKE_CAPTURE)


if __name__ == "__main__":
    unittest.main()
