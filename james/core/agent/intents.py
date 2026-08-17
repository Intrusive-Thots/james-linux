"""Intent patterns for the JAMES Agent."""
import re

INTENT_PATTERNS = [
    # Recon / scanning (specific before generic)
    (r"(?:masscan|mass\s*scan)\s+(.+)", "masscan"),
    (r"(?:quick\s*scan|fast\s*scan)\s+(.+)", "quick_recon"),
    (r"(?:full\s*scan|deep\s*scan|thorough\s*scan)\s+(.+)", "full_scan"),
    (r"(?:os\s*detect|fingerprint)\s+(.+)", "os_detect"),
    (r"(?:arp\s*(?:scan|discover)|discover\s*hosts?)(?:\s+(.+))?", "arp_discover"),
    (r"(?:scan\s*aps?|wifi\s*scan|scan\s*wifi|list\s*aps?)(?:\s+(.+))?", "scan_aps"),
    (r"(?:nmap|scan)\s+(.+)", "quick_recon"),
    # Wi-Fi core
    (r"(?:list\s*interfaces?|show\s*ifaces?|interfaces?)", "list_interfaces"),
    (r"(?:monitor\s*on|enable\s*monitor|start\s*monitor)(?:\s+(.+))?", "monitor_on"),
    (r"(?:monitor\s*off|disable\s*monitor|stop\s*monitor)(?:\s+(.+))?", "monitor_off"),
    (r"(?:deauth|deauthenticate)\s+(.+?)(?:\s+(\d+))?", "deauth"),
    (r"(?:capture|handshake|capture\s*handshake)(?:\s+(.+))?", "capture"),
    (r"(?:autopwn|auto\s*pwn|wifi\s*autopwn)(?:\s+(.+))?", "autopwn"),
    (r"(?:sniff|tcpdump|packet\s*capture)(?:\s+(.+))?", "sniff"),
    # Wi-Fi advanced
    (r"(?:wash|wps\s*scan)(?:\s+(.+))?", "wash_scan"),
    (r"(?:wep\s*attack|attack\s*wep)\s+(.+?)(?:\s+(.+))?", "wep_attack"),
    (r"(?:wps\s*brute|pixie|wps\s*pixie)\s+(.+?)(?:\s+(\d+))?", "wps_brute"),
    (r"(?:wpa3\s*check|check\s*wpa3)\s+(.+?)(?:\s+(.+))?", "wpa3_check"),
    (r"(?:wpa3\s*downgrade|downgrade\s*wpa3)\s+(.+?)(?:\s+(\d+))?", "wpa3_downgrade"),
    # OSINT & Web
    (r"(?:osint|recon\s*osint)\s+(.+)", "osint"),
    (r"(?:whois)\s+(.+)", "whois"),
    (r"(?:dns\s*enum|dns\s*enumeration)\s+(.+)", "dns_enum"),
    (r"(?:dns\s*lookup|resolve)\s+(.+?)(?:\s+(A|AAAA|MX|NS|ANY))?", "dns_lookup"),
    (r"(?:waf\s*detect|detect\s*waf)\s+(.+)", "waf_detect"),
    (r"(?:ssl\s*scan|tls\s*scan)\s+(.+)", "ssl_scan"),
    (r"(?:web\s*scan|nikto)\s+(.+)", "web_scan"),
    (r"(?:dir\s*brute|gobuster|dirb)\s+(.+)", "dir_brute"),
    (r"(?:sqli|sqlmap|sql\s*inject)\s+(.+)", "sqli"),
    # Network Attacks
    (r"(?:mitm|arp\s*poison|arp\s*spoof)\s+(.+?)(?:\s+(.+))?", "mitm"),
    (r"(?:responder|llmnr)(?:\s+(.+))?", "responder"),
    (r"(?:brute|hydra|bruteforce)\s+(.+?)(?:\s+(ssh|ftp|http|rdp|smb))?", "brute"),
    (r"(?:smb\s*enum|enum\s*smb)\s+(.+)", "smb_enum"),
    # Cracking
    (r"(?:crack\s*wpa|wpa\s*crack)\s+(.+?)(?:\s+(.+))?", "crack_wpa"),
    (r"(?:crack\s*hash|hashcat)\s+(.+?)(?:\s+(.+))?", "crack_hash"),
    # IoT
    (r"(?:iot\s*scan)\s+(.+)", "iot_scan"),
    (r"(?:ble\s*scan|bluetooth\s*scan)(?:\s+(.+))?", "ble_scan"),
    (r"(?:mqtt\s*scan)\s+(.+)", "mqtt_scan"),
    # Exploit
    (r"(?:reverse\s*shell|revshell)(?:\s+(\d+))?", "reverse_shell"),
    (r"(?:msf|metasploit|search\s*exploit)(?:\s+(.+))?", "msf"),
    # One-Click
    (r"(?:wifi\s*blitz|oneclick\s*wifi)(?:\s+(.+))?", "oneclick_wifi_blitz"),
    (r"(?:network\s*dominate|oneclick\s*network)\s+(.+)", "oneclick_network_dominate"),
    (r"(?:web\s*pwn|oneclick\s*web)\s+(.+)", "oneclick_web_pwn"),
    (r"(?:stealth\s*recon|oneclick\s*stealth)\s+(.+)", "oneclick_stealth_recon"),
    (r"(?:evil\s*twin|oneclick\s*evil)(?:\s+(.+))?", "oneclick_evil_twin"),
    (r"(?:scan\s*and\s*attack)\s+(.+)", "scan_and_attack"),
    # Pineapple
    (r"(?:pineapple|pineapple\s*campaign)(?:\s+(.+))?", "pineapple_campaign"),
    (r"(?:evil\s*portal|captive\s*portal)(?:\s+(.+))?", "evil_portal"),
    (r"(?:karma|karma\s*attack)(?:\s+(.+))?", "karma_attack"),
    (r"(?:harvest\s*probes?|probe\s*harvest)(?:\s+(.+))?", "harvest_probes"),
    (r"(?:track\s*clients?)", "track_clients"),
    (r"(?:snoop\s*dns|dns\s*snoop)", "snoop_dns"),
    (r"(?:spoof\s*mac|mac\s*spoof)(?:\s+(.+?))?(?:\s+(.+))?", "spoof_mac"),
    (r"(?:show\s*portal\s*creds?|portal\s*creds?)", "show_portal_creds"),
    (r"(?:stop\s*pineapple|kill\s*pineapple)", "stop_pineapple"),
    # System
    (r"(?:system\s*check|check\s*tools|tool\s*check)", "system_check"),
    (r"(?:help|commands?|\?)", "help"),
    (r"(?:show\s*log|task\s*log|history)", "show_log"),
    (r"(?:report|generate\s*report)", "report"),
    (r"(?:show\s*loot|loot|credentials?)", "show_loot"),
    (r"(?:list\s*skills?|skills?)", "list_skills"),
    (r"(?:list\s*wordlists?|wordlists?)", "list_wordlists"),
    (r"(?:run\s*skill|skill)\s+(.+)", "run_skill"),
    (r"(?:set|set\s*context)\s+(\w+)\s+(.+)", "set_context"),
    (r"(?:install\s*deps?|install\s*tools?)", "install_deps"),
    (r"(?:kill\s*james|emergency\s*stop|stop\s*all|cleanup\s*all|nuke|abort|kill\s*tools?|shut\s*down|shutdown)", "kill_james"),
    (r"(?:clear|reset)", "clear"),
    # Direct command passthrough
    (r"^!\s*(.+)", "shell"),
    (r"^(?:run|exec(?:ute)?)\s+(.+)", "shell"),
]

_COMPILED_INTENTS = [(re.compile(p), intent) for p, intent in INTENT_PATTERNS]

def get_compiled_intents():
    return _COMPILED_INTENTS
