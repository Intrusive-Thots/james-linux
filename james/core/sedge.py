"""
Self-Evolving Decision Graph Engine (SEDGE) Core.

This module provides the implementation of the SEDGE system, which builds a
directed weighted decision graph to learn and evolve optimal attack and analysis
pipelines autonomously.
"""

from dataclasses import dataclass, field
import random


@dataclass
class Node:
    """Represents a system state or decision point."""
    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """Represents a transition between decisions with learned success weights."""
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Calculate the utility score of this edge."""
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    """The directed, weighted decision graph storing states and transitions."""
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the decision graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge representing a path between two nodes."""
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        """Retrieve the edge with the highest score from the given node."""
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())


class LearningEngine:
    """Updates the decision graph based on execution feedback."""
    def update(self, graph: DecisionGraph, path: list[str], success: bool) -> None:
        """Update the edge weights along a traversal path."""
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
    """Policy layer replacing static scripts with stochastic path selection."""
    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """Stochastically select the next node based on current edge weights."""
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        weights = [c.score() for c in candidates]
        total = sum(weights)
        if total == 0:
            return None

        probs = [w / total for w in weights]
        chosen_edge = random.choices(candidates, weights=probs)[0]
        return chosen_edge.to_node


class SelfEvolvingAgent:
    """The self-evolution loop for traversing and learning optimal paths."""
    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()

        self.current_node = "START"
        self.current_path: list[str] = ["START"]

    def step(self, success_signal: bool | None = None) -> str:
        """Take a single step through the decision graph."""
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node
        return next_node

    def feedback(self, success: bool) -> None:
        """Provide feedback for the current traversal and reset the episode."""
        self.learner.update(self.graph, self.current_path, success)

        # Reset episode
        self.current_node = "START"
        self.current_path = ["START"]
