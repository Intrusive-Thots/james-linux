"""
SEDGE (Self-Evolving Decision Graph Engine) Models.

Defines the core data structures for the decision graph:
- Node: Represents a state in the pentesting workflow.
- Edge: Represents an action or transition between states.
- DecisionGraph: The container that manages nodes and edges.
"""

from dataclasses import dataclass, field


@dataclass
class Node:
    """A state or phase in the decision graph."""
    id: str
    name: str
    description: str = ""
    is_terminal: bool = False


@dataclass
class Edge:
    """A transition or action between nodes."""
    source_id: str
    target_id: str
    action_name: str
    weight: float = 1.0  # Learned weight/probability/Q-value
    metadata: dict = field(default_factory=dict)


class DecisionGraph:
    """Directed weighted graph representing the decision space."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        # Mapping of source node ID to list of outgoing edges
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self.edges:
            self.edges[node.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge between existing nodes."""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError(f"Source {edge.source_id} or target {edge.target_id} not found in graph.")

        if edge.source_id not in self.edges:
            self.edges[edge.source_id] = []
        self.edges[edge.source_id].append(edge)

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by its ID."""
        return self.nodes.get(node_id)

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        """Get all outgoing edges from a specific node."""
        return self.edges.get(node_id, [])

    def get_edge(self, source_id: str, action_name: str) -> Edge | None:
        """Get a specific edge by source ID and action name."""
        edges = self.get_outgoing_edges(source_id)
        for edge in edges:
            if edge.action_name == action_name:
                return edge
        return None
