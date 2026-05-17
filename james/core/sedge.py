"""
Self-Evolving Decision Graph Engine (SEDGE)

This module implements a directed, weighted decision graph that updates
via a LearningEngine using stochastic weighted selection to automatically
learn and refine optimal attack and analysis pipelines.
"""

import random
from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Calculate the utility score of this edge."""
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        """Get the edge with the highest score from a given node."""
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())


class LearningEngine:
    def update(
        self, graph: DecisionGraph, path: list[str], success: bool
    ) -> None:
        """Update the edge weights based on execution success or failure."""
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
    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """Decide the next node using weighted stochastic selection."""
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # Weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)

        # In case all weights somehow sum to 0 (unlikely given base weight of 1.0)
        if total == 0:
            probs = [1.0 / len(weights) for _ in weights]
        else:
            probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, success_signal: bool | None = None) -> str:
        """Take a step in the decision graph."""
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node
        return next_node

    def feedback(self, success: bool) -> None:
        """Provide feedback and reset the episode."""
        self.learner.update(self.graph, self.current_path, success)

        # Reset episode
        self.current_node = "START"
        self.current_path = ["START"]
