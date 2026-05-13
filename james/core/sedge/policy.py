import random

from james.core.sedge.models import DecisionGraph


class DecisionEngine:
    """Makes decisions based on the decision graph and stochastic selection."""

    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """Decides the next node to visit."""
        candidates = self.graph.edges.get(current_node, [])

        if not candidates:
            return None

        # Weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)

        if total == 0:
            # Fallback if weights somehow total 0 to prevent div by zero
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]

        # random.choices returns a list of length k (default 1)
        selected_edge = random.choices(candidates, weights=probs)[0]
        return selected_edge.to_node
