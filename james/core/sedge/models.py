from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Node:
    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
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
