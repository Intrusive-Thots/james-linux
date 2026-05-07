import random

from james.core.sedge.models import DecisionGraph


class DecisionEngine:
    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        candidates = self.graph.edges.get(current_node, [])

        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]

        total = sum(weights)
        if total == 0:
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node
