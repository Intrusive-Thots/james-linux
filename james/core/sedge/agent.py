from james.core.sedge.models import DecisionGraph
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.learning import LearningEngine


class SelfEvolvingAgent:
    """An agent that uses the decision graph to evolve its behavior over
    time."""

    def __init__(self, graph: DecisionGraph):
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()

        self.current_node = "START"
        self.current_path = ["START"]

    def step(self, success_signal: bool | None = None) -> str:
        """Takes a single step in the environment."""
        next_node = self.decision_engine.decide(self.current_node)

        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, success: bool):
        """Provides feedback to the agent to learn from."""
        self.learner.update(self.graph, self.current_path, success)

        # Reset episode
        self.current_node = "START"
        self.current_path = ["START"]
