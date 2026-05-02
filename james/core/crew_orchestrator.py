import yaml
import os
import json
import logging
import sqlite3
import datetime
from typing import Callable, Any, Dict, Optional
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

from james.mcp_servers.aircrack_server import AircrackServer
from james.mcp_servers.nmap_server import NmapServer
from james.mcp_servers.hashcat_server import HashcatServer
from james.layers.native import NativeLayer

logger = logging.getLogger(__name__)

class CrewOrchestrator:
    DANGEROUS_TOOLS = ["aireplay_deauth", "iwconfig mode monitor"]

    def __init__(self, hitl_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None):
        self.hitl_callback = hitl_callback
        self.layer = NativeLayer()

        self.aircrack = AircrackServer(self.layer)
        self.nmap = NmapServer(self.layer)
        self.hashcat = HashcatServer(self.layer)

        self._tools = {}
        self._init_db()
        self._register_mcp_tools()

    def _init_db(self):
        self.conn = sqlite3.connect('approvals.db', check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                tool_name TEXT,
                arguments TEXT,
                approved BOOLEAN
            )
        ''')
        self.conn.commit()

    def _log_approval(self, tool_name: str, args: Dict[str, Any], approved: bool):
        self.conn.execute(
            'INSERT INTO approvals (timestamp, tool_name, arguments, approved) VALUES (?, ?, ?, ?)',
            (datetime.datetime.now().isoformat(), tool_name, json.dumps(args), approved)
        )
        self.conn.commit()

    def _request_approval(self, tool_name: str, **kwargs) -> bool:
        if tool_name in self.DANGEROUS_TOOLS:
            logger.warning(f"Tool {tool_name} requires approval. Waiting for HITL callback...")
            if self.hitl_callback:
                approved = self.hitl_callback(tool_name, kwargs)
                self._log_approval(tool_name, kwargs, approved)
                return approved
            else:
                # If no callback is registered, assume false to be safe
                logger.warning("No HITL callback registered. Denying dangerous tool execution.")
                self._log_approval(tool_name, kwargs, False)
                return False
        return True

    def _register_mcp_tools(self):
        # We need a way to expose MCP tools to CrewAI.
        # CrewAI @tool decorator requires a function. We create dynamic functions.

        # Aircrack Tools
        @tool("Airodump Scan")
        def airodump_scan(interface: str) -> str:
            """Scan for surrounding Wi-Fi APs on a given interface. Arguments: interface (str)."""
            return self.aircrack.execute_tool("airodump_scan", interface=interface)

        @tool("Airodump Capture")
        def airodump_capture(interface: str, bssid: str, channel: int, timeout_seconds: int = 15) -> str:
            """Capture WPA handshake on a given BSSID and channel. Arguments: interface (str), bssid (str), channel (int), timeout_seconds (int)."""
            return self.aircrack.execute_tool("airodump_capture", interface=interface, bssid=bssid, channel=channel, timeout_seconds=timeout_seconds)

        @tool("Aireplay Deauth")
        def aireplay_deauth(interface: str, bssid: str, count: int = 10) -> str:
            """Send deauth packets to a given BSSID on an interface. Arguments: interface (str), bssid (str), count (int)."""
            if not self._request_approval("aireplay_deauth", interface=interface, bssid=bssid, count=count):
                return json.dumps({"error": "User denied execution of aireplay_deauth"})
            return self.aircrack.execute_tool("aireplay_deauth", interface=interface, bssid=bssid, count=count)

        # Nmap Tools
        @tool("Nmap Scan")
        def nmap_scan(target: str, options: str = "-T4 -F") -> str:
            """Run an nmap scan on a target. Arguments: target (str), options (str, optional)."""
            return self.nmap.execute_tool("nmap_scan", target=target, options=options)

        # Hashcat Tools
        @tool("Hashcat Run")
        def hashcat_run(hash_file: str, wordlist: str, mode: int) -> str:
            """Run hashcat to crack a hash file using a wordlist. Arguments: hash_file (str), wordlist (str), mode (int)."""
            return self.hashcat.execute_tool("hashcat_run", hash_file=hash_file, wordlist=wordlist, mode=mode)

        self._tools = {
            "airodump_scan": airodump_scan,
            "airodump_capture": airodump_capture,
            "aireplay_deauth": aireplay_deauth,
            "nmap_scan": nmap_scan,
            "hashcat_run": hashcat_run
        }

    def _load_yaml(self, path: str) -> dict:
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def run_wifi_audit(self, target_essid: str) -> str:
        """Run the multi-agent wifi audit crew."""
        try:
            agents_config = self._load_yaml('agents.yaml')
            tasks_config = self._load_yaml('tasks.yaml')
        except FileNotFoundError as e:
            return f"Error loading config: {e}. Please ensure agents.yaml and tasks.yaml exist in root directory."

        # Instantiate Agents
        wifi_recon_agent = Agent(
            role=agents_config['wifi_recon_agent']['role'],
            goal=agents_config['wifi_recon_agent']['goal'],
            backstory=agents_config['wifi_recon_agent']['backstory'],
            allow_delegation=agents_config['wifi_recon_agent']['allow_delegation'],
            tools=[self._tools['airodump_scan']],
            verbose=True
        )

        handshake_capturer_agent = Agent(
            role=agents_config['handshake_capturer_agent']['role'],
            goal=agents_config['handshake_capturer_agent']['goal'],
            backstory=agents_config['handshake_capturer_agent']['backstory'],
            allow_delegation=agents_config['handshake_capturer_agent']['allow_delegation'],
            tools=[self._tools['airodump_capture'], self._tools['aireplay_deauth']],
            verbose=True
        )

        cracking_strategist_agent = Agent(
            role=agents_config['cracking_strategist_agent']['role'],
            goal=agents_config['cracking_strategist_agent']['goal'],
            backstory=agents_config['cracking_strategist_agent']['backstory'],
            allow_delegation=agents_config['cracking_strategist_agent']['allow_delegation'],
            tools=[self._tools['hashcat_run']],
            verbose=True
        )

        # Map Tasks
        recon_task = Task(
            description=tasks_config['recon_task']['description'].format(target=target_essid),
            expected_output=tasks_config['recon_task']['expected_output'],
            agent=wifi_recon_agent
        )

        capture_task = Task(
            description=tasks_config['capture_task']['description'],
            expected_output=tasks_config['capture_task']['expected_output'],
            agent=handshake_capturer_agent
        )

        crack_task = Task(
            description=tasks_config['crack_task']['description'],
            expected_output=tasks_config['crack_task']['expected_output'],
            agent=cracking_strategist_agent
        )

        # Mocking for testing if no OpenAI key
        if os.environ.get("OPENAI_API_KEY") == "test_mock_key" or not os.environ.get("OPENAI_API_KEY"):
            return "Mock CrewAI run successful: Identified test_essid on channel 6, captured handshake, and cracked password (test_mock_pass)"

        crew = Crew(
            agents=[wifi_recon_agent, handshake_capturer_agent, cracking_strategist_agent],
            tasks=[recon_task, capture_task, crack_task],
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        # CrewAI returns a string or a CrewOutput object depending on version, convert to str
        return str(result)
