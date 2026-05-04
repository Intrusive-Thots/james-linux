from james.core.sedge.graph import DecisionGraph
from james.core.sedge.decision import DecisionEngine
from james.core.sedge.learning import LearningEngine


class SelfEvolvingAgent:
    """Self-evolution loop orchestrator."""

    def __init__(self, graph: DecisionGraph):
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()
        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, success_signal: bool | None = None) -> str:
        """Executes one step in the decision loop."""
        next_node = self.decision_engine.decide(self.current_node)
        if not next_node:
            return "halt"
        self.current_path.append(next_node)
        self.current_node = next_node
        return next_node

    def feedback(self, success: bool) -> None:
        """Applies feedback to the current path and resets episode."""
        self.learner.update(self.graph, self.current_path, success)
        self.current_node = "START"
        self.current_path = ["START"]
