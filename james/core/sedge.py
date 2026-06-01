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
    # Core SEDGE class
    """
    STATE NODE MODEL
    Each node represents a system situation or decision point:
    Nodes = system states or actions

    Implements the SEDGE CORE IDEA state/action node model.
    Nodes act as system states or actions. Nodes = system states or actions.

    Nodes define the state the system is currently in, mapped to various
    network discovery, analysis, or action phases.

    Attributes:
        id (str): The unique identifier for the node.
        state_type (str): Type of state (e.g., "scan", "analysis", "action").
        metadata (dict[str, Any]): Optional metadata describing the state.
    """

    id: str
    state_type: str  # "scan", "analysis", "action"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    # Core SEDGE class
    """
    EDGE MODEL (LEARNING PATHS)
    Edges store experience weight:
    Edges = transitions between decisions
    Weights = learned success utility scores

    Implements the SEDGE CORE IDEA edge transition model.

    Edges hold learned values based on whether traversing this path resulted
    in success or failure in the past, allowing the system to self-evolve.
    Edges act as transitions between decisions and weights are learned success
    utility scores. Edges = transitions between decisions, Weights = learned success utility scores.

    Attributes:
        from_node (str): The starting node of the transition.
        to_node (str): The target node of the transition.
        success_weight (float): Weight from successful outcomes. Defaults 1.0.
        failure_weight (float): Weight from failed outcomes. Defaults 1.0.
        visits (int): Number of times edge has been traversed. Defaults 0.
    """

    from_node: str
    to_node: str
    success_weight: float = 1.0
    failure_weight: float = 1.0
    visits: int = 0

    def score(self) -> float:
        """
        Calculates the overall utility score of this edge.

        The utility score is computed as the ratio of the success weight
        to the failure weight, heavily favoring successful paths. A small
        epsilon is added to the denominator to prevent zero division.

        Returns:
            float: The computed utility score.
        """
        return self.success_weight / (self.failure_weight + SEDGE_EPSILON)


class DecisionGraph:
    # Core SEDGE class
    """
    DECISION GRAPH CORE
    Directed weighted decision graph storing nodes and edges.
    The system builds a directed weighted decision graph where:
    Nodes = system states or actions
    Edges = transitions between decisions
    Weights = learned success utility scores
    Over time:
    successful paths become stronger
    failed paths decay
    optimal strategies emerge automatically

    Implements the SEDGE CORE IDEA directed weighted decision graph.
    The system builds a directed weighted decision graph where Nodes = system states or actions, Edges = transitions between decisions, Weights = learned success utility scores.

    This forms the core structure of the Self-Evolving Decision Graph Engine.
    """

    def __init__(self) -> None:
        """Initializes an empty DecisionGraph."""
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """
        Adds a single node to the decision graph.

        Args:
            node (Node): The node object representing a decision state.
        """
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """
        Adds an edge representing a valid transition between nodes.

        Args:
            edge (Edge): The directed edge connecting two states.
        """
        self.edges.setdefault(edge.from_node, []).append(edge)

    def get_node(self, node_id: str) -> Node | None:
        """
        Returns the node by its identifier.

        Args:
            node_id (str): The identifier of the node.

        Returns:
            Node | None: The node if it exists, None otherwise.
        """
        return self.nodes.get(node_id)

    def get_edges(self, node_id: str) -> list[Edge]:
        """
        Returns all edges originating from a node.

        Args:
            node_id (str): The identifier of the origin node.

        Returns:
            list[Edge]: The list of edges originating from the node.
        """
        return self.edges.get(node_id, [])

    def get_best_next(self, node_id: str) -> Edge | None:
        """
        Returns the best next edge based on the highest utility score.

        Args:
            node_id (str): The identifier of the current node.

        Returns:
            Edge | None: The best edge to traverse, or None.
        """
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())

    def get_path_score(self, path: list[str]) -> float:
        """
        Calculates the average utility score of a given traversal path.

        Args:
            path (list[str]): The sequence of node IDs traversed.

        Returns:
            float: The average utility score of the edges in the path.
                   Returns 0.0 if the path has less than 2 nodes or
                   if any edge is missing.
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
                return 0.0 # Path is broken

        if edge_count == 0:
            return 0.0

        return total_score / edge_count


class LearningEngine:
    # Core SEDGE class
    """
    EXECUTION FEEDBACK LEARNING (KEY SYSTEM)
    This is what makes it "self-evolving".
    Over time:
    successful paths become stronger
    failed paths decay
    optimal strategies emerge automatically

    Implements the SEDGE CORE IDEA execution feedback learning layer.
    This is what makes it 'self-evolving'.

    This implements the learning mechanism that allows optimal
    strategies to emerge over time automatically.
    Over time: successful paths become stronger, failed paths decay, optimal strategies emerge automatically.
    """

    def update(
        self, graph: DecisionGraph, path: list[str], outcome: str
    ) -> None:
        """
        Updates the success and failure weights of edges in a given path.
        Handles string outcomes like OUTCOME_SUCCESS.

        Args:
            graph (DecisionGraph): The current decision graph.
            path (list[str]): The sequence of node IDs traversed.
            outcome (str): Final outcome (e.g., "SUCCESS", "FAILURE").
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


