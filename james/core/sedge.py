from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

@dataclass
class Node:
    id: str
    state_type: str  # "scan", "analysis", "action"
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

    def get_best_next(self, node_id: str) -> Optional[Edge]:
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())

class LearningEngine:
    def update(self, graph: DecisionGraph, path: List[str], success: bool):
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if success:
                        e.success_weight += 1.0
                    else:
                        e.failure_weight += 1.0

class DecisionEngine:
    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str) -> Optional[str]:
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)
        if total == 0:
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]
        return random.choices(candidates, weights=probs)[0].to_node

class SelfEvolvingAgent:
    def __init__(self, graph: DecisionGraph):
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, success_signal: Optional[bool] = None) -> str:
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node
        return next_node

    def feedback(self, success: bool):
        self.learner.update(self.graph, self.current_path, success)
        # reset episode
        self.current_node = "START"
        self.current_path = ["START"]
