#!/usr/bin/env python3
"""
JAMES Wordlist Generator — creates high-value custom wordlists
optimized for real-world pentesting scenarios.
"""

import itertools
import os
import sys

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wordlists")
os.makedirs(OUTDIR, exist_ok=True)


def write_list(filename, words):
    path = os.path.join(OUTDIR, filename)
    unique = list(dict.fromkeys(words))  # preserve order, deduplicate
    with open(path, "w") as f:
        f.write("\n".join(unique) + "\n")
    print(f"  ✅ {filename}: {len(unique):,} entries")
    return len(unique)


def gen_wifi_common():
    """Wi-Fi passwords people actually use — patterns from real audits."""
    words = []

    # Common base words for Wi-Fi
    bases = [
        "password",
        "internet",
        "wifi",
        "wireless",
        "network",
        "home",
        "house",
        "family",
        "welcome",
        "connect",
        "guest",
        "admin",
        "router",
        "netgear",
        "linksys",
        "comcast",
        "spectrum",
        "verizon",
        "xfinity",
        "att",
        "tmobile",
        "sprint",
        "frontier",
        "cox",
        "charter",
        "centurylink",
        "optimum",
        "fios",
        "love",
        "dragon",
        "master",
        "monkey",
        "shadow",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "soccer",
        "hockey",
        "batman",
        "superman",
        "letmein",
        "trustno1",
        "access",
        "hello",
        "charlie",
        "donald",
        "jordan",
        "thomas",
    ]

    # Add bases as-is + common mutations
    for base in bases:
        words.append(base)
        words.append(base.capitalize())
        words.append(base.upper())
        # Common suffixes
        for suffix in [
            "1",
            "12",
            "123",
            "1234",
            "12345",
            "!",
            "!!",
            "01",
            "99",
            "2024",
            "2025",
            "2026",
        ]:
            words.append(base + suffix)
            words.append(base.capitalize() + suffix)
        # Common prefixes
        for prefix in ["my", "the", "our"]:
            words.append(prefix + base)
            words.append((prefix + base).capitalize())

    # Numeric patterns (8+ chars for WPA)
    for i in range(0, 100000000, 11111111):
        words.append(str(i).zfill(8))
    for i in range(10000000, 10000100):
        words.append(str(i))
    words.extend(
        [
            "00000000",
            "11111111",
            "22222222",
            "33333333",
            "44444444",
            "55555555",
            "66666666",
            "77777777",
            "88888888",
            "99999999",
            "12345678",
            "87654321",
            "12341234",
            "11223344",
            "12121212",
            "01234567",
            "13131313",
            "14141414",
            "15151515",
            "10101010",
            "98765432",
            "11112222",
            "12345679",
            "123456789",
            "1234567890",
            "0123456789",
            "9876543210",
            "1111111111",
            "0000000000",
        ]
    )

    # Keyboard patterns (8+ chars)
    words.extend(
        [
            "qwerty12",
            "qwerty123",
            "qwertyui",
            "qwertyuiop",
            "asdfghjk",
            "asdfghjkl",
            "zxcvbnm1",
            "qazwsxedc",
            "1qaz2wsx",
            "1q2w3e4r",
            "q1w2e3r4",
            "zaq12wsx",
            "poiuytre",
            "lkjhgfds",
            "mnbvcxza",
            "asdfjkl;",
            "qweasdzxc",
            "1234qwer",
            "qwer1234",
            "pass1234",
            "abcd1234",
            "abcdefgh",
            "abcdefg1",
        ]
    )

    # Phone number patterns (common 8-digit WiFi passwords)
    for area in [
        "212",
        "310",
        "312",
        "404",
        "415",
        "512",
        "617",
        "702",
        "713",
        "718",
        "786",
        "818",
        "917",
    ]:
        for i in range(0, 10000, 1111):
            words.append(area + str(i).zfill(4) + "1")

    # Date patterns MMDDYYYY / DDMMYYYY (8 chars)
    for month in range(1, 13):
        for day in [1, 15, 25]:
            for year in range(2000, 2027):
                words.append(f"{month:02d}{day:02d}{year}")
                words.append(f"{day:02d}{month:02d}{year}")

    return write_list("wifi-custom-patterns.txt", words)


