"""
SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE)

# SEDGE CORE IDEA implementation

Core Idea:
The system builds a directed weighted decision graph where:
  - Nodes = system states or actions
  - Edges = transitions between decisions
  - Weights = learned success utility scores

Over time, successful paths become stronger and failed paths decay,
allowing optimal strategies to emerge automatically.
"""

import random
from dataclasses import dataclass, field
from typing import Any

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
    """
    State node model representing a decision point or system situation.

    Nodes define the current status of the system, effectively mapping to
    network discovery, analysis, or actionable phases within the self-evolving
    decision graph.

    Attributes:
        id (str): The unique identifier.
        state_type (str): The type of state (e.g., 'scan', 'action').
        metadata (dict[str, Any]): Arbitrary metadata contextualizing the state.
    """

    id: str
    state_type: str  # "scan", "analysis", "action"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Node(id={self.id!r}, type={self.state_type!r})"


@dataclass
class Edge:
    """
    Edge model representing transitions and learning paths within the graph.

    Edges encapsulate experience weights based on the historical success or
    failure resulting from traversal. This feedback mechanism facilitates the
    self-evolution of optimal strategies over time.

    Attributes:
        from_node (str): The source node identifier.
        to_node (str): The destination node identifier.
        success_weight (float): The accumulated success utility score.
        failure_weight (float): The accumulated failure penalty score.
        visits (int): The total number of traversals across this edge.
    """

    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def __repr__(self) -> str:
        return f"Edge({self.from_node} -> {self.to_node}, visits={self.visits}, score={self.score():.2f})"

    def score(self) -> float:
        """
        Computes the overall utility score for this transition.

        The utility score is the ratio of the success weight to the failure
        weight. A minimal epsilon is added to the denominator to prevent
        zero division.

        Returns:
            float: The computed utility score.
        """
        return self.success_weight / (self.failure_weight + SEDGE_EPSILON)


class DecisionGraph:
    """
    Core representation of the Self-Evolving Decision Graph Engine (SEDGE).

    This structure is the foundation of the directed, weighted decision
    system. Nodes represent states or actions, and edges represent transitions.
    Over time, successful paths organically strengthen while failed paths decay,
    enabling dynamic AI optimization.
    """

    def __init__(self) -> None:
        """Initializes a new, empty decision graph."""
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """
        Incorporates a discrete node into the decision ecosystem.

        Args:
            node (Node): The state or action node to integrate.
        """
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """
        Establishes a directed transition between two nodes in the graph.

        Args:
            edge (Edge): The relational edge mapping the transition.
        """
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_node(self, node_id: str) -> Node | None:
        """
        Retrieves a specific node by its unique identifier.

        Args:
            node_id (str): The target node's identifier.

        Returns:
            Node | None: The requested node, or None if it does not exist.
        """
        return self.nodes.get(node_id)

    def get_edges(self, node_id: str) -> list[Edge]:
        """
        Extracts all outbound edges originating from a specified node.

        Args:
            node_id (str): The identifier of the origin node.

        Returns:
            list[Edge]: A collection of all connecting outbound edges.
        """
        return self.edges.get(node_id, [])

    def get_all_nodes(self) -> list[Node]:
        """
        Aggregates all registered nodes within the graph.

        Returns:
            list[Node]: A comprehensive list of existing nodes.
        """
        return list(self.nodes.values())

    def get_all_edges(self) -> list[Edge]:
        """
        Aggregates all registered edges within the graph.

        Returns:
            list[Edge]: A comprehensive list of existing edges.
        """
        all_edges = []
        for edges in self.edges.values():
            all_edges.extend(edges)
        return all_edges

    def clear(self) -> None:
        """
        Flushes the graph, removing all nodes and relational edges.
        """
        self.nodes.clear()
        self.edges.clear()

    def get_best_next(self, node_id: str) -> Edge | None:
        """
        Identifies the optimal subsequent transition from a given node.

        Args:
            node_id (str): The current node identifier.

        Returns:
            Edge | None: The highest-scoring outbound edge, or None.
        """
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())

    def get_path_score(self, path: list[str]) -> float:
        """
        Evaluates the mean utility score across a complete traversal path.

        Args:
            path (list[str]): The sequential sequence of node identifiers.

        Returns:
            float: The average utility score. Returns 0.0 if the path is
                   invalid or contains fewer than two nodes.
        """
        if len(path) < 2:
            return 0.0

        total_score = 0.0
        edge_count = 0

        for frm, to in zip(path[:-1], path[1:]):
            edges = self.edges.get(frm, [])
            found = False
            for e in edges:
                if e.to_node == to:
                    total_score += e.score()
                    edge_count += 1
                    found = True
                    break
            if not found:
                return 0.0  # Path is broken

        if edge_count == 0:
            return 0.0

        return total_score / edge_count


