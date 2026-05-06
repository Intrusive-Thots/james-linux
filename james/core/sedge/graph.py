from james.core.sedge.models import Node, Edge


class DecisionGraph:
    def __init__(self) -> None:
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