def gen_wifi_names():
    """Wi-Fi passwords based on common SSID naming patterns."""
    words = []

    # People often use their SSID or family name as password base
    name_bases = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Hernandez",
        "Lopez",
        "Wilson",
        "Anderson",
        "Thomas",
        "Taylor",
        "Moore",
        "Jackson",
        "Martin",
        "Lee",
        "Perez",
        "Thompson",
        "White",
        "Harris",
        "Sanchez",
        "Clark",
        "Ramirez",
        "Lewis",
        "Robinson",
        "Walker",
        "Young",
        "Allen",
        "King",
        "Wright",
        "Scott",
        "Torres",
        "Nguyen",
        "Hill",
        "Flores",
        "Green",
        "Adams",
        "Nelson",
        "Baker",
        "Hall",
        "Rivera",
        "Campbell",
        "Mitchell",
        "Carter",
    ]

    for name in name_bases:
        words.append(name.lower() + "wifi")
        words.append(name.lower() + "home")
        words.append(name.lower() + "net")
        words.append(name.lower() + "house")
        words.append(name.lower() + "family")
        for suffix in [
            "123",
            "1234",
            "12345",
            "!",
            "2024",
            "2025",
            "2026",
            "wifi1",
            "net1",
        ]:
            words.append(name.lower() + suffix)
            words.append(name + suffix)
        words.append("the" + name.lower() + "s")
        words.append("The" + name + "s")

    # Common SSID password patterns
    ssid_patterns = [
        "mywifi",
        "mynetwork",
        "myhome",
        "myhouse",
        "myinternet",
        "homewifi",
        "homenet",
        "ourwifi",
        "ournetwork",
        "ourhome",
        "guestwifi",
        "guestnet",
        "guestpass",
        "guestaccess",
        "wifipassword",
        "wifipass",
        "wifi1234",
        "wifikey",
    ]
    for p in ssid_patterns:
        words.append(p)
        words.append(p.capitalize())
        for s in ["1", "123", "!", "2025", "2026"]:
            words.append(p + s)

    return write_list("wifi-name-patterns.txt", words)


def gen_default_creds():
    """Default credentials for routers, IoT, services."""
    creds = []

    # Router defaults (user:pass format and just passwords)
    router_defaults = [
        # Netgear
        "password",
        "admin",
        "1234",
        "comcast",
        # Linksys
        "admin",
        "linksys",
        "default",
        # TP-Link
        "admin",
        "tplink",
        "tp-link",
        # D-Link
        "admin",
        "dlink",
        "private",
        # ASUS
        "admin",
        "asus",
        "password",
        # Ubiquiti
        "ubnt",
        "admin",
        # Cisco
        "cisco",
        "admin",
        "Cisco",
        "Cisco123",
        # Mikrotik
        "admin",
        "",
        # Arris
        "admin",
        "password",
        "motorola",
        # Belkin
        "admin",
        "belkin",
        # ZTE
        "admin",
        "zte",
        "user",
        # Huawei
        "admin",
        "huawei",
        "Admin@123",
        # Generic IoT
        "root",
        "toor",
        "default",
        "pass",
        "test",
        "admin123",
        "root123",
        "password1",
        "12345",
        "changeme",
        "letmein",
        "master",
        "access",
    ]

    # Service defaults
    service_defaults = {
        "ssh": [
            "root:root",
            "root:toor",
            "admin:admin",
            "pi:raspberry",
            "ubuntu:ubuntu",
            "user:user",
            "test:test",
            "guest:guest",
            "root:password",
            "root:123456",
            "admin:password",
            "admin:123456",
        ],
        "ftp": [
            "anonymous:",
            "ftp:ftp",
            "admin:admin",
            "user:user",
            "test:test",
            "root:root",
            "ftpuser:ftpuser",
        ],
        "mysql": [
            "root:",
            "root:root",
            "root:mysql",
            "root:password",
            "root:123456",
            "admin:admin",
            "mysql:mysql",
            "dbadmin:dbadmin",
        ],
        "postgres": [
            "postgres:postgres",
            "postgres:password",
            "postgres:123456",
            "admin:admin",
            "pgadmin:pgadmin",
        ],
        "telnet": [
            "admin:admin",
            "root:root",
            "user:user",
            "admin:password",
            "admin:1234",
            "root:",
        ],
        "snmp": [
            "public",
            "private",
            "community",
            "snmp",
            "default",
            "monitor",
            "manager",
            "admin",
        ],
    }

    # Write flat password file
    passwords = list(set(router_defaults))
    for pairs in service_defaults.values():
        for pair in pairs:
            if ":" in pair:
                passwords.append(pair.split(":")[1])
    write_list("default-passwords.txt", [p for p in passwords if p])

    # Write service-specific files
    for svc, pairs in service_defaults.items():
        users = list(set(p.split(":")[0] for p in pairs if ":" in p))
        passes = list(
            set(p.split(":")[1] for p in pairs if ":" in p and p.split(":")[1])
        )
        write_list(f"default-{svc}-users.txt", users)
        write_list(f"default-{svc}-passwords.txt", passes)

    return len(passwords)


