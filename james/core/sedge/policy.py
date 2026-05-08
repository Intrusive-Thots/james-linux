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

        # avoid division by zero if all weights are 0
        if total == 0:
            probs = [1.0 / len(weights) for _ in weights]
        else:
            probs = [w / total for w in weights]

        selected_edge = random.choices(candidates, weights=probs, k=1)[0]
        return selected_edge.to_node
