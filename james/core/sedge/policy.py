"""
SEDGE Decision Engine (Policy).

Implements decision policies (like epsilon-greedy) to balance
exploration and exploitation in the decision graph.
"""

import random
from james.core.sedge.models import DecisionGraph, Edge

class DecisionEngine:
    """Selects actions using an epsilon-greedy policy."""

    def __init__(self, epsilon: float = 0.2) -> None:
        """
        Args:
            epsilon: Probability of exploring a random action instead of exploiting the best known action.
        """
        self.epsilon = epsilon

    def select_action(self, graph: DecisionGraph, current_node_id: str) -> Edge | None:
        """
        Select the next edge to traverse from the current node.

        Args:
            graph: The DecisionGraph.
            current_node_id: ID of the node the agent is currently at.

        Returns:
            The selected Edge, or None if no valid actions are available.
        """
        edges = graph.get_outgoing_edges(current_node_id)

        if not edges:
            return None

        # Exploration: choose a random action
        if random.random() < self.epsilon:
            return random.choice(edges)

        # Exploitation: choose the action with the highest weight
        # If there are multiple actions with the same highest weight, randomly pick one
        max_weight = max(e.weight for e in edges)
        best_edges = [e for e in edges if e.weight == max_weight]

        return random.choice(best_edges)
