"""Intent pattern matching for the JAMES agent."""
import re

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
    (
        r"(?:scan\s*aps|nearby\s*aps|nearby\s*networks|show\s*aps)(?:\s+(\S+))?",
        "scan_aps",
    ),
    # Stealth/passive recon must be before the generic 'recon' catch-all
    (
        r"(?:stealth\s*recon|passive\s*recon|silent\s*recon)\s+(\S+)",
        "oneclick_stealth_recon",
    ),
    # Discovery (must be before generic recon catch-all)
    (
        r"(?:arp\s*scan|arp\s*discover|lan\s*scan|network\s*discover|host\s*discover)(?:\s+(\S+))?",
        "arp_discover",
    ),
    (r"(?:web\s*vuln\s*scan)\s+(\S+)", "nikto_scan"),
    (r"(?:smb\s*enum|enum4linux|smb\s*scan|netbios)\s+(\S+)", "smb_enum"),
    (r"(?:dns\s*lookup|nslookup|resolve)\s+(\S+)(?:\s+(\S+))?", "dns_lookup"),
    # WPS / WEP / WPA3 / IoT — must be BEFORE generic scan catch-all
    (r"(?:wash|wps\s*scan|scan\s*wps|wps\s*detect)(?:\s+(\S+))?", "wash_scan"),
    (
        r"(?:wep\s*(?:attack|crack|hack)|crack\s*wep|attack\s*wep)\s+(\S+)(?:\s+(\S+))?",
        "wep_attack",
    ),
    (
        r"(?:wps\s*brute|brute\s*wps|wps\s*pin|pin\s*brute)\s+(\S+)(?:\s+(\d+))?",
        "wps_brute",
    ),
    (
        r"(?:wpa3\s*(?:check|scan|detect|probe)|sae\s*(?:check|scan|detect))\s+(\S+)(?:\s+(\S+))?",
        "wpa3_check",
    ),
    (
        r"(?:wpa3\s*(?:downgrade|attack|crack)|sae\s*(?:downgrade|attack)|dragonblood)\s+(\S+)(?:\s+(\d+))?",
        "wpa3_downgrade",
    ),
    (
        r"(?:iot\s*scan|iot\s*recon|smart\s*home\s*scan|device\s*scan)\s+(\S+)",
        "iot_scan",
    ),
    (r"(?:ble\s*scan|bluetooth\s*scan|bt\s*scan)(?:\s+(\S+))?", "ble_scan"),
    (r"(?:mqtt\s*scan|mqtt\s*probe|mqtt\s*enum)\s+(\S+)", "mqtt_scan"),
    # Compound auto-attack commands (must be before generic scan/recon catch-all)
    (
        r"(?:scan\s*(?:and|&)\s*attack|recon\s*(?:and|&)\s*attack|auto\s*recon)\s+(\S+)",
        "scan_and_attack",
    ),
    (
        r"(?:auto\s*attack|attack\s*all|attack\s*services|auto\s*exploit)(?:\s+(\S+))?",
        "auto_attack_services",
    ),
    # Generic recon catch-all (MUST be last in this section)
    (r"(?:scan|recon|enumerate|discover)\s+(.+)", "recon"),
    # Wi-Fi
    (r"(?:list|show)\s+(?:interfaces?|wifi|wlan|wireless)", "list_interfaces"),
    (
        r"(?:enable|start|turn\s*on)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?",
        "monitor_on",
    ),
    (
        r"(?:disable|stop|turn\s*off)\s+monitor(?:\s+(?:mode\s+)?(?:on\s+)?(\S+))?",
        "monitor_off",
    ),
    (r"deauth(?:enticate)?\s+(\S+)(?:\s+(\d+))?", "deauth"),
    (
        r"(?:capture|sniff)\s+(?:handshake|packets?)\s+(?:on\s+)?(\S+)",
        "capture",
    ),
    (
        r"(?:auto\s*pwn|autopwn|auto\s*hack|auto\s*crack|autopilot|go\s*autonomous|wifi\s*autopilot)(?:\s+(\S+))?",
        "autopwn",
    ),
    (
        r"(?:install\s*(?:deps|dependencies|tools|packages)|auto\s*install|setup\s*tools|check\s*deps)",
        "install_deps",
    ),
    # One-Click Hacks
    (
        r"(?:wifi\s*blitz|blitz\s*wifi|wifi\s*nuke)(?:\s+(\S+))?",
        "oneclick_wifi_blitz",
    ),
    (
        r"(?:network\s*dominate|dominate|net\s*dominate|net\s*pwn)\s+(\S+)",
        "oneclick_network_dominate",
    ),
    (r"(?:web\s*pwn|web\s*hack|web\s*nuke)\s+(\S+)", "oneclick_web_pwn"),
    (r"(?:evil\s*twin|rogue\s*ap)(?:\s+(\S+))?", "oneclick_evil_twin"),
    (
        r"(?:stop\s*pineapple|stop\s*portal|stop\s*karma|pineap\s*stop)",
        "stop_pineapple",
    ),
]

# Pre-compile patterns once at import time for fast matching
_COMPILED_INTENTS = [(re.compile(p), intent) for p, intent in INTENT_PATTERNS]
