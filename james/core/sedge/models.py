from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any

class State(str, Enum):
    INITIAL = "INITIAL"
    NETWORK_DISCOVERY = "NETWORK_DISCOVERY"
    TARGET_ANALYSIS = "TARGET_ANALYSIS"
    ATTACK_PLANNING = "ATTACK_PLANNING"
    EXPLOITATION = "EXPLOITATION"
    POST_EXPLOITATION = "POST_EXPLOITATION"

class Action(str, Enum):
    PASSIVE_SCAN = "PASSIVE_SCAN"
    ACTIVE_SCAN = "ACTIVE_SCAN"
    DEAUTH_TEST = "DEAUTH_TEST"
    PMKID_CAPTURE = "PMKID_CAPTURE"
    WPA_HANDSHAKE = "WPA_HANDSHAKE"

class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"

@dataclass
class Edge:
    source: State
    action: Action
    target: State
    weight: float = 1.0
    outcomes: Dict[Outcome, int] = None

    def __post_init__(self):
        if self.outcomes is None:
            self.outcomes = {Outcome.SUCCESS: 0, Outcome.FAILURE: 0, Outcome.PARTIAL: 0}

@dataclass
class Graph:
    nodes: List[State]
    edges: List[Edge]
