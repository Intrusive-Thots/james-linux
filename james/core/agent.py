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

        # Initialize SEDGE decision graph
        self.graph = DecisionGraph()

        # Add basic nodes for the workflow
        self.graph.add_node(Node("START", "state"))
        self.graph.add_node(Node("MONITOR_MODE", "action"))
        self.graph.add_node(Node("SCAN", "action"))
        self.graph.add_node(Node("STOP_MONITOR", "action"))
        self.graph.add_node(Node("halt", "state"))

        # Add basic edges defining the potential paths
        self.graph.add_edge(Edge("START", "MONITOR_MODE"))
        self.graph.add_edge(Edge("MONITOR_MODE", "SCAN"))
        self.graph.add_edge(Edge("SCAN", "STOP_MONITOR"))
        self.graph.add_edge(Edge("STOP_MONITOR", "halt"))

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

        # 1. Enable monitor mode
        print("[*] Enabling monitor mode...")
        monitor_result = self.aircrack.start_monitor_mode(interface)
        self.history.append({"action": "start_monitor", "result": monitor_result})

        if not monitor_result.get("success", False):
            logger.error(f"Failed to enable monitor mode. Error: {monitor_result.get('error', 'Unknown')}")
            print("Aborting cycle: could not start monitor mode.")
            return

        mon_interface = monitor_result.get("monitor_interface", interface)
        print(f"[*] Interface is now: {mon_interface}")

        # 2. Scan
        print("[*] Scanning for networks for 5 seconds...")
        scan_result = self.aircrack.scan_networks(mon_interface, duration=5)
        self.history.append({"action": "scan", "result": scan_result})

        print(f"[*] Scan complete. Found networks logic output: {len(scan_result.get('networks_found_raw', []))} potential matches.")

        # 3. Disable monitor mode (Cleanup)
        print("[*] Cleaning up: disabling monitor mode...")
        cleanup_result = self.aircrack.stop_monitor_mode(mon_interface)
        self.history.append({"action": "stop_monitor", "result": cleanup_result})

        print("[*] Cycle complete.")
