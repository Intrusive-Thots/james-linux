#!/usr/bin/env python3
"""
JAMES Intent Pattern Test Suite

Automated tests for all intent patterns to catch ordering bugs
and regressions. Run after any change to INTENT_PATTERNS.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from james.core.agent import Agent, INTENT_PATTERNS
from james.core.orchestrator import Orchestrator


def test_intent_routing():
    """Test that specific inputs route to the correct intents."""
    agent = Agent(Orchestrator())

    # (input, expected_intent)
    CASES = [
        # ── Recon ──────────────────────────────────────────────
        ("scan 192.168.1.1",              "recon"),
        ("recon 10.0.0.0/24",             "recon"),
        ("enumerate target.com",          "recon"),
        ("discover 10.0.0.1",             "recon"),
        ("port scan 10.0.0.1",            "recon"),
        ("quick scan 10.0.0.1",           "quick_recon"),
        ("fast scan target.com",          "quick_recon"),
        ("full scan 10.0.0.1",            "full_scan"),
        ("deep scan target.com",          "full_scan"),
        ("os detect 10.0.0.1",            "os_detect"),
        ("fingerprint 10.0.0.1",          "os_detect"),
        ("masscan 10.0.0.0/24",           "masscan"),
        ("mass scan 10.0.0.0/24",         "masscan"),

        # ── Stealth recon MUST win over generic recon ──────────
        ("stealth recon google.com",      "oneclick_stealth_recon"),
        ("passive recon target.com",      "oneclick_stealth_recon"),
        ("silent recon 10.0.0.1",         "oneclick_stealth_recon"),

        # ── Wi-Fi ──────────────────────────────────────────────
        ("list interfaces",               "list_interfaces"),
        ("show wifi",                     "list_interfaces"),
        ("show wireless",                 "list_interfaces"),
        ("enable monitor wlan0",          "monitor_on"),
        ("start monitor mode on wlan0",   "monitor_on"),
        ("disable monitor wlan0",         "monitor_off"),
        ("deauth AA:BB:CC:DD:EE:FF",      "deauth"),
        ("deauthenticate AA:BB:CC:DD:EE:FF 10", "deauth"),
        ("scan aps",                      "scan_aps"),
        ("scan aps wlan0",                "scan_aps"),
        ("nearby aps",                    "scan_aps"),
        ("nearby networks",               "scan_aps"),

        # ── Open Wi-Fi ─────────────────────────────────────────
        ("I need wifi",                   "connect_open_wifi"),
        ("need wifi",                     "connect_open_wifi"),
        ("need internet",                 "connect_open_wifi"),
        ("want wifi",                     "connect_open_wifi"),
        ("get wifi",                      "connect_open_wifi"),
        ("find wifi",                     "connect_open_wifi"),
        ("connect to wifi",              "connect_open_wifi"),
        ("connect to open wifi",          "connect_open_wifi"),
        ("find open network",             "connect_open_wifi"),
        ("join wifi",                     "connect_open_wifi"),
        ("grab wifi",                     "connect_open_wifi"),
        ("gimme internet",                "connect_open_wifi"),
        ("get free wifi",                 "connect_open_wifi"),
        ("find a hotspot",                "connect_open_wifi"),
        ("connect wireless",              "connect_open_wifi"),

        # ── One-Click Hacks ────────────────────────────────────
        ("wifi blitz wlan0",              "oneclick_wifi_blitz"),
        ("blitz wifi",                    "oneclick_wifi_blitz"),
        ("network dominate 192.168.1.0/24", "oneclick_network_dominate"),
        ("web pwn http://target.com",     "oneclick_web_pwn"),
        ("web hack http://target.com",    "oneclick_web_pwn"),
        ("evil twin wlan0",               "oneclick_evil_twin"),
        ("rogue ap",                      "oneclick_evil_twin"),

        # ── Web ────────────────────────────────────────────────
        ("web scan http://target.com",    "web_scan"),
        ("nikto http://target.com",       "web_scan"),
        ("ssl scan target.com",           "ssl_scan"),
        ("tls check target.com",          "ssl_scan"),
        ("waf detect target.com",         "waf_detect"),

        # ── OSINT ──────────────────────────────────────────────
        ("osint target.com",              "osint"),
        ("harvest target.com",            "osint"),
        ("whois target.com",              "whois"),
        ("dns enum target.com",           "dns_enum"),

        # ── Exploitation ───────────────────────────────────────
        ("brute 10.0.0.1 ssh",            "brute"),
        ("hydra 10.0.0.1",                "brute"),
        ("sqlmap http://target.com/page?id=1", "sqli"),
        ("sqli http://target.com/page?id=1", "sqli"),
        ("sql injection http://target.com", "sqli"),
        ("mitm 10.0.0.5 10.0.0.1",       "mitm"),
        ("responder eth0",                "responder"),
        ("reverse shell",                 "reverse_shell"),
        ("msf 10.0.0.1",                  "msf"),

        # ── System / management ────────────────────────────────
        ("system check",                  "system_check"),
        ("status",                        "system_check"),
        ("check tools",                   "system_check"),
        ("list skills",                   "list_skills"),
        ("list wordlists",               "list_wordlists"),
        ("show wordlists",               "list_wordlists"),
        ("show dicts",                    "list_wordlists"),
        ("show primers",                  "show_primer"),
        ("show primer wifi",             "show_primer"),
        ("get primer recon",             "show_primer"),
        ("net guard",                     "net_guard_status"),
        ("network guard",                "net_guard_status"),
        ("connection status",             "system_check"),
        ("self protect",                  "net_guard_status"),
        ("run skill brute_ssh",           "run_skill"),
        ("set target 10.0.0.1",           "set_context"),
        ("help",                          "help"),
        ("show loot",                     "show_loot"),
        ("loot",                          "show_loot"),
        ("cracked keys",                  "show_loot"),
        ("kill james",                    "kill_james"),
        ("emergency stop",                "kill_james"),
        ("report",                        "report"),
        ("history",                       "show_log"),
        ("clear",                         "clear"),

        # ── Shell passthrough ──────────────────────────────────
        ("! ls -la",                      "shell"),
        ("! whoami",                      "shell"),

        # ── Capture / sniff ────────────────────────────────────
        ("capture handshake on wlan0mon",  "capture"),
        ("sniff packets on wlan0mon",     "capture"),
        ("autopwn wlan0",                 "autopwn"),
    ]

    passed = 0
    failed = 0
    failures = []

    for user_input, expected in CASES:
        intent, match = agent._match_intent(user_input)
        if intent == expected:
            passed += 1
        else:
            failed += 1
            failures.append((user_input, expected, intent))

    # Print results
    print(f"JAMES Intent Test Suite — {len(CASES)} cases")
    print("=" * 60)

    if failures:
        for user_input, expected, actual in failures:
            print(f"  ❌ FAIL: \"{user_input}\"")
            print(f"          Expected: {expected}")
            print(f"          Got:      {actual}")
            print()

    print(f"\n  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total:  {len(CASES)}")

    # Also check that every intent in INTENT_PATTERNS has a handler
    print("\n" + "=" * 60)
    print("Handler Coverage Check")
    print("=" * 60)

    all_intents = set(intent for _, intent in INTENT_PATTERNS)
    missing_handlers = []
    for intent in sorted(all_intents):
        handler = getattr(agent, f"_do_{intent}", None)
        if handler is None:
            missing_handlers.append(intent)

    if missing_handlers:
        print(f"  ❌ {len(missing_handlers)} intents missing handlers:")
        for i in missing_handlers:
            print(f"      - {i}")
    else:
        print(f"  ✅ All {len(all_intents)} intents have handlers")

    print(f"\n  Intent patterns: {len(INTENT_PATTERNS)}")
    print(f"  Unique intents:  {len(all_intents)}")

    # Exit code for CI
    sys.exit(1 if failed or missing_handlers else 0)


if __name__ == "__main__":
    test_intent_routing()
