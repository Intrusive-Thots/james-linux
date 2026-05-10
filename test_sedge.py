from james.core.sedge.models import DecisionGraph, Node, Edge
from james.core.sedge.agent import SelfEvolvingAgent


def test_sedge():
    # 1. Initialize graph
    graph = DecisionGraph()

    # 2. Add nodes
    graph.add_node(Node("START", "state"))
    graph.add_node(Node("NETWORK_DISCOVERY", "action"))
    graph.add_node(Node("TARGET_ANALYSIS", "analysis"))
    graph.add_node(Node("PASSIVE_SCAN", "action"))
    graph.add_node(Node("DEAUTH_TEST", "action"))
    graph.add_node(Node("SUCCESS", "outcome"))
    graph.add_node(Node("FAILURE", "outcome"))

    # 3. Add edges
    # START -> NETWORK_DISCOVERY
    graph.add_edge(Edge("START", "NETWORK_DISCOVERY"))

    # NETWORK_DISCOVERY -> TARGET_ANALYSIS
    graph.add_edge(Edge("NETWORK_DISCOVERY", "TARGET_ANALYSIS"))

    # TARGET_ANALYSIS -> PASSIVE_SCAN (safer)
    graph.add_edge(Edge("TARGET_ANALYSIS", "PASSIVE_SCAN"))

    # TARGET_ANALYSIS -> DEAUTH_TEST (aggressive)
    graph.add_edge(Edge("TARGET_ANALYSIS", "DEAUTH_TEST"))

    # Actions -> Outcomes
    graph.add_edge(Edge("PASSIVE_SCAN", "SUCCESS"))
    graph.add_edge(Edge("DEAUTH_TEST", "FAILURE"))

    # 4. Initialize agent
    agent = SelfEvolvingAgent(graph)

    # 5. Run simulation
    assert agent.current_node == "START"

    node1 = agent.step()
    assert node1 == "NETWORK_DISCOVERY"

    node2 = agent.step()
    assert node2 == "TARGET_ANALYSIS"

    node3 = agent.step()
    assert node3 in ("PASSIVE_SCAN", "DEAUTH_TEST")

    agent.feedback(success=True)

    # Validate weight updates
    edge_to_discovery = graph.edges["START"][0]
    assert edge_to_discovery.visits == 1
    assert edge_to_discovery.success_weight > 1.0


if __name__ == "__main__":
    test_sedge()
    print("All SEDGE tests passed!")
