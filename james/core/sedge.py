"""
SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE) CORE IDEA

The system builds a directed weighted decision graph where:
- Nodes = system states or actions (state nodes)
- Edges = transitions between decisions (learning paths)
- Weights = learned success utility scores (execution feedback learning)

Over time:
- successful paths become stronger
- failed paths decay
- optimal strategies emerge automatically

ARCHITECTURE

STATE NODE MODEL
Each node represents a system situation or decision point.

EDGE MODEL (LEARNING PATHS)
Edges store experience weight.

DECISION GRAPH CORE
The core structure holding the nodes and edges.

EXECUTION FEEDBACK LEARNING (KEY SYSTEM)
This is what makes it self-evolving.

DECISION ENGINE (POLICY LAYER)
This replaces static AI decisions.

SELF-EVOLUTION LOOP
This is where learning actually happens.
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
    STATE NODE MODEL

    Each node represents a system situation or decision point.
    These state nodes function as discrete state nodes mapping to actual phases
    (e.g., NETWORK_DISCOVERY) or actions (e.g., PASSIVE_SCAN) within
    the system's architecture, providing a structural foundation.

    Attributes:
        id (str): Unique string identifier for the node.
        state_type (str): Categorical classification of the state
            (e.g., "scan", "analysis", "action").
        metadata (dict[str, Any]): Optional contextual tracking metadata.
    """

    id: str
    state_type: str  # "scan", "analysis", "action"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Node(id={self.id!r}, type={self.state_type!r})"


@dataclass
class Edge:
    """
    EDGE MODEL (LEARNING PATHS)

    Edges store experience weight and act as transitions
    between decisions along learning paths.
    They govern the learning paths of the system. Over time, higher
    success_weight translates to stronger traversal probability, while
    failing paths accrue failure_weight and decay. This mechanism forms
    the basis of execution feedback learning across all learning paths.

    Attributes:
        from_node (str): Identifier of the origin node.
        to_node (str): Identifier of the destination node.
        success_weight (float): Accumulated success utility metric.
        failure_weight (float): Accumulated failure penalty metric.
        visits (int): Total occurrences of path traversal along this vector.
    """

    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def __repr__(self) -> str:
        return (
            f"Edge({self.from_node} -> {self.to_node}, "
            f"visits={self.visits}, score={self.score():.2f})"
        )

    def score(self) -> float:
        """
        Computes the proportional utility score for the transition.

        Evaluates the relative ratio of the success weight to failure weight
        as part of the execution feedback learning system. This connects the
        state nodes through learning paths.
        A small epsilon is integrated into the denominator to mitigate
        zero-division anomalies.

        Returns:
            float: The computed utility score.
        """
        return self.success_weight / (self.failure_weight + SEDGE_EPSILON)


class DecisionGraph:
    """
    DECISION GRAPH CORE

    Serves as the central state tracking structure for the SEDGE
    ecosystem for the self-evolution loop.
    The system builds a directed weighted decision graph where:
    - Nodes = system states or actions (state nodes).
    - Edges = transitions between decisions (learning paths).
    - Weights = learned success utility scores based on historical execution
      outcomes (execution feedback learning).

    Over time, successful paths become stronger, failed paths decay, and
    optimal strategies emerge automatically.
    This creates a living decision ecosystem instead of static scripts.
    """

    def __init__(self) -> None:
        """Initializes a new, empty decision graph."""
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}
        self.edges_dict: dict[str, dict[str, Edge]] = {}

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
        self.edges_dict.setdefault(edge.from_node, {})[edge.to_node] = edge

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
        self.edges_dict.clear()

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
            edges_dict = self.edges_dict.get(frm)
            if edges_dict and to in edges_dict:
                total_score += edges_dict[to].score()
                edge_count += 1
            else:
                return 0.0  # Path is broken

        if edge_count == 0:
            return 0.0

        return total_score / edge_count


