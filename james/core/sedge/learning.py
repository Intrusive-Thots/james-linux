from james.core.sedge.models import Edge, DecisionGraph


class LearningEngine:
    def __init__(
        self, learning_rate: float = 0.1, discount_factor: float = 0.9
    ):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor

    def update_weight(self, edge: Edge, reward: float) -> None:
        """
        Updates the weight of an edge based on the reward.
        """
        # Simple Q-learning style update rule
        edge.weight = edge.weight + self.learning_rate * (reward - edge.weight)

    def apply_feedback(
        self, graph: DecisionGraph, path: list[Edge], final_reward: float
    ) -> None:
        """
        Applies a reward backwards along a sequence of edges (the path taken).
        """
        discounted_reward = final_reward
        # Update backwards from the last action
        for edge in reversed(path):
            self.update_weight(edge, discounted_reward)
            discounted_reward *= self.discount_factor
