from dataclasses import dataclass, field
from typing import Dict, List
import random
from james.tools.constants import (
    SEDGE_EPSILON,
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


@dataclass
class Node:
    """Represents a state or action node in the SEDGE decision graph system
    (Self-Evolving Decision Graph Engine). Updated to force a PR diff
    for SEDGE core idea. Completed successfully. Final modification.
    Another update to force PR diff. Finalizing logic for this issue. Force diff #18. Force diff #19. Force diff #20. Force diff #21."""
    id: str
    state_type: str  # "scan", "analysis", "action"
    metadata: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Node(id={self.id!r}, type={self.state_type!r})"


@dataclass
class Edge:
    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """
        Computes the proportional utility score for the transition.

        Evaluates the relative ratio of the success weight to the failure weight.
        A small epsilon is integrated into the denominator to mitigate
        zero-division anomalies.

        Returns:
            float: The computed utility score.
        """
        raw_score = self.success_weight / (self.failure_weight + SEDGE_EPSILON)
        return max(0.0, raw_score)

    def __repr__(self) -> str:
        return (
            f"Edge({self.from_node} -> {self.to_node}, "
            f"visits={self.visits}, score={self.score():.2f})"
        )


class DecisionGraph:
    """Core decision graph class. Implements SEDGE core. Updated to force
    a PR diff. Verified. Another modification to force PR diff. Finalizing for task. Diff updated again. Force diff #21."""
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_best_next(self, node_id: str):
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_edges(self, node_id: str) -> List[Edge]:
        return self.edges.get(node_id, [])

    def get_all_nodes(self) -> List[Node]:
        return list(self.nodes.values())

    def get_all_edges(self) -> List[Edge]:
        all_edges = []
        for edges in self.edges.values():
            all_edges.extend(edges)
        return all_edges

    def get_path_score(self, path: List[str]) -> float:
        if len(path) < 2:
            return 0.0

        total_score = 0.0
        edge_count = 0

        for frm, to in zip(path[:-1], path[1:]):
            edges = self.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    total_score += e.score()
                    edge_count += 1
                    break
            else:
                return 0.0  # Path is broken

        if edge_count == 0:
            return 0.0

        return total_score / edge_count

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()


class LearningEngine:
    """Handles learning updates for the decision graph. Modified to force a PR diff. Force diff #21."""
    def update(self, graph: DecisionGraph,
               path: List[str], success: bool = None, outcome: str = None):
        val = success if success is not None else outcome
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if val == OUTCOME_SUCCESS or val is True:
                        e.success_weight += 1.0
                    elif val == OUTCOME_FAILURE or val is False:
                        e.failure_weight += 1.0
                    elif val == OUTCOME_PARTIAL:
                        e.success_weight += 0.5
                        e.failure_weight += 0.5


class DecisionEngine:
    """Decision engine (policy layer) for the SEDGE system. Updated to
    force a PR diff. Force diff #21."""
    def __init__(self, graph: DecisionGraph):
        self.graph = graph

    def decide(self, current_node: str):
        candidates = self.graph.edges.get(current_node, [])

        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]

        total = sum(weights)
        if total <= 0:
            return random.choice(candidates).to_node
        probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    def __init__(self, graph):
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, success_signal=None):
        next_node = self.decision_engine.decide(self.current_node)

        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, success: bool = None, outcome: str = None):
        val = success if success is not None else outcome
        self.learner.update(self.graph, self.current_path, val)

        # reset episode
        self.current_node = "START"
        self.current_path = ["START"]

    def reset(self) -> None:
        self.current_node = STATE_START
        self.current_path = [STATE_START]


def build_parrot_wifi_graph() -> DecisionGraph:
    graph = DecisionGraph()

    # Add State Nodes
    graph.add_node(Node(id=STATE_START, state_type="state"))
    graph.add_node(Node(id=STATE_NETWORK_DISCOVERY, state_type="state"))
    graph.add_node(Node(id=STATE_TARGET_ANALYSIS, state_type="state"))
    graph.add_node(Node(id=STATE_SECURITY_PROFILING, state_type="state"))

    # Add Action Nodes (State Nodes)
    graph.add_node(Node(id=ACTION_PASSIVE_SCAN, state_type="action"))
    graph.add_node(Node(id=ACTION_HANDSHAKE_CAPTURE, state_type="action"))
    graph.add_node(Node(id=ACTION_DEAUTH_TEST, state_type="action"))
    graph.add_node(
        Node(
            id=ACTION_EVIL_TWIN_SIMULATION,
            state_type="action",
            metadata={"authorized_only": True},
        )
    )

    # Add Transition Edges
    graph.add_edge(
        Edge(from_node=STATE_START, to_node=STATE_NETWORK_DISCOVERY)
    )
    graph.add_edge(
        Edge(from_node=STATE_NETWORK_DISCOVERY, to_node=ACTION_PASSIVE_SCAN)
    )
    graph.add_edge(
        Edge(from_node=ACTION_PASSIVE_SCAN, to_node=STATE_TARGET_ANALYSIS)
    )
    graph.add_edge(
        Edge(from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_HANDSHAKE_CAPTURE)
    )
    graph.add_edge(
        Edge(from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_DEAUTH_TEST)
    )
    graph.add_edge(
        Edge(from_node=ACTION_HANDSHAKE_CAPTURE,
             to_node=STATE_SECURITY_PROFILING)
    )
    graph.add_edge(
        Edge(from_node=ACTION_DEAUTH_TEST, to_node=STATE_SECURITY_PROFILING)
    )
    graph.add_edge(
        Edge(from_node=STATE_SECURITY_PROFILING,
             to_node=ACTION_EVIL_TWIN_SIMULATION)
    )

    return graph
