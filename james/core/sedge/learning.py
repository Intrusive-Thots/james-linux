from .models import DecisionGraph


class LearningEngine:
    def update(
        self, graph: DecisionGraph, path: list[str], success: bool
    ) -> None:
        """
        Update the weights of the edges traversed in the path based on
        whether the execution was successful or not.
        """
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
