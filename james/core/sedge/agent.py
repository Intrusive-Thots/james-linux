from james.core.sedge.models import DecisionGraph
from james.core.sedge.policy import DecisionEngine
from james.core.sedge.learning import LearningEngine


class SelfEvolvingAgent:
    """Manages the self-evolution loop for path selection and learning."""

    def __init__(self, graph: DecisionGraph) -> None:
        self.graph = graph
        self.decision_engine = DecisionEngine(graph)
        self.learner = LearningEngine()

        self.current_node = "START"
        self.current_path = ["START"]

    def step(self) -> str:
        """Advance one step in the decision graph."""
        next_node = self.decision_engine.decide(self.current_node)

        if not next_node:
            return "halt"

        self.current_path.append(next_node)
        self.current_node = next_node

        return next_node

    def feedback(self, success: bool) -> None:
        """Process feedback to update the graph and reset the episode."""
        self.learner.update(self.graph, self.current_path, success)

        # reset episode
        self.current_node = "START"
        self.current_path = ["START"]
