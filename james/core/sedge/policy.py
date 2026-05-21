import random
from james.core.sedge.models import DecisionGraph


class DecisionEngine:
    """Policy layer replacing static AI decisions
    using stochastic selection.
    """

    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # Weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)

        # If total is 0, fallback to uniform
        if total == 0:
            probs = [1.0 / len(weights) for _ in weights]
        else:
            probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node
