from dataclasses import dataclass, field


@dataclass
class Node:
    """Represents a system situation or decision point."""
    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """Stores experience and weight between two nodes."""
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Calculate the utility score of this path."""
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    """Core structure for the directed weighted decision graph."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a state or action node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add a transition edge between nodes."""
        if edge.from_node not in self.edges:
            self.edges[edge.from_node] = []
        self.edges[edge.from_node].append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        """Get the edge with the highest score from a given node."""
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())
