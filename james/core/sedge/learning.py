"""
SEDGE Learning Engine.

Handles weight adjustments based on action outcomes (SUCCESS/FAILURE)
to evolve optimal analysis and attack pipelines.
"""

from james.core.sedge.models import DecisionGraph, Edge

class LearningEngine:
    """Updates edge weights in a DecisionGraph based on outcomes."""

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9) -> None:
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor

    def update_weight(self, graph: DecisionGraph, edge: Edge, outcome: str, reward: float = 0.0) -> None:
        """
        Update the weight (Q-value) of an edge based on the outcome.

        Args:
            graph: The DecisionGraph containing the edge.
            edge: The Edge that was executed.
            outcome: Outcome string, typically 'SUCCESS' or 'FAILURE'.
            reward: Optional explicit reward value, overriding the outcome default.
        """
        if reward == 0.0:
            if outcome == "SUCCESS":
                reward = 1.0
            elif outcome == "FAILURE":
                reward = -0.5
            else:
                reward = 0.0

        # Simple Q-learning style update
        # Q(s, a) = Q(s, a) + alpha * [reward + gamma * max(Q(s', a')) - Q(s, a)]

        # Find max Q-value for next state
        next_edges = graph.get_outgoing_edges(edge.target_id)
        max_next_q = 0.0
        if next_edges:
            max_next_q = max(e.weight for e in next_edges)

        current_q = edge.weight
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)

        # Ensure weight doesn't drop below a minimum threshold for exploration
        edge.weight = max(0.1, new_q)
