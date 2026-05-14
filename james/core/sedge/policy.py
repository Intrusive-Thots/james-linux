import random
from james.core.sedge.models import DecisionGraph, Edge


class DecisionEngine:
    def __init__(self, epsilon: float = 0.2):
        """
        epsilon: The probability of exploration (choosing a random action).
                 1 - epsilon is prob of exploitation (choosing best action).
        """
        self.epsilon = epsilon

    def select_edge(
        self, graph: DecisionGraph, current_state_id: str
    ) -> Edge | None:
        """
        Selects the next edge to traverse based on the current state
        and epsilon-greedy policy.
        """
        available_edges = graph.get_edges(current_state_id)
        if not available_edges:
            return None

        # Exploration
        if random.random() < self.epsilon:
            return random.choice(available_edges)

        # Exploitation
        return max(available_edges, key=lambda e: e.weight)

    def get_best_edge(
        self, graph: DecisionGraph, current_state_id: str
    ) -> Edge | None:
        """
        Selects the next edge purely based on maximum weight
        (pure exploitation).
        """
        available_edges = graph.get_edges(current_state_id)
        if not available_edges:
            return None
        return max(available_edges, key=lambda e: e.weight)
