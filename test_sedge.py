from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
)

def test_sedge_functionality():
    print("Testing SEDGE functionality...")
    graph = DecisionGraph()
    graph.add_node(Node("START", "scan"))
    graph.add_node(Node("NETWORK_DISCOVERY", "scan"))
    graph.add_node(Node("TARGET_ANALYSIS", "analysis"))

    graph.add_edge(Edge("START", "NETWORK_DISCOVERY"))
    graph.add_edge(Edge("NETWORK_DISCOVERY", "TARGET_ANALYSIS"))

    agent = SelfEvolvingAgent(graph)
    assert agent.current_node == "START"

    n1 = agent.step()
    assert n1 == "NETWORK_DISCOVERY"

    n2 = agent.step()
    assert n2 == "TARGET_ANALYSIS"

    agent.feedback(True)

    assert graph.edges["START"][0].visits == 1
    assert graph.edges["START"][0].success_weight == 2.0
    assert graph.edges["NETWORK_DISCOVERY"][0].visits == 1
    assert graph.edges["NETWORK_DISCOVERY"][0].success_weight == 2.0

    print("SEDGE Tests passed successfully!")

if __name__ == "__main__":
    test_sedge_functionality()
