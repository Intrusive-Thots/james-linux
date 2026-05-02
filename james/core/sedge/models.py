from dataclasses import dataclass, field

from james.tools.constants import (
    DEFAULT_SUCCESS_WEIGHT,
    DEFAULT_FAILURE_WEIGHT,
    DEFAULT_VISITS,
    EPSILON
)

@dataclass
class Node:
    id: str
    state_type: str  # e.g., "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)

@dataclass
class Edge:
    from_node: str
    to_node: str
    success_weight: float = DEFAULT_SUCCESS_WEIGHT
    failure_weight: float = DEFAULT_FAILURE_WEIGHT
    visits: int = DEFAULT_VISITS

    def score(self) -> float:
        return self.success_weight / (self.failure_weight + EPSILON)
