"""
SELF-EVOLVING DECISION GRAPH ENGINE (SEDGE)

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


@dataclass
class Node:
    """
    Represents a system situation or decision point in the decision graph.

    Nodes define the state the system is currently in, mapped to various
    network discovery, analysis, or action phases.

    Example States:
        - NETWORK_DISCOVERY
        - TARGET_ANALYSIS
        - SECURITY_PROFILING
    """

    id: str
    state_type: str  # "scan", "analysis", "action"
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    """
    Represents a transition between decisions, storing experience weight.

    Edges hold learned values based on whether traversing this path resulted
    in success or failure in the past, allowing the system to self-evolve.

    Example Actions:
        - PASSIVE_SCAN
        - HANDSHAKE_CAPTURE
        - DEAUTH_TEST
        - EVIL_TWIN_SIMULATION

    Example Outcomes:
        - SUCCESS
        - FAILURE
        - PARTIAL_SIGNAL
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
        to the failure weight, heavily favoring successful paths.

        Returns:
            float: The computed utility score.
        """
        return self.success_weight / (self.failure_weight + 1e-6)


class DecisionGraph:
    """
    Directed weighted decision graph storing nodes and edges.

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

    def get_best_next(self, node_id: str) -> Edge | None:
        """
        Returns the best next edge based on the highest utility score.

        Args:
            node_id (str): The identifier of the current node.

        Returns:
            Edge | None: The best edge to traverse, or None if no edges exist.
        """
        edges = self.edges.get(node_id, [])
        if not edges:
            return None
        return max(edges, key=lambda e: e.score())


class LearningEngine:
    """
    Updates edge weights across the graph based on execution feedback.

    This implements the learning mechanism that allows optimal
    strategies to emerge over time automatically. Over time:
        - Successful paths become stronger (higher success_weight)
        - Failed paths decay (higher failure_weight)
    """

    def update(
        self, graph: DecisionGraph, path: list[str], outcome: str
    ) -> None:
        """
        Updates the success and failure weights of edges in a given path.

        Args:
            graph (DecisionGraph): The current decision graph.
            path (list[str]): The sequence of node IDs traversed.
            success (bool): Whether the overall operation was successful.
        """
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if outcome == "SUCCESS":
                        e.success_weight += 1.0
                    elif outcome == "FAILURE":
                        e.failure_weight += 1.0
                    elif outcome == "PARTIAL_SIGNAL":
                        e.success_weight += 0.5
                        e.failure_weight += 0.5


class DecisionEngine:
    """
    Policy layer for making stochastic weighted selections.

    Instead of static rules, it uses a probabilistic model balancing
    exploration of new paths and exploitation of known strong paths.
    The system naturally balances exploration (trying weak paths occasionally)
    with exploitation (using strong known paths) via stochastic
    weighted selection.
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
            str | None: The ID of the next node to transition to, or None.
        """
        candidates = self.graph.edges.get(current_node, [])
        if not candidates:
            return None

        # weighted stochastic selection (exploration + exploitation)
        weights = [c.score() for c in candidates]
        total = sum(weights)
        probs = [w / total for w in weights]

        return random.choices(candidates, weights=probs)[0].to_node


class SelfEvolvingAgent:
    """
    Agent that learns optimal paths through a self-evolution loop.

    The agent walks the graph and continuously improves its logic
    via the underlying DecisionEngine and LearningEngine. After enough runs,
    the graph converges toward optimal attack/analysis pipelines,
    unstable techniques decay automatically, and high-yield workflows
    become dominant paths. This creates a living decision ecosystem
    instead of static scripts.
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
        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, outcome_signal: str | None = None) -> str:
        """Executes a single step in the decision graph."""
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, outcome: str) -> None:
        """Applies feedback to the learning engine and resets the episode."""
        self.learner.update(self.graph, self.current_path, outcome)
        # reset episode
        self.current_node = "START"
        self.current_path = ["START"]
