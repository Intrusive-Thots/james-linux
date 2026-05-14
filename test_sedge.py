import pytest
from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
)

def test_node_and_edge_creation():
    node = Node(id="scan_1", state_type="scan", metadata={"target": "192.168.1.1"})
    assert node.id == "scan_1"
    assert node.state_type == "scan"
    assert node.metadata["target"] == "192.168.1.1"

    edge = Edge(from_node="START", to_node="scan_1")
    assert edge.from_node == "START"
    assert edge.to_node == "scan_1"
    assert edge.success_weight == 1.0
    assert edge.failure_weight == 1.0
    assert edge.visits == 0
    assert edge.score() > 0.99  # 1.0 / (1.0 + 1e-6)

def test_decision_graph_operations():
    graph = DecisionGraph()
    n1 = Node(id="START", state_type="start")
    n2 = Node(id="A", state_type="action")
    graph.add_node(n1)
    graph.add_node(n2)

    assert "START" in graph.nodes
    assert "A" in graph.nodes

    e1 = Edge(from_node="START", to_node="A", success_weight=2.0, failure_weight=1.0)
    graph.add_edge(e1)

    assert "START" in graph.edges
    assert len(graph.edges["START"]) == 1

    best_edge = graph.get_best_next("START")
    assert best_edge is not None
    assert best_edge.to_node == "A"

    assert graph.get_best_next("NON_EXISTENT") is None

def test_learning_engine_update():
    graph = DecisionGraph()
    e1 = Edge(from_node="START", to_node="A")
    e2 = Edge(from_node="A", to_node="B")
    graph.add_edge(e1)
    graph.add_edge(e2)

    learner = LearningEngine()

    # Test successful path
    path = ["START", "A", "B"]
    learner.update(graph, path, success=True)

    assert e1.visits == 1
    assert e1.success_weight == 2.0
    assert e1.failure_weight == 1.0

    assert e2.visits == 1
    assert e2.success_weight == 2.0
    assert e2.failure_weight == 1.0

    # Test failed path
    learner.update(graph, path, success=False)

    assert e1.visits == 2
    assert e1.success_weight == 2.0
    assert e1.failure_weight == 2.0

def test_decision_engine_decide():
    graph = DecisionGraph()
    e1 = Edge(from_node="START", to_node="A", success_weight=1.0, failure_weight=1.0)
    e2 = Edge(from_node="START", to_node="B", success_weight=10.0, failure_weight=1.0)
    graph.add_edge(e1)
    graph.add_edge(e2)

    engine = DecisionEngine(graph)

    # Due to stochastic nature, we cannot guarantee which is picked, but we can verify it's one of them.
    # B has much higher score, so it's more likely, but we just check valid return values.
    next_node = engine.decide("START")
    assert next_node in ["A", "B"]

    assert engine.decide("NON_EXISTENT") is None

def test_self_evolving_agent():
    graph = DecisionGraph()
    graph.add_edge(Edge(from_node="START", to_node="A"))
    graph.add_edge(Edge(from_node="A", to_node="B"))

    agent = SelfEvolvingAgent(graph)

    assert agent.current_node == "START"
    assert agent.current_path == ["START"]

    next_1 = agent.step()
    assert next_1 == "A"
    assert agent.current_node == "A"
    assert agent.current_path == ["START", "A"]

    next_2 = agent.step()
    assert next_2 == "B"
    assert agent.current_node == "B"
    assert agent.current_path == ["START", "A", "B"]

    next_3 = agent.step()
    assert next_3 == "halt"

    # Test feedback
    agent.feedback(success=True)
    assert agent.current_node == "START"
    assert agent.current_path == ["START"]

    # Verify learning happened
    e1 = graph.edges["START"][0]
    assert e1.success_weight == 2.0
    assert e1.visits == 1
