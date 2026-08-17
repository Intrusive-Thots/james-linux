"""JAMES Agent Brain — conversational pentesting agent (restored minimal + security fixes)."""
import os
import re
import json
import logging
import keyring
import shlex
from datetime import datetime
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from james.core.ai_engine import GeminiEngine, ActionParams, ResultStore
from james.core.orchestrator import Orchestrator
from .models import AgentAction, AgentPlan, PlanStep, AttackPlan
from .intents import INTENT_PATTERNS, _COMPILED_INTENTS

class Agent:
    """Conversational pentesting agent."""

    MAX_HISTORY = 200
    CONTEXT_FILE = Path.home() / ".james" / "context.json"
    _PERSIST_KEYS = {
        "target", "interface", "wordlist", "domain", "lhost", "lport",
        "gateway", "username", "target_url", "target_bssid", "target_ssid",
        "discovered_services", "scan_history", "victim", "monitor_interface",
        "cracked_keys", "loot_cache",
    }

    def __init__(self, orchestrator: Orchestrator = None):
        self.orch = orchestrator
        self.context: dict = self._load_context()
        self.history: list[dict] = []
        self.last_intent: str = "default"
        self.ai = GeminiEngine() if hasattr(GeminiEngine, '__call__') or True else None
        if self.ai:
            try:
                self.ai.agent_ref = self
            except Exception:
                pass
        self.attack_plan: Optional[AttackPlan] = None

    def _load_context(self) -> dict:
        try:
            if self.CONTEXT_FILE.exists():
                return json.loads(self.CONTEXT_FILE.read_text())
        except Exception:
            pass
        return {}

    def _save_context(self):
        try:
            self.CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in self.context.items() if k in self._PERSIST_KEYS}
            self.CONTEXT_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save context: %s", e)

    def _do_whois(self, m, raw) -> str:
        domain = m.group(1).strip() if m and m.group(1) else ""
        if not domain:
            return "[!] Usage: whois <domain>"
        # Security: quote to prevent injection
        cmd = f"whois {shlex.quote(domain)}"
        result = self.orch.layer.run(cmd)
        out = getattr(result, "stdout", str(result)) or ""
        return f"📋 WHOIS — {domain}\n{out}"

    def _do_dns_enum(self, m, raw) -> str:
        domain = m.group(1).strip() if m and m.group(1) else ""
        if not domain:
            return "[!] Usage: dns enum <domain>"
        cmd = f"dig {shlex.quote(domain)} ANY +noall +answer"
        result = self.orch.layer.run(cmd)
        out = getattr(result, "stdout", str(result)) or ""
        return f"DNS Enum — {domain}\n{out}"

    def _do_sniff(self, m, raw) -> str:
        iface = m.group(1).strip() if m and m.group(1) else self.context.get("interface", "any")
        cmd = f"timeout 5 tcpdump -i {shlex.quote(iface)} -c 10 -nn 2>/dev/null || true"
        result = self.orch.layer.run(cmd)
        out = getattr(result, "stdout", str(result)) or ""
        return f"Sniff on {iface}\n{out}"

    def process(self, text: str) -> str:
        """Main entry: match intent and dispatch."""
        text = (text or "").strip()
        if not text:
            return ""
        for pattern, intent in _COMPILED_INTENTS:
            m = pattern.search(text)
            if m:
                self.last_intent = intent
                handler = getattr(self, f"_do_{intent}", None)
                if handler:
                    try:
                        return handler(m, text)
                    except Exception as e:
                        return f"[!] Error in {intent}: {e}"
                return f"[!] Intent {intent} recognized but no handler yet. Raw: {text}"
        return f"[?] Unknown command. Try 'help' or a known intent. Got: {text}"

    # Stubs for common intents to avoid AttributeError
    def _do_recon(self, m, raw): return self._do_full_scan(m, raw) if hasattr(self, '_do_full_scan') else f"Recon: {m.group(1) if m else ''}"
    def _do_full_scan(self, m, raw):
        target = m.group(1).strip() if m else ""
        self.context["target"] = target
        self._save_context()
        return f"Full scan requested for {target} (orchestrator integration pending full restore)"
    def _do_masscan(self, m, raw): return f"Masscan: {m.group(1) if m else ''}"
    def _do_quick_recon(self, m, raw): return f"Quick recon: {m.group(1) if m else ''}"
    def _do_os_detect(self, m, raw): return f"OS detect: {m.group(1) if m else ''}"
    def _do_ssl_scan(self, m, raw): return f"SSL scan: {m.group(1) if m else ''}"
    def _do_web_scan(self, m, raw): return f"Web scan: {m.group(1) if m else ''}"
    def _do_waf_detect(self, m, raw): return f"WAF detect: {m.group(1) if m else ''}"
    def _do_scan_aps(self, m, raw): return "Scanning APs..."
    def _do_oneclick_stealth_recon(self, m, raw): return f"Stealth recon: {m.group(1) if m else ''}"
    def _do_arp_discover(self, m, raw): return "ARP discover..."
    def _do_nikto_scan(self, m, raw): return f"Nikto: {m.group(1) if m else ''}"
    def _do_smb_enum(self, m, raw): return f"SMB enum: {m.group(1) if m else ''}"
    def _do_dns_lookup(self, m, raw): return self._do_dns_enum(m, raw)
    def _do_wash_scan(self, m, raw): return "Wash WPS scan..."
    def _do_wep_attack(self, m, raw): return f"WEP attack: {m.group(1) if m else ''}"
    def _do_wps_brute(self, m, raw): return f"WPS brute: {m.group(1) if m else ''}"
    def _do_wpa3_check(self, m, raw): return f"WPA3 check: {m.group(1) if m else ''}"
    def _do_wpa3_downgrade(self, m, raw): return f"WPA3 downgrade: {m.group(1) if m else ''}"
    def _do_iot_scan(self, m, raw): return f"IoT scan: {m.group(1) if m else ''}"
    def _do_ble_scan(self, m, raw): return "BLE scan..."
