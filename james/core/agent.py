import logging
from typing import Dict, Any, List
from james.layers.native import NativeLayer
from james.tools.parrot import AircrackSuite
from james.core.sedge import Node, Edge, DecisionGraph, SelfEvolvingAgent

logger = logging.getLogger(__name__)

class PentestAgent:
    """
    The main reasoning and orchestration loop for the AI agent.
    Responsible for getting user consent, deciding next actions, and interpreting results.
    """
    def __init__(self, target_scope: str):
        self.target_scope = target_scope
        self.layer = NativeLayer()
        self.aircrack = AircrackSuite(self.layer)
        self.history: List[Dict[str, Any]] = []
        self.authorized = False

        # Initialize SEDGE Decision Graph
        self.graph = DecisionGraph()

        # Add Nodes
        self.graph.add_node(Node(id="START", state_type="state"))
        self.graph.add_node(Node(id="NETWORK_DISCOVERY", state_type="state"))
        self.graph.add_node(Node(id="PASSIVE_SCAN", state_type="action"))
        self.graph.add_node(Node(id="AGGRESSIVE_SCAN", state_type="action"))
        self.graph.add_node(Node(id="SUCCESS", state_type="terminal"))
        self.graph.add_node(Node(id="FAILURE", state_type="terminal"))

        # Add Edges
        self.graph.add_edge(Edge(from_node="START", to_node="NETWORK_DISCOVERY"))
        self.graph.add_edge(Edge(from_node="NETWORK_DISCOVERY", to_node="PASSIVE_SCAN"))
        self.graph.add_edge(Edge(from_node="NETWORK_DISCOVERY", to_node="AGGRESSIVE_SCAN"))

        self.sedge_agent = SelfEvolvingAgent(self.graph)

    def request_authorization(self) -> bool:
        """Prompts the user to confirm authorization for the target scope."""
        print(f"\n[!] WARNING: You are about to initiate operations against: {self.target_scope}")
        print("Ensure you have explicit, legal permission to test this target.")
        consent = input("Do you have authorization and consent to proceed? (yes/no): ")
        if consent.lower() in ["y", "yes"]:
            self.authorized = True
            logger.info("User granted authorization.")
            return True
        logger.warning("User denied authorization. Aborting.")
        return False

    def run_cycle(self, interface: str):
        """Runs a basic execution loop: monitor mode -> scan -> stop monitor mode."""
        if not self.authorized:
            if not self.request_authorization():
                print("Exiting due to lack of authorization.")
                return

        print(f"[*] Starting cycle on interface: {interface}")

        while True:
            action = self.sedge_agent.step()

            if not action or action == "halt" or action in ["SUCCESS", "FAILURE"]:
                print(f"[*] Cycle complete. Reached path end without terminal success logic.")
                break

            if action == "NETWORK_DISCOVERY":
                print("[*] Network discovery phase started...")
                continue

            if action in ["PASSIVE_SCAN", "AGGRESSIVE_SCAN"]:
                scan_duration = 5 if action == "PASSIVE_SCAN" else 15

                # 1. Enable monitor mode
                print(f"[*] Enabling monitor mode for {action}...")
                monitor_result = self.aircrack.start_monitor_mode(interface)
                self.history.append({"action": "start_monitor", "result": monitor_result})

                if not monitor_result.get("success", False):
                    logger.error(f"Failed to enable monitor mode. Error: {monitor_result.get('error', 'Unknown')}")
                    print("Aborting cycle: could not start monitor mode.")
                    self.sedge_agent.feedback(False)
                    break

                mon_interface = monitor_result.get("monitor_interface", interface)
                print(f"[*] Interface is now: {mon_interface}")

                # 2. Scan
                print(f"[*] Scanning for networks for {scan_duration} seconds...")
                scan_result = self.aircrack.scan_networks(mon_interface, duration=scan_duration)
                self.history.append({"action": "scan", "result": scan_result})

                num_networks = len(scan_result.get('networks_found_raw', []))
                print(f"[*] Scan complete. Found networks logic output: {num_networks} potential matches.")

                # 3. Disable monitor mode (Cleanup)
                print("[*] Cleaning up: disabling monitor mode...")
                cleanup_result = self.aircrack.stop_monitor_mode(mon_interface)
                self.history.append({"action": "stop_monitor", "result": cleanup_result})

                # Feedback based on REAL environment outcome
                scan_success = scan_result.get('success', False) and num_networks > 0
                if scan_success:
                    print("[+] Action was successful!")
                    self.sedge_agent.feedback(True)
                else:
                    print("[-] Action failed to find networks.")
                    self.sedge_agent.feedback(False)
                break
