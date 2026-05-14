from james.core.sedge.models import DecisionGraph, Node, NodeType, Edge
from james.core.sedge.learning import LearningEngine
from james.core.sedge.policy import DecisionEngine


class SelfEvolvingAgent:
    def __init__(
        self,
        epsilon: float = 0.2,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
    ):
        self.graph = DecisionGraph()
        self.learning_engine = LearningEngine(learning_rate, discount_factor)
        self.policy = DecisionEngine(epsilon)
        self._initialize_knowledge()

    def _initialize_knowledge(self) -> None:
        """
        Initializes the graph with Parrot WiFi domain concepts.
        """
        # States
        states = [
            Node(id="NETWORK_DISCOVERY", type=NodeType.STATE),
            Node(id="TARGET_ANALYSIS", type=NodeType.STATE),
            Node(id="EXPLOIT", type=NodeType.STATE),
        ]
        for state in states:
            self.graph.add_node(state)

        # Actions
        actions = [
            Node(id="PASSIVE_SCAN", type=NodeType.ACTION),
            Node(id="DEAUTH_TEST", type=NodeType.ACTION),
            Node(id="WPA_CRACK", type=NodeType.ACTION),
        ]
        for action in actions:
            self.graph.add_node(action)

        # Outcomes
        outcomes = [
            Node(id="SUCCESS", type=NodeType.OUTCOME),
            Node(id="FAILURE", type=NodeType.OUTCOME),
        ]
        for outcome in outcomes:
            self.graph.add_node(outcome)

        # Edges (State -> Action)
        self.graph.add_edge(
            Edge("NETWORK_DISCOVERY", "PASSIVE_SCAN", weight=1.0)
        )
        self.graph.add_edge(Edge("TARGET_ANALYSIS", "DEAUTH_TEST", weight=1.0))
        self.graph.add_edge(Edge("EXPLOIT", "WPA_CRACK", weight=1.0))

    def decide_next_action(self, current_state_id: str) -> str | None:
        """
        Uses the policy to decide the next action from the current state.
        """
        edge = self.policy.select_edge(self.graph, current_state_id)
        if edge:
            return edge.target
        return None

    def learn_from_feedback(
        self, path: list[Edge], final_reward: float
    ) -> None:
        """
        Updates the graph weights based on the path taken and the final reward.
        """
        self.learning_engine.apply_feedback(self.graph, path, final_reward)
