from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Node:
    id: str
    state_type: str  # e.g. "scan", "analysis", "action"
    metadata: Dict = field(default_factory=dict)

@dataclass
class Edge:
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        return self.success_weight / (self.failure_weight + 1e-6)

class DecisionGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[Edge]] = {}

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str) -> Optional[str]:
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score()).to_node
