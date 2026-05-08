import random
from typing import List
from .models import Edge, Action

class Policy:
    def __init__(self, epsilon: float = 0.2):
        self.epsilon = epsilon

    def select_action(self, available_edges: List[Edge]) -> Edge:
        if not available_edges:
            return None

        # Exploration
        if random.random() < self.epsilon:
            return random.choice(available_edges)

        # Exploitation
        return max(available_edges, key=lambda e: e.weight)
