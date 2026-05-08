from typing import List, Dict, Any
from .models import Graph, State, Action, Edge, Outcome
from .learning import RLUpdater
from .policy import Policy

class SEDGEAgent:
    def __init__(self):
        self.graph = Graph(
            nodes=list(State),
            edges=self._initialize_edges()
        )
        self.current_state = State.INITIAL
        self.updater = RLUpdater()
        self.policy = Policy()

    def _initialize_edges(self) -> List[Edge]:
        # Basic graph structure for WiFi auditing
        return [
            Edge(State.INITIAL, Action.PASSIVE_SCAN, State.NETWORK_DISCOVERY),
            Edge(State.NETWORK_DISCOVERY, Action.ACTIVE_SCAN, State.TARGET_ANALYSIS),
            Edge(State.TARGET_ANALYSIS, Action.DEAUTH_TEST, State.ATTACK_PLANNING),
            Edge(State.ATTACK_PLANNING, Action.PMKID_CAPTURE, State.EXPLOITATION),
            Edge(State.ATTACK_PLANNING, Action.WPA_HANDSHAKE, State.EXPLOITATION),
        ]

    def get_available_actions(self) -> List[Edge]:
        return [e for e in self.graph.edges if e.source == self.current_state]

    def step(self) -> Action:
        edges = self.get_available_actions()
        selected_edge = self.policy.select_action(edges)
        if selected_edge:
            return selected_edge.action
        return None

    def feedback(self, action: Action, outcome: Outcome, reward: float):
        # Find edge
        edge = next((e for e in self.graph.edges
                     if e.source == self.current_state and e.action == action), None)
        if edge:
            self.updater.update_weight(edge, outcome, reward)
            # Transition
            if outcome == Outcome.SUCCESS:
                self.current_state = edge.target
