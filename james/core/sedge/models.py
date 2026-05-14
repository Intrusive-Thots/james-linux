from dataclasses import dataclass, field


class NodeType:
    STATE = "STATE"
    ACTION = "ACTION"
    OUTCOME = "OUTCOME"


@dataclass
class Node:
    id: str
    type: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)


class DecisionGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def get_edges(self, source_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == source_id]
