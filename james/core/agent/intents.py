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
        r"(?:auto\s*attack|auto\s*pwn|one\s*click)\s+(\S+)",
        "auto_attack",
    ),
    # WiFi specific
    (r"(?:deauth|deauthenticate)\s+(\S+)(?:\s+(\S+))?", "deauth"),
    (r"(?:pmkid|pmk\s*id)\s+(\S+)(?:\s+(\S+))?", "pmkid"),
    (r"(?:handshake|capture\s*handshake)\s+(\S+)(?:\s+(\S+))?", "handshake"),
    (r"(?:evil\s*twin|rogue\s*ap)\s+(\S+)(?:\s+(\S+))?", "evil_twin"),
    (r"(?:pixie|pixie\s*dust|wps\s*pixie)\s+(\S+)(?:\s+(\S+))?", "wps_pixie"),
    (r"(?:monitor\s*mode|start\s*monitor|airmon)\s*(\S+)?", "monitor_mode"),
    (r"(?:managed\s*mode|stop\s*monitor)\s*(\S+)?", "managed_mode"),
    (
        r"(?:connect\s*(?:to\s*)?(?:open\s*)?(?:wifi|wi-fi|internet|network))",
        "connect_open_wifi",
    ),
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
    (
        r"(?:reverse\s*shell|rev\s*shell|listener)(?:\s+(\d+))?",
        "reverse_shell",
    ),
    (r"(?:msf|metasploit|msfconsole)(?:\s+(.+))?", "msf"),
    # Cracking
    (
        r"crack\s+(?:wpa|handshake|cap)\s+(\S+)(?:\s+(?:with|using)\s+(\S+))?",
        "crack_wpa",
    ),
    (
        r"crack\s+(?:hash(?:es)?)\s+(\S+)(?:\s+(?:with|using)\s+(\S+))?",
        "crack_hash",
    ),
    # Brute force
    (r"(?:brute\s*force|hydra|brute)\s+(\S+)(?:\s+(\S+))?", "brute"),
    # System
    (r"(?:system\s*check|check\s*tools?|status)", "system_check"),
    (r"(?:list|show)\s+skills?", "list_skills"),
    (
        r"(?:list|show)\s+(?:wordlists?|word\s*lists?|dicts?|dictionaries)",
        "list_wordlists",
    ),
    (
        r"(?:generate|create|build|make)\s+(?:wordlists?|word\s*lists?)(?:\s+(.+))?",
        "generate_wordlists",
    ),
    (r"(?:show|list|get)\s+primers?(?:\s+(\w+))?", "show_primer"),
    (
        r"(?:net\s*guard|network\s*guard|connection\s*status|self.?protect)",
        "net_guard_status",
    ),
    (r"(?:run|execute|load)\s+skill\s+(\S+)", "run_skill"),
    (r"set\s+(\w+)\s+(.+)", "set_context"),
    (r"(?:help|commands?|what\s+can)", "help"),
    (r"(?:history|log|task\s*log)", "show_log"),
    (r"(?:report|generate\s*report|export\s*report)", "report"),
    (r"(?:show\s*loot|loot|cracked|captured\s*keys|show\s*keys)", "show_loot"),
    (
        r"(?:remote\s*(?:access|control)|enable\s*(?:remote|ssh)|start\s*ssh|ssh\s*server)",
        "remote_access",
    ),
    (
        r"(?:kill\s*james|kill\s*all|stop\s*everything|emergency\s*stop|stop\s*all\s*tools?|cleanup\s*all|nuke|abort|kill\s*tools?|shut\s*down|shutdown)",
        "kill_james",
    ),
    (r"(?:clear|reset)", "clear"),
    # Direct command passthrough
    (r"^!\s*(.+)", "shell"),
    (r"^(?:run|exec(?:ute)?)\s+(.+)", "shell"),
]