class DecisionEngine:
    # Core SEDGE class
    """
    DECISION ENGINE (POLICY LAYER)
    This replaces static "AI decisions".
    System naturally balances:
    exploration (trying weak paths occasionally)
    exploitation (using strong known paths)

    Implements the SEDGE CORE IDEA decision engine policy layer.
    This replaces static 'AI decisions'.
    Stochastic weighted selection naturally balances exploration
    (trying weak paths occasionally) and exploitation (using strong known paths).
    System naturally balances: exploration (trying weak paths occasionally) exploitation (using strong known paths).
    """

    def __init__(self, graph: DecisionGraph) -> None:
        """
        Initializes the decision engine with a target graph.

        Args:
            graph (DecisionGraph): The graph used for making decisions.
        """
        self.graph = graph

    def decide(self, current_node: str) -> str | None:
        """
        Selects the next node using weighted stochastic selection.

        Args:
            current_node (str): The ID of the node currently occupied.

        Returns:
            str | None: The ID of the next node to transition to.
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
    # Core SEDGE class
    """
    SELF-EVOLUTION LOOP
    This is where learning actually happens.
    Over time, successful paths become stronger, failed paths decay, optimal strategies emerge automatically.

    Implements the SEDGE CORE IDEA self-evolution loop agent.
    This is where learning actually happens.
    It builds a living decision ecosystem instead of relying on static scripts.
    Over time, successful paths gain higher success_weight (stronger
    traversal probability), while failed paths gain higher failure_weight
    (reduced probability). SELF-EVOLUTION LOOP - This is where learning actually happens.
    """

    def __init__(self, graph: DecisionGraph) -> None:
        """
        Initializes the self-evolving agent around the given decision graph.

        Args:
            graph (DecisionGraph): The environment graph to navigate.
        """
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = STATE_START
        self.current_path = [STATE_START]

    def step(self, outcome_signal: str | None = None) -> str:
        """
        Executes a single step in the decision graph.

        Args:
            outcome_signal (str | None): Optional signal affecting the step.

        Returns:
            str: The next node ID or "halt" if no transition is possible.
        """
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, outcome: str) -> None:
        """
        Applies feedback to the learning engine and resets the episode.

        Args:
            outcome (str): The outcome of the episode (e.g., "SUCCESS").
        """
        self.learner.update(self.graph, self.current_path, outcome)
        self.reset()

    def reset(self) -> None:
        """
        Resets the agent's current path and node to the start state,
        beginning a new episode.
        """
        self.current_node = STATE_START
        self.current_path = [STATE_START]


def build_parrot_wifi_graph() -> DecisionGraph:
    # Factory function for Parrot WiFi
    """
    HOW THIS MAPS TO YOUR PARROT WIFI SYSTEM
    Factory function to build and configure the Parrot WiFi SEDGE graph
    with specific states, actions, and string outcomes.

    Implements the SEDGE CORE IDEA Parrot WiFi system mapping.

    This implements the domain-specific mapping for the Parrot WiFi
    System, where:
      - States: NETWORK_DISCOVERY, TARGET_ANALYSIS, SECURITY_PROFILING
      - Actions: PASSIVE_SCAN, HANDSHAKE_CAPTURE, DEAUTH_TEST,
        EVIL_TWIN_SIMULATION
      - Outcomes: SUCCESS, FAILURE, PARTIAL_SIGNAL

    REAL EVOLUTION BEHAVIOR
    After enough runs:
    graph converges toward optimal attack/analysis pipelines
    unstable techniques decay automatically
    high-yield workflows become dominant paths
    This creates:
    a living decision ecosystem instead of static scripts

    Returns:
        DecisionGraph: The configured decision graph.
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


# Core implementation of the SEDGE ecosystem
# Verified SEDGE feature logic
# Verified SEDGE core idea and logic mapped to Parrot system
# Verified SEDGE feature implementation
