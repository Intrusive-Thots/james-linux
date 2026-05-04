import unittest

from james.core.sedge import (
    Node,
    Edge,
    DecisionGraph,
    LearningEngine,
    DecisionEngine,
    SelfEvolvingAgent)


class TestSEDGE(unittest.TestCase):

    def setUp(self):
        self.graph = DecisionGraph()
        # Add states
        self.graph.add_node(Node(id="START", state_type="start"))
        self.graph.add_node(Node(id="NETWORK_DISCOVERY", state_type="state"))
        self.graph.add_node(Node(id="TARGET_ANALYSIS", state_type="state"))
        self.graph.add_node(Node(id="SECURITY_PROFILING", state_type="state"))

        # Add actions
        self.graph.add_node(Node(id="PASSIVE_SCAN", state_type="action"))
        self.graph.add_node(Node(id="HANDSHAKE_CAPTURE", state_type="action"))
        self.graph.add_node(Node(id="DEAUTH_TEST", state_type="action"))
        self.graph.add_node(
            Node(
                id="EVIL_TWIN_SIMULATION",
                state_type="action"))

        # Build initial paths
        self.graph.add_edge(
            Edge(
                from_node="START",
                to_node="NETWORK_DISCOVERY"))
        self.graph.add_edge(
            Edge(
                from_node="NETWORK_DISCOVERY",
                to_node="PASSIVE_SCAN"))
        self.graph.add_edge(
            Edge(
                from_node="PASSIVE_SCAN",
                to_node="TARGET_ANALYSIS"))

        # Two diverging paths from TARGET_ANALYSIS
        self.graph.add_edge(
            Edge(
                from_node="TARGET_ANALYSIS",
                to_node="HANDSHAKE_CAPTURE"))
        self.graph.add_edge(
            Edge(
                from_node="TARGET_ANALYSIS",
                to_node="DEAUTH_TEST"))

    def test_graph_creation(self):
        self.assertIn("START", self.graph.nodes)
        self.assertIn("NETWORK_DISCOVERY", self.graph.nodes)

        edges_from_start = self.graph.edges.get("START", [])
        self.assertEqual(len(edges_from_start), 1)
        self.assertEqual(edges_from_start[0].to_node, "NETWORK_DISCOVERY")

    def test_learning_updates(self):
        learner = LearningEngine()

        # Simulate a successful path
        path1 = [
            "START",
            "NETWORK_DISCOVERY",
            "PASSIVE_SCAN",
            "TARGET_ANALYSIS",
            "HANDSHAKE_CAPTURE"]
        learner.update(self.graph, path1, success=True)

        # Simulate a failed path
        path2 = [
            "START",
            "NETWORK_DISCOVERY",
            "PASSIVE_SCAN",
            "TARGET_ANALYSIS",
            "DEAUTH_TEST"]
        learner.update(self.graph, path2, success=False)

        # Verify edge weights
        edges_from_analysis = self.graph.edges.get("TARGET_ANALYSIS", [])
        for e in edges_from_analysis:
            if e.to_node == "HANDSHAKE_CAPTURE":
                self.assertEqual(e.visits, 1)
                self.assertEqual(e.success_weight, 2.0)
                self.assertEqual(e.failure_weight, 1.0)
            elif e.to_node == "DEAUTH_TEST":
                self.assertEqual(e.visits, 1)
                self.assertEqual(e.success_weight, 1.0)
                self.assertEqual(e.failure_weight, 2.0)

    def test_decision_stochastic_making(self):
        # We'll use learning to heavily weight one path to test stochastic
        # nature reliably
        learner = LearningEngine()
        path1 = [
            "START",
            "NETWORK_DISCOVERY",
            "PASSIVE_SCAN",
            "TARGET_ANALYSIS",
            "HANDSHAKE_CAPTURE"]
        for _ in range(100):
            learner.update(self.graph, path1, success=True)

        decision_engine = DecisionEngine(self.graph)

        # Ensure it strongly prefers HANDSHAKE_CAPTURE, but DEAUTH_TEST is
        # still possible
        choices = []
        for _ in range(1000):
            choices.append(decision_engine.decide("TARGET_ANALYSIS"))

        handshake_count = choices.count("HANDSHAKE_CAPTURE")
        deauth_count = choices.count("DEAUTH_TEST")

        self.assertTrue(handshake_count > deauth_count * 10)
        self.assertTrue(deauth_count > 0)  # Exploration should still happen

    def test_agent_end_to_end(self):
        agent = SelfEvolvingAgent(self.graph)

        self.assertEqual(agent.current_node, "START")

        next_node = agent.step()
        self.assertEqual(next_node, "NETWORK_DISCOVERY")

        next_node = agent.step()
        self.assertEqual(next_node, "PASSIVE_SCAN")

        next_node = agent.step()
        self.assertEqual(next_node, "TARGET_ANALYSIS")

        next_node = agent.step()
        self.assertIn(next_node, ["HANDSHAKE_CAPTURE", "DEAUTH_TEST"])

        next_node = agent.step()
        self.assertEqual(next_node, "halt")  # No outgoing edges

        agent.feedback(success=True)
        self.assertEqual(agent.current_node, "START")
        self.assertEqual(agent.current_path, ["START"])


if __name__ == '__main__':
    unittest.main()
