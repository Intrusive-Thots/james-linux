
from james.core.sedge.models import Node, Edge
from james.core.sedge.graph import DecisionGraph
from james.core.sedge.decision import DecisionEngine
from james.core.sedge.learning import LearningEngine
from james.core.sedge.agent import SelfEvolvingAgent


def test_graph_initialization():
    graph = DecisionGraph()
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0

    node_start = Node(id="START", state_type="state")
    node_scan = Node(id="SCAN", state_type="action")
    graph.add_node(node_start)
    graph.add_node(node_scan)

    edge_1 = Edge(from_node="START", to_node="SCAN")
    graph.add_edge(edge_1)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert "START" in graph.edges
    assert len(graph.edges["START"]) == 1

    best_next = graph.get_best_next("START")
    assert best_next is not None
    assert best_next.to_node == "SCAN"

    assert graph.get_best_next("NON_EXISTENT") is None


def test_weight_update_on_success():
    graph = DecisionGraph()
    edge_1 = Edge(from_node="START", to_node="SCAN")
    graph.add_edge(edge_1)

    learner = LearningEngine()
    path = ["START", "SCAN"]

    assert edge_1.visits == 0
    assert edge_1.success_weight == 1.0

    learner.update(graph, path, success=True)

    assert edge_1.visits == 1
    assert edge_1.success_weight == 2.0
    assert edge_1.failure_weight == 1.0


def test_weight_update_on_failure():
    graph = DecisionGraph()
    edge_1 = Edge(from_node="START", to_node="SCAN")
    graph.add_edge(edge_1)

    learner = LearningEngine()
    path = ["START", "SCAN"]

    assert edge_1.visits == 0
    assert edge_1.failure_weight == 1.0

    learner.update(graph, path, success=False)

    assert edge_1.visits == 1
    assert edge_1.success_weight == 1.0
    assert edge_1.failure_weight == 2.0


def test_decision_engine_selection():
    graph = DecisionGraph()
    # Edge to SCAN has higher score
    edge_scan = Edge(
        from_node="START",
        to_node="SCAN",
        success_weight=10.0,
        failure_weight=1.0
    )
    # Edge to IDLE has lower score
    edge_idle = Edge(
        from_node="START",
        to_node="IDLE",
        success_weight=1.0,
        failure_weight=10.0
    )

    graph.add_edge(edge_scan)
    graph.add_edge(edge_idle)

    engine = DecisionEngine(graph)

    # Over 1000 trials, SCAN should be chosen more often
    scan_count = 0
    idle_count = 0
    for _ in range(1000):
        choice = engine.decide("START")
        if choice == "SCAN":
            scan_count += 1
        elif choice == "IDLE":
            idle_count += 1

    assert scan_count > idle_count
    assert engine.decide("NON_EXISTENT") is None


def test_agent_step():
    graph = DecisionGraph()
    edge_1 = Edge(from_node="START", to_node="SCAN")
    graph.add_edge(edge_1)

    agent = SelfEvolvingAgent(graph)

    assert agent.current_node == "START"
    assert agent.current_path == ["START"]

    next_node = agent.step()

    assert next_node == "SCAN"
    assert agent.current_node == "SCAN"
    assert agent.current_path == ["START", "SCAN"]

    # Next step from SCAN should halt as there are no outgoing edges
    halt_node = agent.step()
    assert halt_node == "halt"


def test_agent_feedback():
    graph = DecisionGraph()
    edge_1 = Edge(from_node="START", to_node="SCAN")
    graph.add_edge(edge_1)

    agent = SelfEvolvingAgent(graph)
    agent.step()  # Moves to SCAN

    assert agent.current_path == ["START", "SCAN"]

    agent.feedback(success=True)

    # Verify learning happened
    assert edge_1.visits == 1
    assert edge_1.success_weight == 2.0

    # Verify state reset
    assert agent.current_node == "START"
    assert agent.current_path == ["START"]