class LearningEngine:
    """
    EXECUTION FEEDBACK LEARNING (KEY SYSTEM)

    This execution feedback learning is what makes the system
    "self-evolving" across the self-evolution loop.
    Successful sequences (e.g., scan -> analyze -> handshake_capture) gain
    higher success_weight and stronger traversal probability along paths.
    Failed sequences gain higher failure_weight and reduced probability,
    causing unstable techniques to decay automatically.
    """

    def update(
        self, graph: DecisionGraph, path: list[str], outcome: str
    ) -> None:
        """
        Adjusts the experiential weights of all edges in a completed path.

        Args:
            graph (DecisionGraph): The decision graph undergoing updates.
            path (list[str]): The sequential path of node IDs traversed.
            outcome (str): The final result (e.g., 'SUCCESS', 'FAILURE').
        """
        for frm, to in zip(path[:-1], path[1:]):
            edges_dict = graph.edges_dict.get(frm)
            if edges_dict and to in edges_dict:
                e = edges_dict[to]
                e.visits += 1
                if outcome == OUTCOME_SUCCESS:
                    e.success_weight += 1.0
                elif outcome == OUTCOME_FAILURE:
                    e.failure_weight += 1.0
                elif outcome == OUTCOME_PARTIAL:
                    e.success_weight += 0.5
                    e.failure_weight += 0.5


class DecisionEngine:
    """
    DECISION ENGINE (POLICY LAYER)

    This policy layer replaces static "AI decisions" to drive the
    self-evolution loop.
    Uses weighted stochastic selection to balance exploration vs exploitation.
    The system naturally balances:
    - exploration (trying weak paths occasionally)
    - exploitation (using strong known paths)
    This is achieved via stochastic weighted selection across the graph
    using the established learning paths.
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
        Determines the optimal subsequent transition stochastically
        using utility scores.

        Args:
            current_node (str): The identifier of the currently active node.

        Returns:
            str | None: The identifier of the stochastically selected
                        subsequent node, or None if no valid candidate
                        paths exist.
        """
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # Calculate utility scores for weighted stochastic selection
        weights = [c.score() for c in candidates]
        total = sum(weights)

        # Fallback to uniform random selection if cumulative utility is <= 0
        # This zero-utility fallback logic prevents zero-division errors when
        # all path candidates have an accumulated weight of 0.0 or lower.
        # By falling back to uniform random selection, it distributes
        # selections equally to balance exploration vs exploitation.
        if total <= 0.0:
            return random.choice(candidates).to_node

        probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    """
    SELF-EVOLUTION LOOP

    This self-evolution loop is where learning actually happens.

    HOW IT LEARNS OPTIMAL PATHS
    Over time, successful sequences gain:
    - higher success_weight
    - stronger traversal probability

    Failed sequences gain:
    - higher failure_weight
    - reduced probability

    EXPLORATION vs EXPLOITATION
    System naturally balances:
    - exploration (trying weak paths occasionally)
    - exploitation (using strong known paths)
    This is achieved via stochastic weighted selection.

    After enough runs, the graph converges toward optimal pipelines,
    unstable techniques decay, and workflows become dominant paths,
    creating a living decision ecosystem instead of static scripts.
    """

    def __init__(self, graph: DecisionGraph) -> None:
        """
        Initializes the autonomous agent within the provided decision graph.

        Args:
            graph (DecisionGraph): The environment map to traverse.
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
    HOW THIS MAPS TO YOUR PARROT WIFI SYSTEM

    You can map nodes like:
    - States: NETWORK_DISCOVERY, TARGET_ANALYSIS, SECURITY_PROFILING
    - Actions: PASSIVE_SCAN, HANDSHAKE_CAPTURE, DEAUTH_TEST,
               EVIL_TWIN_SIMULATION (authorized only)
    - Outcomes: SUCCESS, FAILURE, PARTIAL_SIGNAL

    REAL EVOLUTION BEHAVIOR
    After enough runs:
    - graph converges toward optimal attack/analysis pipelines
    - unstable techniques decay automatically
    - high-yield workflows become dominant paths

    This creates a living decision ecosystem instead of static scripts.

    Returns:
        DecisionGraph: The fully initialized decision graph ecosystem.
    """
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
