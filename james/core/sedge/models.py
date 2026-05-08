from dataclasses import dataclass, field
from james.tools.constants import (
    DEFAULT_SUCCESS_WEIGHT,
    DEFAULT_FAILURE_WEIGHT,
    EPSILON
)


@dataclass
class Node:
    id: str
    state_type: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    from_node: str
    to_node: str
    success_weight: float = DEFAULT_SUCCESS_WEIGHT
    failure_weight: float = DEFAULT_FAILURE_WEIGHT
    visits: int = 0

    def score(self) -> float:
        return self.success_weight / (self.failure_weight + EPSILON)


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
