import random
from dataclasses import dataclass, field


@dataclass
class Node:
    """Represents a system situation or decision point in the decision graph."""

    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """Represents a transition between decisions, storing experience weight."""

    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Calculate the utility score based on success and failure weights."""
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    """A directed weighted decision graph for the self-evolving agent."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the decision graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge to the decision graph."""
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        """Get the edge with the highest score from the given node."""
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())


class LearningEngine:
    """Updates the decision graph based on execution feedback."""

    def update(
        self, graph: DecisionGraph, path: list[str], success: bool
    ) -> None:
        """Update weights of edges in the given path based on success."""
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
    """Makes stochastic weighted decisions balancing exploration and exploitation."""

    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """Select the next node to transition to based on edge weights."""
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # Weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)
        if total > 0:
            probs = [w / total for w in weights]
        else:
            probs = [1.0 / len(weights) for _ in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    """Agent that traverses the decision graph and evolves its strategy over time."""

    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()

        self.current_node = "START"
        self.current_path: list[str] = ["START"]

    def step(self, success_signal: bool | None = None) -> str:
        """Take a step in the decision graph and return the next node."""
        next_node = self.decision_engine.decide(self.current_node)

        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, success: bool) -> None:
        """Provide feedback for the current path and reset the episode."""
        self.learner.update(self.graph, self.current_path, success)

        # Reset episode
        self.current_node = "START"
        self.current_path = ["START"]
