import random
from typing import List, Optional

from james.core.sedge.graph import DecisionGraph

class LearningEngine:
    def update(self, graph: DecisionGraph, path: List[str], success: bool):
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if success:
                        e.success_weight += 1.0
                    else:
                        e.failure_weight += 1.0

class DecisionEngine:
    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str) -> Optional[str]:
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)
        if total <= 0:
             # handle case where all weights might be 0, though score should always be > 0
             return random.choice(candidates).to_node

        probs = [w / total for w in weights]
        return random.choices(candidates, weights=probs)[0].to_node
