from dataclasses import dataclass, field


@dataclass
class Node:
    """Represents a system situation or decision point."""

    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """Stores experience weight between decisions."""

    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Calculate the utility score of this edge."""
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    """Directed weighted decision graph."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())
