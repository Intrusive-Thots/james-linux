import sys
from james.core.sedge import Node, Edge, DecisionGraph, SelfEvolvingAgent

def test_sedge():
    graph = DecisionGraph()

    # Create nodes corresponding to the Parrot WiFi domain
    start_node = Node(id="START", state_type="state")
    network_discovery_node = Node(id="NETWORK_DISCOVERY", state_type="state")
    target_analysis_node = Node(id="TARGET_ANALYSIS", state_type="state")
    passive_scan_node = Node(id="PASSIVE_SCAN", state_type="action")
    deauth_test_node = Node(id="DEAUTH_TEST", state_type="action")

    graph.add_node(start_node)
    graph.add_node(network_discovery_node)
    graph.add_node(target_analysis_node)
    graph.add_node(passive_scan_node)
    graph.add_node(deauth_test_node)

    # Add some edges
    graph.add_edge(Edge(from_node="START", to_node="NETWORK_DISCOVERY"))
    graph.add_edge(Edge(from_node="NETWORK_DISCOVERY", to_node="PASSIVE_SCAN"))
    graph.add_edge(Edge(from_node="PASSIVE_SCAN", to_node="TARGET_ANALYSIS"))
    graph.add_edge(Edge(from_node="TARGET_ANALYSIS", to_node="DEAUTH_TEST"))

    agent = SelfEvolvingAgent(graph)

    print("Initial traversal...")
    path = []
    current = agent.current_node
    while current != "halt":
        path.append(current)
        current = agent.step()

    print(f"Path taken: {path}")

    print("Providing feedback...")
    agent.feedback(success=True)

    # Check that weights have updated
    edge = [e for e in graph.edges["START"] if e.to_node == "NETWORK_DISCOVERY"][0]
    print(f"Visits to START -> NETWORK_DISCOVERY: {edge.visits}")
    print(f"Success weight: {edge.success_weight}")

    assert edge.visits == 1
    assert edge.success_weight == 2.0

if __name__ == "__main__":
    try:
        test_sedge()
        print("✅ SEDGE tests passed successfully!")
    except Exception as e:
        print(f"❌ SEDGE tests failed: {e}")
        sys.exit(1)