def gen_hybrid_wifi():
    """
    Mega Wi-Fi wordlist: merge WPA-specific patterns + common passwords,
    filtered to WPA minimum (8 chars) and max (63 chars).
    """
    words = set()

    # Load existing WPA lists
    for f in [
        "wifi-wpa-top62.txt",
        "wifi-wpa-top447.txt",
        "wifi-wpa-top4800.txt",
        "wifi-custom-patterns.txt",
        "wifi-name-patterns.txt",
    ]:
        path = os.path.join(OUTDIR, f)
        if os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    w = line.strip()
                    if 8 <= len(w) <= 63:
                        words.add(w)

    # Pull top entries from rockyou that meet WPA length requirements
    rockyou_paths = [
        "/usr/share/wordlists/rockyou.txt",
        "/home/malcolm/Desktop/rockyou.txt",
    ]
    for rp in rockyou_paths:
        if os.path.exists(rp):
            print(f"  📂 Pulling 8+ char passwords from {rp}...")
            count = 0
            with open(rp, encoding="latin-1") as f:
                for line in f:
                    w = line.strip()
                    if 8 <= len(w) <= 63:
                        words.add(w)
                        count += 1
            print(f"     Extracted {count:,} WPA-length passwords")
            break

    out = sorted(words)
    return write_list("wifi-mega-wpa.txt", out)


def gen_web_fuzzing():
    """Custom web fuzzing paths for gobuster/dirb."""
    paths = [
        # Common web paths
        "admin",
        "login",
        "wp-admin",
        "wp-login.php",
        "administrator",
        "admin.php",
        "admin/login",
        "admin/index.php",
        "cpanel",
        "phpmyadmin",
        "dashboard",
        "panel",
        "manage",
        "management",
        "console",
        "portal",
        "webmail",
        "mail",
        "email",
        "owa",
        "exchange",
        # API paths
        "api",
        "api/v1",
        "api/v2",
        "api/v3",
        "graphql",
        "swagger",
        "api-docs",
        "swagger-ui",
        "swagger.json",
        "openapi.json",
        "api/health",
        "api/status",
        "api/config",
        "api/users",
        "api/admin",
        "rest",
        "rest/api",
        "v1",
        "v2",
        # Config / sensitive
        ".env",
        ".git",
        ".git/config",
        ".git/HEAD",
        ".gitignore",
        ".svn",
        ".svn/entries",
        ".htaccess",
        ".htpasswd",
        "config.php",
        "config.yml",
        "config.json",
        "config.xml",
        "wp-config.php",
        "wp-config.php.bak",
        "configuration.php",
        "settings.py",
        "settings.json",
        "database.yml",
        ".DS_Store",
        "web.config",
        "crossdomain.xml",
        "robots.txt",
        "sitemap.xml",
        "security.txt",
        ".well-known/security.txt",
        # Backup files
        "backup",
        "backup.zip",
        "backup.tar.gz",
        "backup.sql",
        "database.sql",
        "db.sql",
        "dump.sql",
        "data.sql",
        "backup.bak",
        "site.zip",
        "www.zip",
        "htdocs.zip",
        # CMS specific
        "wp-content",
        "wp-includes",
        "wp-json",
        "xmlrpc.php",
        "joomla",
        "components",
        "modules",
        "templates",
        "drupal",
        "sites/default",
        "core",
        # DevOps / Debug
        "debug",
        "test",
        "testing",
        "staging",
        "dev",
        "phpinfo.php",
        "info.php",
        "php_info.php",
        "test.php",
        "server-status",
        "server-info",
        "status",
        "health",
        "actuator",
        "actuator/health",
        "actuator/env",
        "actuator/beans",
        "metrics",
        "prometheus",
        "grafana",
        "jenkins",
        "hudson",
        "bamboo",
        "teamcity",
        "gitlab",
        "bitbucket",
        # Cloud / containers
        ".aws/credentials",
        "docker-compose.yml",
        "Dockerfile",
        "kubernetes",
        "k8s",
        ".kube/config",
        # Common directories
        "images",
        "img",
        "css",
        "js",
        "static",
        "assets",
        "uploads",
        "files",
        "documents",
        "docs",
        "media",
        "public",
        "private",
        "internal",
        "secret",
        "hidden",
        "tmp",
        "temp",
        "cache",
        "log",
        "logs",
        "cgi-bin",
        "bin",
        "scripts",
        "includes",
    ]

    return write_list("web-custom-paths.txt", paths)


