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
    (r"(?:wifi\s*blitz|blitz)\s+(\S+)", "wifi_blitz"),
    (r"(?:pmkid|pmkid\s*attack)\s+(\S+)(?:\s+(\S+))?", "pmkid_attack"),
    (r"(?:handshake|capture\s*handshake)\s+(\S+)(?:\s+(\S+))?", "capture_handshake"),
    (r"(?:deauth|deauthenticate)\s+(\S+)(?:\s+(\S+))?", "deauth"),
    (r"(?:wps\s*pixie|pixie\s*dust)\s+(\S+)(?:\s+(\S+))?", "wps_pixie"),
    (r"(?:evil\s*twin|rogue\s*ap)\s+(\S+)", "evil_twin"),
    (r"(?:crack\s*wpa|wpa\s*crack)\s+(\S+)(?:\s+(\S+))?", "crack_wpa"),
    (r"(?:hashcat|crack\s*hash)\s+(\S+)(?:\s+(\S+))?", "hashcat"),
    (r"(?:john|john\s*the\s*ripper)\s+(\S+)", "john"),
    (r"(?:hydra|brute)\s+(\S+)", "hydra"),
    (r"(?:sqlmap|sql\s*inject)\s+(\S+)", "sqlmap"),
    (r"(?:responder)\s+(\S+)", "responder"),
    (r"(?:ettercap)\s+(\S+)", "ettercap"),
    (r"(?:nmap)\s+(\S+)", "nmap"),
    (r"(?:masscan)\s+(\S+)", "masscan"),
    (r"(?:theharvester|harvester)\s+(\S+)", "theharvester"),
    (r"(?:wafw00f)\s+(\S+)", "wafw00f"),
    (r"(?:sslscan)\s+(\S+)", "sslscan"),
    (r"(?:reaver)\s+(\S+)", "reaver"),
    (r"(?:set\s+target|target)\s+(\S+)", "set_target"),
    (r"(?:set\s+interface|iface)\s+(\S+)", "set_interface"),
    (r"(?:set\s+wordlist)\s+(\S+)", "set_wordlist"),
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

_COMPILED_INTENTS = [(re.compile(p), intent) for p, intent in INTENT_PATTERNS]
