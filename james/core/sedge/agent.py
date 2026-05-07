"""
SEDGE Agent Wrapper.

Wraps the models, learning engine, and policy engine into a cohesive
agent interface for the main JAMES orchestrator to use.
"""

from james.core.sedge.models import DecisionGraph, Node, Edge
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine

class SelfEvolvingAgent:
    """
    Main entry point for SEDGE functionality.
    Initializes the domain states and coordinates decision making and learning.
    """

    def __init__(self, epsilon: float = 0.2, learning_rate: float = 0.1, discount_factor: float = 0.9) -> None:
        self.graph = DecisionGraph()
        self.learning_engine = LearningEngine(learning_rate=learning_rate, discount_factor=discount_factor)
        self.decision_engine = DecisionEngine(epsilon=epsilon)
        self.current_state: str | None = None

        self._initialize_domain()

    def _initialize_domain(self) -> None:
        """Initialize the decision graph with Parrot WiFi domain concepts."""
        # Define Nodes (States)
        nodes = [
            Node("IDLE", "Idle State", "Awaiting commands"),
            Node("NETWORK_DISCOVERY", "Network Discovery", "Scanning for networks"),
            Node("TARGET_ANALYSIS", "Target Analysis", "Analyzing a specific target network"),
            Node("ATTACK_EXECUTION", "Attack Execution", "Executing an attack against the target"),
            Node("SUCCESS_STATE", "Success", "Attack succeeded", is_terminal=True),
            Node("FAILURE_STATE", "Failure", "Attack failed", is_terminal=True),
        ]
        for n in nodes:
            self.graph.add_node(n)

        # Define Edges (Actions)
        edges = [
            Edge("IDLE", "NETWORK_DISCOVERY", "START_SCAN"),
            Edge("NETWORK_DISCOVERY", "TARGET_ANALYSIS", "SELECT_TARGET"),
            Edge("TARGET_ANALYSIS", "ATTACK_EXECUTION", "PASSIVE_SCAN", weight=1.0),
            Edge("TARGET_ANALYSIS", "ATTACK_EXECUTION", "DEAUTH_TEST", weight=0.8),
            Edge("ATTACK_EXECUTION", "SUCCESS_STATE", "REPORT_SUCCESS"),
            Edge("ATTACK_EXECUTION", "FAILURE_STATE", "REPORT_FAILURE"),
            # Allow restarting from failure
            Edge("FAILURE_STATE", "TARGET_ANALYSIS", "RETRY_ANALYSIS", weight=0.5),
        ]
        for e in edges:
            self.graph.add_edge(e)

        self.current_state = "IDLE"

    def get_next_action(self) -> str | None:
        """Get the name of the next recommended action based on the current state."""
        if not self.current_state:
            return None

        edge = self.decision_engine.select_action(self.graph, self.current_state)
        if edge:
            return edge.action_name
        return None

    def execute_action(self, action_name: str, outcome: str = "PENDING") -> None:
        """
        Transition to the next state based on the action, and update weights
        if an outcome (SUCCESS/FAILURE) is provided.
        """
        if not self.current_state:
            return

        edge = self.graph.get_edge(self.current_state, action_name)
        if not edge:
            raise ValueError(f"Action {action_name} not valid from state {self.current_state}")

        # Update weight if an outcome is reported
        if outcome in ["SUCCESS", "FAILURE"]:
            self.learning_engine.update_weight(self.graph, edge, outcome)

        # Transition state
        self.current_state = edge.target_id

    def reset(self) -> None:
        """Reset the agent's state to IDLE."""
        self.current_state = "IDLE"
