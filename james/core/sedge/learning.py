from james.core.sedge.graph import DecisionGraph


class LearningEngine:
    """Execution feedback learning. Updates graph scores."""

    def update(self, graph: DecisionGraph, path: list[str],
               success: bool) -> None:
        """Updates edge weights based on the success of a path."""
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])
            for e in edges:
                if e.to_node == to:
                    e.visits += 1
                    if success:
                        e.success_weight += 1.0
                    else:
                        e.failure_weight += 1.0
