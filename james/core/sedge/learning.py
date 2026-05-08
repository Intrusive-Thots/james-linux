from .models import Edge, Outcome

class RLUpdater:
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.alpha = learning_rate
        self.gamma = discount_factor

    def update_weight(self, edge: Edge, outcome: Outcome, reward: float):
        edge.outcomes[outcome] += 1
        # Q-learning style update
        edge.weight = (1 - self.alpha) * edge.weight + self.alpha * reward
