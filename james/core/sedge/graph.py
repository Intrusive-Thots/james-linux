from james.core.sedge.models import Node, Edge


class DecisionGraph:
    """Core directed weighted decision graph engine."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Adds a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Adds an edge to the graph."""
        if edge.from_node not in self.edges:
            self.edges[edge.from_node] = []
        self.edges[edge.from_node].append(edge)

    def get_best_next(self, node_id: str) -> Edge | None:
        """Returns the edge with the highest score."""
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())
