from typing import Any
from james.tools.constants import START_NODE, HALT_SIGNAL
from .graph import DecisionGraph
from .engine import DecisionEngine, LearningEngine

class SelfEvolvingAgent:
    def __init__(self, graph: DecisionGraph):
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()

        self.current_node = START_NODE
        self.current_path = [START_NODE]

    def step(self, success_signal: Any | None = None) -> str:
        next_node = self.decision_engine.decide(self.current_node)

        if not next_node:
            return HALT_SIGNAL

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, success: bool):
        self.learner.update(self.graph, self.current_path, success)

        # reset episode
        self.current_node = START_NODE
        self.current_path = [START_NODE]
