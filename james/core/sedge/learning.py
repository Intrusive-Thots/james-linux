from james.core.sedge.models import DecisionGraph


class LearningEngine:
    """Updates the experience weights of edges in the decision graph."""

    def update(self, graph: DecisionGraph, path: list[str], success: bool):
        """Updates the weights of the edges traversed in the path."""
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
