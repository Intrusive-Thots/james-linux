"""
JAMES AI Engine — Gemini Function-Calling Integration.

Replaces the old raw-JSON LLM dispatch with proper Gemini tool_use.
Every JAMES action is declared as a FunctionDeclaration so Gemini can
pick the right tool with validated params. Conversational fallback
lets the LLM advise, explain, and strategize when no tool is needed.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from james.core.primers import get_primer, SYSTEM_PRIMER


# ── ActionParams: unified param object for regex + LLM dispatch ──

class ActionParams:
    """
    Drop-in replacement for regex match objects.

    Both the regex path and the LLM function-call path produce an
    ActionParams, so every ``_do_*`` handler works unchanged via
    ``m.group(1)``, ``m.lastindex``, etc.
    """

    def __init__(self, groups: Optional[dict] = None, **kwargs):
        self._groups = groups or {}
        self._kwargs = kwargs

    def group(self, n: int = 0):
        if n == 0:
            return self._kwargs.get("_raw", "")
        return self._groups.get(n)

    @property
    def lastindex(self):
        if not self._groups:
            return 0
        return max(k for k in self._groups if self._groups[k] is not None) if self._groups else 0

    @classmethod
    def from_function_call(cls, action: str, args: dict, param_map: dict):
        """
        Build an ActionParams from a Gemini function call response.

        param_map maps function-call arg names → group indices, e.g.
        {"target": 1, "count": 2}  →  m.group(1) returns args["target"]
        """
        groups = {}
        for arg_name, group_idx in param_map.items():
            val = args.get(arg_name)
            if val is not None:
                groups[group_idx] = str(val)
        return cls(groups=groups, _raw=json.dumps(args))


# ── Tool declarations for Gemini function calling ────────────────

# Each entry: (action_name, description, {param: (type, description, required)}, {param: group_index})
# The group_index maps LLM params → m.group(N) for the existing _do_* handlers.

TOOL_DECLARATIONS = [
    # Recon
    ("quick_recon",    "Run a fast nmap scan on a target IP or domain",
     {"target": ("string", "IP address, hostname, or CIDR range to scan", True)},
     {"target": 1}),
    ("full_scan",      "Run a deep nmap service + script scan",
     {"target": ("string", "IP address or hostname to scan", True)},
     {"target": 1}),
    ("masscan",        "Ultra-fast full-port scan (all 65535 ports)",
     {"target": ("string", "IP or CIDR range", True)},
     {"target": 1}),
    ("os_detect",      "OS fingerprinting via nmap",
     {"target": ("string", "Target IP", True)},
     {"target": 1}),
    ("arp_discover",   "Discover hosts on the local network via ARP",
     {"interface": ("string", "Network interface (optional)", False)},
     {"interface": 1}),
    ("scan_aps",       "Scan for nearby Wi-Fi access points",
     {"interface": ("string", "Wireless interface (optional)", False)},
     {"interface": 1}),

    # Wi-Fi
    ("list_interfaces", "List all wireless network interfaces and their modes",
     {}, {}),
    ("monitor_on",     "Enable monitor mode on a wireless interface",
     {"interface": ("string", "Wireless interface name like wlan0", False)},
     {"interface": 1}),
    ("monitor_off",    "Disable monitor mode on a wireless interface",
     {"interface": ("string", "Monitor interface name like wlan0mon", False)},
     {"interface": 1}),
    ("deauth",         "Send deauthentication frames to disconnect clients from an AP",
     {"bssid": ("string", "Target AP MAC address", True),
      "count": ("string", "Number of deauth frames to send (default 10)", False)},
     {"bssid": 1, "count": 2}),
    ("capture",        "Capture WiFi handshake packets on an interface",
     {"interface": ("string", "Monitor-mode interface", False)},
     {"interface": 1}),
    ("autopwn",        "Full autonomous WiFi audit: scan, PMKID, deauth, crack",
     {"interface": ("string", "Wireless interface (optional)", False)},
     {"interface": 1}),
    ("sniff",          "Capture and display network packets using tcpdump",
     {"interface": ("string", "Network interface to sniff on", False)},
     {"interface": 1}),

    # Wi-Fi Advanced
    ("wash_scan",      "Scan for WPS-enabled access points using wash",
     {"interface": ("string", "Monitor-mode interface", False)},
     {"interface": 1}),
    ("wep_attack",     "WEP attack chain: fake auth, ARP replay, crack",
     {"bssid": ("string", "Target AP BSSID", True),
      "interface": ("string", "Monitor interface", False)},
     {"bssid": 1, "interface": 2}),
    ("wps_brute",      "WPS PIN brute-force (Pixie Dust + full brute)",
     {"bssid": ("string", "Target AP BSSID", True),
      "channel": ("string", "AP channel number", False)},
     {"bssid": 1, "channel": 2}),
    ("wpa3_check",     "Check if target AP supports WPA3/SAE",
     {"bssid": ("string", "Target AP BSSID", True),
      "interface": ("string", "Interface", False)},
     {"bssid": 1, "interface": 2}),
    ("wpa3_downgrade", "WPA3 transition-mode downgrade attack",
     {"bssid": ("string", "Target AP BSSID", True),
      "channel": ("string", "AP channel", False)},
     {"bssid": 1, "channel": 2}),

    # OSINT & Web
    ("osint",          "OSINT harvest: emails, subdomains, IPs for a domain",
     {"domain": ("string", "Target domain", True)},
     {"domain": 1}),
    ("whois",          "WHOIS domain registration lookup",
     {"domain": ("string", "Domain to look up", True)},
     {"domain": 1}),
    ("dns_enum",       "DNS record enumeration",
     {"domain": ("string", "Domain to enumerate", True)},
     {"domain": 1}),
    ("dns_lookup",     "Quick DNS resolution",
     {"domain": ("string", "Domain to resolve", True),
      "record_type": ("string", "Record type: A, AAAA, MX, NS, ANY", False)},
     {"domain": 1, "record_type": 2}),
    ("waf_detect",     "Detect web application firewall",
     {"url": ("string", "Target URL", True)},
     {"url": 1}),
    ("ssl_scan",       "SSL/TLS security audit",
     {"target": ("string", "Host or URL to scan", True)},
     {"target": 1}),
    ("web_scan",       "Nikto web vulnerability scan",
     {"url": ("string", "Target URL", True)},
     {"url": 1}),
    ("nikto_scan",     "Nikto web vulnerability scan (alias)",
     {"target": ("string", "Target URL", True)},
     {"target": 1}),
    ("dir_brute",      "Directory brute-force with gobuster",
     {"url": ("string", "Target URL", True)},
     {"url": 1}),
    ("sqli",           "SQL injection test with sqlmap",
     {"url": ("string", "Target URL with parameters", True)},
     {"url": 1}),

    # Network Attacks
    ("mitm",           "ARP poisoning man-in-the-middle attack",
     {"victim": ("string", "Victim IP address", True),
      "gateway": ("string", "Gateway IP address", False)},
     {"victim": 1, "gateway": 2}),
    ("responder",      "LLMNR/NBT-NS hash capture with Responder",
     {"interface": ("string", "Network interface", False)},
     {"interface": 1}),
    ("brute",          "Brute-force network service credentials with Hydra",
     {"target": ("string", "Target IP or hostname", True),
      "protocol": ("string", "Protocol: ssh, ftp, http, rdp, smb", False)},
     {"target": 1, "protocol": 2}),
    ("smb_enum",       "SMB/NetBIOS enumeration",
     {"target": ("string", "Target IP", True)},
     {"target": 1}),

    # Cracking
    ("crack_wpa",      "Crack WPA handshake with multi-engine pipeline",
     {"capture_file": ("string", "Path to capture file (.cap)", True),
      "wordlist": ("string", "Path to wordlist", False)},
     {"capture_file": 1, "wordlist": 2}),
    ("crack_hash",     "Crack hash file with hashcat",
     {"hash_file": ("string", "Path to hash file", True),
      "wordlist": ("string", "Path to wordlist", False)},
     {"hash_file": 1, "wordlist": 2}),

    # IoT
    ("iot_scan",       "IoT device scan with banner grabbing",
     {"target": ("string", "Target IP or range", True)},
     {"target": 1}),
    ("ble_scan",       "Scan for Bluetooth Low Energy devices",
     {"interface": ("string", "Bluetooth interface (optional)", False)},
     {"interface": 1}),
    ("mqtt_scan",      "Probe MQTT broker for open access",
     {"target": ("string", "MQTT broker IP", True)},
     {"target": 1}),

    # Exploit
    ("reverse_shell",  "Generate reverse shell payloads for various languages",
     {"port": ("string", "Listening port (default 4444)", False)},
     {"port": 1}),
    ("msf",            "Search Metasploit for exploits",
     {"query": ("string", "Search term", False)},
     {"query": 1}),

    # One-Click Hacks
    ("oneclick_wifi_blitz",      "Multi-vector WiFi attack: PMKID + Handshake + WPS",
     {"interface": ("string", "Wireless interface", False)},
     {"interface": 1}),
    ("oneclick_network_dominate", "Full network attack chain: scan, fingerprint, brute, vulns",
     {"target": ("string", "Target IP or CIDR", True)},
     {"target": 1}),
    ("oneclick_web_pwn",          "Full web attack chain: WAF, dirs, SQLi, SSL, Nikto",
     {"url": ("string", "Target URL", True)},
     {"url": 1}),
    ("oneclick_stealth_recon",    "Passive OSINT chain: OSINT, DNS, WHOIS, scan",
     {"target": ("string", "Target domain or IP", True)},
     {"target": 1}),
    ("oneclick_evil_twin",        "Rogue AP clone with credential capture",
     {"interface": ("string", "Wireless interface", False)},
     {"interface": 1}),
    ("scan_and_attack",           "Full scan then auto-attack all discovered services",
     {"target": ("string", "Target IP or range", True)},
     {"target": 1}),

    # Pineapple
    ("pineapple_campaign", "Full WiFi Pineapple campaign: scan, portal, harvest",
     {"interface": ("string", "Wireless interface", False)},
     {"interface": 1}),
    ("evil_portal",     "Launch captive portal credential harvester",
     {"interface": ("string", "Wireless interface", False)},
     {"interface": 1}),
    ("karma_attack",    "KARMA attack — respond to all probe requests",
     {"interface": ("string", "Wireless interface", False)},
     {"interface": 1}),
    ("harvest_probes",  "Passive probe request collection",
     {"interface": ("string", "Monitor-mode interface", False)},
     {"interface": 1}),
    ("track_clients",   "Show clients connected to rogue AP",
     {}, {}),
    ("snoop_dns",       "Show DNS queries from connected clients",
     {}, {}),
    ("spoof_mac",       "Randomize or set MAC address on an interface",
     {"interface": ("string", "Interface to spoof", False),
      "mac": ("string", "Specific MAC address (optional, random if omitted)", False)},
     {"interface": 1, "mac": 2}),
    ("show_portal_creds", "Show credentials captured by evil portal",
     {}, {}),
    ("stop_pineapple",  "Stop all PineAP services (hostapd, dnsmasq, portal)",
     {}, {}),

    # System
    ("system_check",    "Check which pentesting tools are installed",
     {}, {}),
    ("help",            "Show full command reference",
     {}, {}),
    ("show_log",        "Show task execution history",
     {}, {}),
    ("report",          "Generate HTML penetration test report",
     {}, {}),
    ("show_loot",       "Show all cracked keys and captured credentials",
     {}, {}),
    ("list_skills",     "List available automation skill workflows",
     {}, {}),
    ("list_wordlists",  "List all available wordlists by category",
     {}, {}),
    ("run_skill",       "Execute an automated skill workflow",
     {"name": ("string", "Skill name to run", True)},
     {"name": 1}),
    ("set_context",     "Set a session context variable (target, interface, wordlist, etc)",
     {"key": ("string", "Variable name", True),
      "value": ("string", "Variable value", True)},
     {"key": 1, "value": 2}),
    ("install_deps",    "Auto-install missing pentesting tool dependencies",
     {}, {}),
    ("kill_james",      "Emergency stop: kill all tools, restore interfaces",
     {}, {}),
    ("clear",           "Reset session context and history",
     {}, {}),
    ("shell",           "Run a raw shell command",
     {"command": ("string", "Shell command to execute", True)},
     {"command": 1}),
    ("remote_access",   "Enable SSH and remote access services",
     {}, {}),
    ("net_guard_status", "Show network self-protection status",
     {}, {}),
    ("generate_wordlists", "Generate WiFi-optimized wordlists",
     {"ssid": ("string", "Target SSID for targeted wordlist (optional)", False)},
     {"ssid": 1}),
    ("connect_open_wifi", "Scan and connect to the strongest open WiFi network",
     {}, {}),
]

# Build the param_map lookup: action_name → {param: group_idx}
PARAM_MAP = {decl[0]: decl[3] for decl in TOOL_DECLARATIONS}


def _build_gemini_tools() -> list:
    """Build Gemini FunctionDeclaration objects from TOOL_DECLARATIONS."""
    if not HAS_GENAI:
        return []

    declarations = []
    for action, description, params, _pmap in TOOL_DECLARATIONS:
        properties = {}
        required = []
        for pname, (ptype, pdesc, preq) in params.items():
            properties[pname] = types.Schema(
                type=ptype.upper(),
                description=pdesc,
            )
            if preq:
                required.append(pname)

        schema = None
        if properties:
            schema = types.Schema(
                type="OBJECT",
                properties=properties,
                required=required if required else None,
            )

        declarations.append(types.FunctionDeclaration(
            name=action,
            description=description,
            parameters=schema,
        ))

    return [types.Tool(function_declarations=declarations)]


class GeminiEngine:
    """
    Gemini-powered AI brain for JAMES.

    Uses function calling to route user intent to the correct tool,
    and generates conversational responses when no tool is appropriate.
    """

    MAX_HISTORY = 30  # sliding window of conversation turns

    def __init__(self):
        self.client = None
        self.available = False
        self._tools = []
        self._history: list = []  # Gemini Content objects

        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                self.client = genai.Client()
                self._tools = _build_gemini_tools()
                self.available = True
                logger.info("GeminiEngine initialized with %d tool declarations",
                            sum(len(t.function_declarations) for t in self._tools))
            except Exception as e:
                logger.warning("GeminiEngine init failed: %s", e)

    def _build_system_prompt(self, context: dict) -> str:
        """Build a context-aware system prompt with the right phase primer."""
        parts = [SYSTEM_PRIMER]

        # Auto-detect phase from context and inject relevant primer
        if context.get("monitor_interface") or context.get("target_bssid"):
            parts.append(get_primer("wifi"))
        elif context.get("target_url"):
            parts.append(get_primer("web"))
        elif context.get("target"):
            parts.append(get_primer("recon"))

        # Inject live context
        ctx_lines = ["\n\nCURRENT SESSION STATE:"]
        for key in ("target", "interface", "monitor_interface", "target_bssid",
                     "target_ssid", "target_url", "domain", "wordlist",
                     "gateway", "victim", "lhost", "lport"):
            val = context.get(key)
            if val:
                ctx_lines.append(f"  {key}: {val}")

        svcs = context.get("discovered_services", {})
        if svcs:
            ctx_lines.append("  Discovered services:")
            for tgt, info in list(svcs.items())[:3]:
                svc_list = info.get("services", [])
                if svc_list:
                    ctx_lines.append(f"    {tgt}: {', '.join(svc_list)}")

        if len(ctx_lines) > 1:
            parts.append("\n".join(ctx_lines))

        parts.append(
            "\n\nINSTRUCTIONS:\n"
            "- If the user wants to perform an action, call the appropriate function.\n"
            "- If the user asks a question, wants advice, or you need clarification, "
            "respond conversationally with helpful pentesting guidance.\n"
            "- Be aggressive and thorough — always recommend the most effective attack.\n"
            "- Reference the session state when recommending next steps."
        )

        return "\n\n---\n\n".join(parts)

    def process(self, text: str, context: dict) -> Optional[dict]:
        """
        Send user text to Gemini with function calling enabled.

        Returns:
            dict with either:
              {"type": "function_call", "action": str, "params": ActionParams}
              {"type": "chat", "message": str}
            or None if the engine is unavailable / errors out.
        """
        if not self.available:
            return None

        try:
            system_prompt = self._build_system_prompt(context)

            # Build contents with conversation history
            contents = list(self._history[-self.MAX_HISTORY:])
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ))

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    tools=self._tools,
                ),
            )

            # Record in history
            self._history.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ))

            if not response.candidates:
                return None

            candidate = response.candidates[0]

            # Check for function call
            for part in candidate.content.parts:
                if part.function_call:
                    fc = part.function_call
                    action = fc.name
                    args = dict(fc.args) if fc.args else {}

                    logger.info("Gemini function call: %s(%s)", action, args)

                    # Build ActionParams from the function call
                    pmap = PARAM_MAP.get(action, {})
                    params = ActionParams.from_function_call(action, args, pmap)

                    # Record the function call in history as model turn
                    self._history.append(candidate.content)

                    return {"type": "function_call", "action": action, "params": params}

            # Text response (conversational)
            text_response = candidate.content.parts[0].text if candidate.content.parts else None
            if text_response:
                self._history.append(candidate.content)
                return {"type": "chat", "message": text_response}

            return None

        except Exception as e:
            logger.error("GeminiEngine error: %s", e)
            return None

    def chat_only(self, text: str, context: dict) -> Optional[str]:
        """
        LLM-only conversational response (no function calling).
        Used as smart fallback when regex also fails to match.
        """
        if not self.available:
            return None

        try:
            system_prompt = (
                self._build_system_prompt(context) +
                "\n\nYou are responding to a query that doesn't match any tool. "
                "Provide helpful pentesting advice, explain concepts, or suggest "
                "which JAMES command the user should try. Be concise but thorough."
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                ),
            )

            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return None

        except Exception as e:
            logger.error("GeminiEngine chat_only error: %s", e)
            return None

    def run_chain(
        self,
        goal: str,
        context: dict,
        execute_fn,
        *,
        max_steps: int = 10,
        on_step=None,
    ) -> str:
        """
        Agentic loop: AI plans and chains tools until the goal is met.

        The AI calls a tool, observes the result, then decides the next
        tool — repeating until it returns a text summary or the step
        limit is reached.

        Args:
            goal:       User's natural language objective
            context:    Current session state dict
            execute_fn: Callable(action: str, params: ActionParams) -> str
                        Runs the tool and returns its output string.
            max_steps:  Safety cap to prevent runaway loops (default 10)
            on_step:    Optional callback(step: int, action: str, summary: str)
                        for live UI updates.

        Returns:
            Final summary string from the AI.
        """
        if not self.available:
            return None

        chain_prompt = (
            self._build_system_prompt(context) +
            "\n\nMULTI-STEP MODE:\n"
            "You are executing a multi-step pentesting workflow.\n"
            "After each tool result, decide: call the next tool, or "
            "return a final text summary if the objective is complete.\n"
            "- Analyze each result before choosing the next action.\n"
            "- Stop when the goal is achieved or no further progress is possible.\n"
            "- Your final text response should summarize everything that was done and found."
        )

        # Start the conversation with the user's goal
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=goal)],
            )
        ]

        step_log = []

        try:
            for step in range(1, max_steps + 1):
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=chain_prompt,
                        temperature=0.1,
                        tools=self._tools,
                    ),
                )

                if not response.candidates:
                    break

                candidate = response.candidates[0]

                # Check for function call
                fc_part = None
                for part in candidate.content.parts:
                    if part.function_call:
                        fc_part = part
                        break

                if fc_part:
                    fc = fc_part.function_call
                    action = fc.name
                    args = dict(fc.args) if fc.args else {}

                    logger.info("Chain step %d: %s(%s)", step, action, args)

                    # Build ActionParams and execute
                    pmap = PARAM_MAP.get(action, {})
                    params = ActionParams.from_function_call(action, args, pmap)

                    if on_step:
                        on_step(step, action, f"Executing {action}...")

                    # Execute the tool
                    try:
                        result_str = execute_fn(action, params)
                    except Exception as e:
                        result_str = f"[ERROR] {action} failed: {e}"
                        logger.error("Chain step %d error: %s", step, e)

                    # Truncate very long results to avoid blowing context
                    if len(result_str) > 3000:
                        result_str = result_str[:3000] + "\n... (truncated)"

                    step_log.append({
                        "step": step,
                        "action": action,
                        "args": args,
                        "result": result_str[:500],
                    })

                    if on_step:
                        on_step(step, action, result_str[:200])

                    # Append the model's function call to conversation
                    contents.append(candidate.content)

                    # Append the function result
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=action,
                            response={"result": result_str},
                        )],
                    ))

                else:
                    # Text response — chain is complete
                    text_resp = ""
                    for part in candidate.content.parts:
                        if part.text:
                            text_resp += part.text

                    if text_resp:
                        logger.info("Chain complete after %d steps", step - 1)
                        # Record the chain in conversation history
                        self._history.append(types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=goal)],
                        ))
                        self._history.append(candidate.content)
                        return text_resp

                    break  # Empty response, bail

            # Hit step limit — ask AI for a summary of what was done
            if step_log:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text="Step limit reached. Summarize what was accomplished so far."
                    )],
                ))
                try:
                    summary_resp = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=chain_prompt,
                            temperature=0.2,
                        ),
                    )
                    if summary_resp.candidates and summary_resp.candidates[0].content.parts:
                        return summary_resp.candidates[0].content.parts[0].text
                except Exception:
                    pass

                # Fallback: manual summary
                lines = [f"⚡ Chain completed ({len(step_log)} steps):"]
                for entry in step_log:
                    lines.append(f"  Step {entry['step']}: {entry['action']} → {entry['result'][:100]}")
                return "\n".join(lines)

            return None

        except Exception as e:
            logger.error("Chain error: %s", e)
            if step_log:
                lines = [f"⚠ Chain interrupted after {len(step_log)} steps: {e}"]
                for entry in step_log:
                    lines.append(f"  Step {entry['step']}: {entry['action']}")
                return "\n".join(lines)
            return None

    def clear_history(self):
        """Reset conversation memory."""
        self._history.clear()
