from dataclasses import dataclass, field


@dataclass
class Node:
    """Represents a system state or decision point."""
    id: str
    state_type: str  # "scan", "analysis", "action", etc.
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """Represents a transition between decisions."""
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """Returns the learned success utility score."""
        return self.success_weight / (self.failure_weight + 1e-6)
