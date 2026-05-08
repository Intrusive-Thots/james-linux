from james.core.sedge.models import DecisionGraph
from james.tools.constants import WEIGHT_INCREMENT


class LearningEngine:
    def update(
        self,
        graph: DecisionGraph,
        path: list[str],
        success: bool
    ) -> None:
        for i in range(len(path) - 1):
            frm, to = path[i], path[i + 1]
            edges = graph.edges.get(frm, [])

            for e in edges:
                if e.to_node == to:
                    e.visits += 1

                    if success:
                        e.success_weight += WEIGHT_INCREMENT
                    else:
                        e.failure_weight += WEIGHT_INCREMENT