class LearningEngine:
    """
    Execution feedback learning system driving continuous graph evolution.

    This engine is responsible for retrospectively updating the utility weights
    of traversed edges based on real-world outcomes. This backpropagation of
    success guarantees that reliable strategies gain prominence.
    """

    def update(
        self, graph: DecisionGraph, path: list[str], outcome: str
    ) -> None:
        """
        Adjusts the experiential weights of all edges in a completed path.

        Args:
            graph (DecisionGraph): The decision graph undergoing updates.
            path (list[str]): The sequential path of node identifiers traversed.
            outcome (str): The final result (e.g., 'SUCCESS', 'FAILURE').
        """
        for frm, to in zip(path[:-1], path[1:]):
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if outcome == OUTCOME_SUCCESS:
                        e.success_weight += 1.0
                    elif outcome == OUTCOME_FAILURE:
                        e.failure_weight += 1.0
                    elif outcome == OUTCOME_PARTIAL:
                        e.success_weight += 0.5
                        e.failure_weight += 0.5
                    break


class DecisionEngine:
    """
    Policy layer facilitating dynamic, stochastic node selection.

    By employing weighted stochastic selection, this engine balances the
    exploration of novel or underdeveloped paths with the exploitation of
    established, high-yield trajectories.
    """

    def __init__(self, graph: DecisionGraph) -> None:
        """
        Constructs the decision engine mapped to a specific graph.

        Args:
            graph (DecisionGraph): The foundational decision ecosystem.
        """
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """
        Determines the optimal subsequent transition stochastically.

        Args:
            current_node (str): The identifier of the active node.

        Returns:
            str | None: The identifier of the selected node, or None if halted.
        """
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)

        # Handle zero-division edge case and fallback to uniform selection
        if total <= 0.0:
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    """
    Orchestrator driving the core autonomous evolution loop.

    This agent continuously navigates the graph, executes decisions, and
    applies real-world feedback to cultivate an organically optimizing
    intelligence ecosystem.
    """

    def __init__(self, graph: DecisionGraph) -> None:
        """
        Initializes the autonomous agent within the provided decision graph.

        Args:
            graph (DecisionGraph): The environment map to traverse and optimize.
        """
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = STATE_START
        self.current_path = [STATE_START]

    def step(self, outcome_signal: str | None = None) -> str:
        """
        Advances the agent one step forward along the decision graph.

        Args:
            outcome_signal (str | None): Optional signal influencing traversal.

        Returns:
            str: The target node identifier, or 'halt' if traversal terminates.
        """
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, outcome: str) -> None:
        """
        Submits traversal outcomes to the learning engine and resets state.

        Args:
            outcome (str): The final execution state (e.g., 'SUCCESS').
        """
        self.learner.update(self.graph, self.current_path, outcome)
        self.reset()

    def reset(self) -> None:
        """
        Restores the agent to the starting node to begin a new epoch.
        """
        self.current_node = STATE_START
        self.current_path = [STATE_START]


def build_parrot_wifi_graph() -> DecisionGraph:
    """
    Factory function to build the Parrot WiFi SEDGE graph domain map.

    Constructs a decision graph specific to the Parrot WiFi system, containing:
      - States: NETWORK_DISCOVERY, TARGET_ANALYSIS, SECURITY_PROFILING
      - Actions: PASSIVE_SCAN, HANDSHAKE_CAPTURE, DEAUTH_TEST, EVIL_TWIN_SIMULATION
      - Outcomes: SUCCESS, FAILURE, PARTIAL_SIGNAL

    Through continued evaluation, the graph converges toward optimal pipelines
    where strong paths flourish and weak paths naturally decay.

    Returns:
        DecisionGraph: The configured decision graph ecosystem.
    """
    graph = DecisionGraph()

    # Add State Nodes
    graph.add_node(Node(id=STATE_START, state_type="state"))
    graph.add_node(Node(id=STATE_NETWORK_DISCOVERY, state_type="state"))
    graph.add_node(Node(id=STATE_TARGET_ANALYSIS, state_type="state"))
    graph.add_node(Node(id=STATE_SECURITY_PROFILING, state_type="state"))

    # Add Action Nodes
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

    # Sequence: START -> Network Discovery
    graph.add_edge(
        Edge(from_node=STATE_START, to_node=STATE_NETWORK_DISCOVERY)
    )

    # Sequence: Network Discovery -> Passive Scan -> Target Analysis
    graph.add_edge(
        Edge(from_node=STATE_NETWORK_DISCOVERY, to_node=ACTION_PASSIVE_SCAN)
    )
    graph.add_edge(
        Edge(from_node=ACTION_PASSIVE_SCAN, to_node=STATE_TARGET_ANALYSIS)
    )

    # Target Analysis -> Actions
    graph.add_edge(
        Edge(from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_HANDSHAKE_CAPTURE)
    )
    graph.add_edge(
        Edge(from_node=STATE_TARGET_ANALYSIS, to_node=ACTION_DEAUTH_TEST)
    )

    # Actions -> Security Profiling
    graph.add_edge(
        Edge(
            from_node=ACTION_HANDSHAKE_CAPTURE,
            to_node=STATE_SECURITY_PROFILING,
        )
    )
    graph.add_edge(
        Edge(from_node=ACTION_DEAUTH_TEST, to_node=STATE_SECURITY_PROFILING)
    )

    # Security Profiling -> Evil Twin Simulation
    graph.add_edge(
        Edge(
            from_node=STATE_SECURITY_PROFILING,
            to_node=ACTION_EVIL_TWIN_SIMULATION,
        )
    )

    return graph


# Core implementation of the SEDGE ecosystem initialized
