import unittest
import math

from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent,
    build_parrot_wifi_graph,
)
from james.tools.constants import (
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL,
    STATE_START,
    STATE_NETWORK_DISCOVERY,
    STATE_TARGET_ANALYSIS,
    STATE_SECURITY_PROFILING,
    ACTION_PASSIVE_SCAN,
    ACTION_HANDSHAKE_CAPTURE,
    ACTION_DEAUTH_TEST,
    ACTION_EVIL_TWIN_SIMULATION,
)


class TestSEDGECoreIdeaSystem(unittest.TestCase):
    """
    Comprehensive test suite proving the SEDGE Core Idea functionality:
    - Nodes = system states or actions
    - Edges = transitions between decisions
    - Weights = learned success utility scores
    Over time: successful paths become stronger, failed paths decay,
    and optimal strategies emerge automatically.
    """

    def setUp(self):
        """Initializes a fresh graph and components for each test."""
        self.graph = DecisionGraph()

    def test_node_model(self):
        """Test the Node model representation of a system state/action."""
        node = Node(id="test_node", state_type="scan", metadata={"key": "val"})
        self.assertEqual(node.id, "test_node")
        self.assertEqual(node.state_type, "scan")
        self.assertEqual(node.metadata, {"key": "val"})

    def test_edge_model_and_score(self):
        """Test the Edge model and the utility score calculation."""
        edge = Edge(from_node="A", to_node="B")
        self.assertEqual(edge.from_node, "A")
        self.assertEqual(edge.to_node, "B")
        self.assertEqual(edge.success_weight, 1.0)
        self.assertEqual(edge.failure_weight, 1.0)

        # Initial score: 1.0 / (1.0 + 1e-6) ~= 1.0
        self.assertAlmostEqual(edge.score(), 1.0, places=5)

        # Success updates
        edge.success_weight += 1.0
        # Score: 2.0 / (1.0 + 1e-6) ~= 2.0
        self.assertAlmostEqual(edge.score(), 2.0, places=5)

        # Failure updates
        edge.failure_weight += 3.0
        # Score: 2.0 / (4.0 + 1e-6) ~= 0.5
        self.assertAlmostEqual(edge.score(), 0.5, places=5)

    def test_decision_graph_core(self):
        """Test the core DecisionGraph functionality."""
        node_a = Node(id="A", state_type="state")
        node_b = Node(id="B", state_type="state")

        self.graph.add_node(node_a)
        self.graph.add_node(node_b)

        edge_ab = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge_ab)

        self.assertEqual(self.graph.get_node("A"), node_a)
        self.assertEqual(self.graph.get_edges("A"), [edge_ab])

        best_next = self.graph.get_best_next("A")
        self.assertEqual(best_next, edge_ab)

        # Test path scoring
        score = self.graph.get_path_score(["A", "B"])
        self.assertAlmostEqual(score, 1.0, places=5)

    def test_learning_engine_feedback(self):
        """Test that execution feedback adjusts edge weights."""
        self.graph.add_node(Node(id="A", state_type="state"))
        self.graph.add_node(Node(id="B", state_type="state"))
        edge = Edge(from_node="A", to_node="B")
        self.graph.add_edge(edge)

        learner = LearningEngine()

        # Successful feedback
        learner.update(self.graph, ["A", "B"], OUTCOME_SUCCESS)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 1.0)
        self.assertEqual(edge.visits, 1)

        # Failed feedback
        learner.update(self.graph, ["A", "B"], OUTCOME_FAILURE)
        self.assertEqual(edge.success_weight, 2.0)
        self.assertEqual(edge.failure_weight, 2.0)
        self.assertEqual(edge.visits, 2)

        # Partial feedback
        learner.update(self.graph, ["A", "B"], OUTCOME_PARTIAL)
        self.assertEqual(edge.success_weight, 2.5)
        self.assertEqual(edge.failure_weight, 2.5)
        self.assertEqual(edge.visits, 3)

    def test_decision_engine_policy(self):
        """Test stochastic weighted selection for decision making."""
        self.graph.add_node(Node(id="A", state_type="state"))
        self.graph.add_node(Node(id="B", state_type="state"))
        self.graph.add_node(Node(id="C", state_type="state"))

        edge_ab = Edge(from_node="A", to_node="B")
        edge_ac = Edge(from_node="A", to_node="C")
        self.graph.add_edge(edge_ab)
        self.graph.add_edge(edge_ac)

        # Manipulate weights to make C strictly dominant
        edge_ab.success_weight = 1.0
        edge_ab.failure_weight = 100.0 # Score ~ 0.01

        edge_ac.success_weight = 100.0
        edge_ac.failure_weight = 1.0   # Score ~ 100.0

        engine = DecisionEngine(self.graph)

        # Due to stochastic weighted selection, C should be chosen most times
        choices = {"B": 0, "C": 0}
        for _ in range(1000):
            choices[engine.decide("A")] += 1

        self.assertTrue(choices["C"] > 900)
        self.assertTrue(choices["B"] < 100)

    def test_self_evolving_agent_loop(self):
        """Test the self-evolution loop: step and feedback."""
        self.graph.add_node(Node(id=STATE_START, state_type="state"))
        self.graph.add_node(Node(id="TARGET", state_type="state"))
        self.graph.add_edge(Edge(from_node=STATE_START, to_node="TARGET"))

        agent = SelfEvolvingAgent(self.graph)

        # Step through graph
        next_node = agent.step()
        self.assertEqual(next_node, "TARGET")
        self.assertEqual(agent.current_path, [STATE_START, "TARGET"])

        # Provide feedback
        agent.feedback(OUTCOME_SUCCESS)

        # Agent should reset
        self.assertEqual(agent.current_node, STATE_START)
        self.assertEqual(agent.current_path, [STATE_START])

        # Edge weight should be updated
        edge = self.graph.get_edges(STATE_START)[0]
        self.assertEqual(edge.success_weight, 2.0)

    def test_parrot_wifi_system_mapping(self):
        """Test the domain mapping for the Parrot WiFi SEDGE graph."""
        graph = build_parrot_wifi_graph()

        # Verify specific nodes exist
        self.assertIsNotNone(graph.get_node(STATE_NETWORK_DISCOVERY))
        self.assertIsNotNone(graph.get_node(ACTION_HANDSHAKE_CAPTURE))
        self.assertIsNotNone(graph.get_node(ACTION_EVIL_TWIN_SIMULATION))

        # Verify sequence edges exist
        discovery_edges = graph.get_edges(STATE_NETWORK_DISCOVERY)
        self.assertTrue(any(e.to_node == ACTION_PASSIVE_SCAN for e in discovery_edges))

        analysis_edges = graph.get_edges(STATE_TARGET_ANALYSIS)
        self.assertTrue(any(e.to_node == ACTION_HANDSHAKE_CAPTURE for e in analysis_edges))
        self.assertTrue(any(e.to_node == ACTION_DEAUTH_TEST for e in analysis_edges))

    def test_evolution_convergence_over_time(self):
        """Test that the graph naturally converges toward optimal paths."""
        graph = build_parrot_wifi_graph()
        agent = SelfEvolvingAgent(graph)

        # We simulate multiple runs where:
        # Handshake capture succeeds
        # Deauth test fails

        for _ in range(500):
            node = agent.step()
            while node != "halt":
                if node == ACTION_HANDSHAKE_CAPTURE:
                    agent.feedback(OUTCOME_SUCCESS)
                    break
                elif node == ACTION_DEAUTH_TEST:
                    agent.feedback(OUTCOME_FAILURE)
                    break
                node = agent.step()

        # Now verify probabilities
        analysis_edges = graph.get_edges(STATE_TARGET_ANALYSIS)
        handshake_edge = next(e for e in analysis_edges if e.to_node == ACTION_HANDSHAKE_CAPTURE)
        deauth_edge = next(e for e in analysis_edges if e.to_node == ACTION_DEAUTH_TEST)

        # Handshake should have a much higher score than Deauth
        self.assertTrue(handshake_edge.score() > deauth_edge.score())

        # Decision Engine should heavily favor the successful path
        engine = DecisionEngine(graph)
        choices = {ACTION_HANDSHAKE_CAPTURE: 0, ACTION_DEAUTH_TEST: 0}

        for _ in range(1000):
            choices[engine.decide(STATE_TARGET_ANALYSIS)] += 1

        self.assertTrue(choices[ACTION_HANDSHAKE_CAPTURE] > choices[ACTION_DEAUTH_TEST])


if __name__ == "__main__":
    unittest.main()
