import random
from james.core.sedge.graph import DecisionGraph


class DecisionEngine:
    """Decision engine for stochastic weighted node selection."""

    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """Returns the next node based on stochastic weighted selection."""
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        weights = [c.score() for c in candidates]
        total = sum(weights)
        if total == 0:
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]
        return random.choices(candidates, weights=probs)[0].to_node