def gen_subdomain_custom():
    """Custom subdomain wordlist for DNS brute-forcing."""
    subs = [
        "www",
        "mail",
        "remote",
        "blog",
        "webmail",
        "server",
        "ns1",
        "ns2",
        "smtp",
        "secure",
        "vpn",
        "m",
        "shop",
        "ftp",
        "mail2",
        "test",
        "portal",
        "ns",
        "ww1",
        "host",
        "support",
        "dev",
        "web",
        "bbs",
        "ww42",
        "mx",
        "email",
        "cloud",
        "api",
        "app",
        "staging",
        "admin",
        "forum",
        "news",
        "lab",
        "labs",
        "git",
        "gitlab",
        "cdn",
        "assets",
        "static",
        "media",
        "images",
        "img",
        "db",
        "database",
        "docs",
        "doc",
        "status",
        "monitor",
        "grafana",
        "prometheus",
        "jenkins",
        "ci",
        "cd",
        "deploy",
        "build",
        "registry",
        "docker",
        "k8s",
        "kubernetes",
        "auth",
        "sso",
        "login",
        "oauth",
        "accounts",
        "billing",
        "payments",
        "pay",
        "internal",
        "intranet",
        "extranet",
        "private",
        "corp",
        "office",
        "exchange",
        "owa",
        "autodiscover",
        "lyncdiscover",
        "sip",
        "meet",
        "conference",
        "chat",
        "slack",
        "teams",
        "jira",
        "confluence",
        "wiki",
        "help",
        "helpdesk",
        "tickets",
        "crm",
        "erp",
        "hr",
        "finance",
        "backup",
        "bak",
        "old",
        "legacy",
        "archive",
        "sandbox",
        "stage",
        "stg",
        "uat",
        "qa",
        "preprod",
        "pre",
        "demo",
        "beta",
        "alpha",
        "canary",
        "edge",
        "proxy",
        "gateway",
        "lb",
        "loadbalancer",
        "cache",
        "search",
        "elastic",
        "elasticsearch",
        "kibana",
        "logstash",
        "redis",
        "memcached",
        "rabbitmq",
        "kafka",
        "mq",
        "mysql",
        "postgres",
        "postgresql",
        "mongo",
        "mongodb",
        "s3",
        "storage",
        "blob",
        "bucket",
        "files",
        "analytics",
        "tracking",
        "stats",
        "metrics",
        "mobile",
        "ios",
        "android",
        "wap",
        "video",
        "stream",
        "live",
        "tv",
        "radio",
    ]
    return write_list("subdomains-custom.txt", subs)


# ── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔨 JAMES Wordlist Generator")
    print("=" * 50)
    total = 0

    print("\n[1/6] Wi-Fi Common Patterns...")
    total += gen_wifi_common()

    print("\n[2/6] Wi-Fi Name-Based Patterns...")
    total += gen_wifi_names()

    print("\n[3/6] Default Credentials...")
    total += gen_default_creds()

    print("\n[4/6] Mega WPA List (merged + rockyou 8+ chars)...")
    total += gen_hybrid_wifi()

    print("\n[5/6] Web Fuzzing Paths...")
    total += gen_web_fuzzing()

    print("\n[6/6] Custom Subdomains...")
    total += gen_subdomain_custom()

    print("\n" + "=" * 50)
    print(f"✅ Generated {total:,} total entries across all custom lists")
    print(f"📁 Output: {OUTDIR}/")
