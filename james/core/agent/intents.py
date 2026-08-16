"""Agent intent patterns for natural language parsing."""
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
    # WPS / WEP / WPA3 / IoT
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
        r"(?:wpa3\s*downgrade|dragonblood|transition\s*mode)\s+(\S+)(?:\s+(\d+))?",
        "wpa3_downgrade",
    ),
    (r"(?:iot\s*scan|device\s*scan|smart\s*home\s*scan)\s+(\S+)", "iot_scan"),
    (r"(?:ble\s*scan|bluetooth\s*scan)(?:\s+(\S+))?", "ble_scan"),
    (r"(?:mqtt\s*scan|mqtt\s*probe)\s+(\S+)", "mqtt_scan"),
    # One-click / chains
    (r"(?:wifi\s*blitz|blitz\s*wifi)(?:\s+(\S+))?", "oneclick_wifi_blitz"),
    (r"(?:network\s*dominate|dominate)\s+(\S+)", "oneclick_network_dominate"),
    (r"(?:web\s*pwn|web\s*hack)\s+(\S+)", "oneclick_web_pwn"),
    (r"(?:evil\s*twin|rogue\s*ap)(?:\s+(\S+))?", "oneclick_evil_twin"),
    # Wi-Fi control
    (r"(?:list\s*interfaces|show\s*wifi|show\s*wireless)", "list_interfaces"),
    (r"(?:enable\s*monitor|start\s*monitor(?:\s*mode)?)(?:\s+(?:on\s+)?(\S+))?", "monitor_on"),
    (r"(?:disable\s*monitor|stop\s*monitor(?:\s*mode)?)(?:\s+(\S+))?", "monitor_off"),
    (r"(?:deauth(?:enticate)?)\s+(\S+)(?:\s+(\d+))?", "deauth"),
    (r"(?:capture|sniff(?:\s*packets)?)(?:\s+(?:on\s+)?(\S+))?", "capture"),
    (r"(?:autopwn|auto\s*pwn)(?:\s+(\S+))?", "autopwn"),
    # Open wifi
    (
        r"(?:I\s+need\s+wifi|need\s+wifi|need\s+internet|want\s+wifi|get\s+wifi|find\s+wifi|connect\s+to\s+(?:open\s+)?wifi|find\s+open\s+network|join\s+wifi|grab\s+wifi|gimme\s+internet|get\s+free\s+wifi|find\s+a\s+hotspot|connect\s+wireless)",
        "connect_open_wifi",
    ),
    # OSINT / web
    (r"(?:osint|harvest)\s+(\S+)", "osint"),
    (r"(?:whois)\s+(\S+)", "whois"),
    (r"(?:dns\s*enum)\s+(\S+)", "dns_enum"),
    (r"(?:gobuster|dir\s*brute|dirb)\s+(\S+)", "dir_brute"),
    (r"(?:sqlmap|sqli|sql\s*injection)\s+(\S+)", "sqli"),
    # Attacks
    (r"(?:brute|hydra)\s+(\S+)(?:\s+(\S+))?", "brute"),
    (r"(?:mitm)\s+(\S+)(?:\s+(\S+))?", "mitm"),
    (r"(?:responder)(?:\s+(\S+))?", "responder"),
    (r"(?:reverse\s*shell)(?:\s+(\d+))?", "reverse_shell"),
    (r"(?:msf)\s*(.*)", "msf"),
    # Crack
    (r"(?:crack\s*wpa)\s+(\S+)(?:\s+(\S+))?", "crack_wpa"),
    (r"(?:crack\s*hash)\s+(\S+)(?:\s+(\S+))?", "crack_hash"),
    # System
    (r"(?:system\s*check|status|check\s*tools|connection\s*status)", "system_check"),
    (r"(?:list\s*skills)", "list_skills"),
    (r"(?:list\s*wordlists|show\s*wordlists|show\s*dicts)", "list_wordlists"),
    (r"(?:show\s*primers?|get\s*primer)(?:\s+(\S+))?", "show_primer"),
    (r"(?:net\s*guard|network\s*guard|self\s*protect)", "net_guard_status"),
    (r"(?:run\s*skill)\s+(\S+)", "run_skill"),
    (r"(?:set)\s+(\S+)\s+(.+)", "set_context"),
    (r"(?:help|\?)", "help"),
    (r"(?:show\s*loot|loot|cracked\s*keys)", "show_loot"),
    (r"(?:kill\s*james|emergency\s*stop)", "kill_james"),
    (r"(?:report)", "report"),
    (r"(?:history|show\s*log)", "show_log"),
    (r"(?:clear|reset)", "clear"),
    (r"(?:enable\s*remote|remote\s*access|enable\s*ssh|start\s*ssh|remote\s*control|ssh\s*server)", "remote_access"),
    (r"(?:install\s*deps|auto\s*install)", "install_deps"),
    (r"(?:generate\s*wordlists)(?:\s+(\S+))?", "generate_wordlists"),
    # Generic recon last
    (r"(?:scan|recon|enumerate|discover)\s+(.+)", "recon"),
    # Shell passthrough
    (r"^!\s*(.+)", "shell"),
    (r"^(?:run|exec(?:ute)?)\s+(.+)", "shell"),
]

# Pre-compile patterns once at import time for fast matching
_COMPILED_INTENTS = [(re.compile(p), intent) for p, intent in INTENT_PATTERNS]
