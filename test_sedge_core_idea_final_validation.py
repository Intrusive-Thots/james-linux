import unittest

from james.core.sedge import build_parrot_wifi_graph, SelfEvolvingAgent
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)

class TestSedgeCoreIdeaFinalValidation(unittest.TestCase):
    """
    Test class to validate the SEDGE Core Idea Implementation.
    It verifies that optimal paths emerge, weak paths decay,
    and probabilities naturally balance.
    """

    def test_sedge_core_idea_evolution(self):
        """
        Validates the self-evolving behavior of the SEDGE graph over many runs.
        We will simulate successful outcomes for the optimal path:
        START -> NETWORK_DISCOVERY -> PASSIVE_SCAN -> TARGET_ANALYSIS ->
        HANDSHAKE_CAPTURE -> SECURITY_PROFILING -> EVIL_TWIN_SIMULATION.

        Other paths (like taking DEAUTH_TEST) will result in FAILURE.
        """
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # We simulate 1000 runs
        for _ in range(1000):
            while True:
                next_node = agent.step()
                if next_node == "halt":
                    break

            # Determine outcome based on path
            if ACTION_DEAUTH_TEST in agent.current_path:
                agent.feedback(OUTCOME_FAILURE)
            else:
                agent.feedback(OUTCOME_SUCCESS)

        # Retrieve edges from TARGET_ANALYSIS
        target_edges = graph.edges.get(STATE_TARGET_ANALYSIS, [])

        handshake_edge = next((e for e in target_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE), None)
        deauth_edge = next((e for e in target_edges if e.to_node == ACTION_DEAUTH_TEST), None)

        self.assertIsNotNone(handshake_edge)
        self.assertIsNotNone(deauth_edge)

        # Verify success path is stronger
        self.assertGreater(handshake_edge.success_weight, deauth_edge.success_weight)

        # Verify utility score (probability) of optimal path is higher
        self.assertGreater(handshake_edge.score(), deauth_edge.score())

        # Verify decayed path has higher failure weight
        self.assertGreater(deauth_edge.failure_weight, handshake_edge.failure_weight)

if __name__ == '__main__':
    unittest.main()
