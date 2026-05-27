#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
# JAMES — Dependency Installer
# Ensures all required tools, wordlists, and libraries
# are present for WPS/WEP/WPA2/WPA3/IoT operations.
# Run with: sudo bash install_deps.sh
# ══════════════════════════════════════════════════════════

set -e

TARGET_USER=${SUDO_USER:-$USER}
if [ "$TARGET_USER" = "root" ]; then TARGET_HOME="/root"; else TARGET_HOME="/home/$TARGET_USER"; fi

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "  ${RED}❌${NC} $1"; }
info() { echo -e "  ${CYAN}ℹ${NC}  $1"; }

echo -e "\n${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   JAMES — Full Dependency Installer${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}\n"

# Must be root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Run as root: sudo bash install_deps.sh${NC}"
    exit 1
fi

echo -e "${CYAN}[1/5] Core Security Tools${NC}"
echo "─────────────────────────────────────────"

CORE_PKGS=(
    # Wireless
    aircrack-ng
    reaver
    bully
    wash
    hcxdumptool
    hcxtools
    macchanger
    iw
    wireless-tools
    # Scanning
    nmap
    masscan
    nikto
    gobuster
    dirb
    # Exploitation
    sqlmap
    hydra
    john
    hashcat
    metasploit-framework
    # Network
    ettercap-text-only
    responder
    arp-scan
    dnsutils
    whois
    tcpdump
    tshark
    net-tools
    # SMB/AD
    enum4linux
    smbclient
    nbtscan
    # Web
    curl
    wget
    # SSL
    sslscan
    testssl.sh
    # SSH
    openssh-server
    # Remote Desktop / GUI Streaming
    xrdp
    x11vnc
    novnc
    websockify
    # OSINT
    theharvester
    # IoT
    mosquitto-clients
    avahi-utils
    bluez
    # Python deps
    python3-pip
    python3-pyqt5
    python3-scapy
)

apt-get update -qq

INSTALLED=0
FAILED=0

for pkg in "${CORE_PKGS[@]}"; do
    if dpkg -s "$pkg" &>/dev/null; then
        ok "$pkg (already installed)"
        ((INSTALLED++))
    else
        if apt-get install -y -qq "$pkg" &>/dev/null; then
            ok "$pkg (installed)"
            ((INSTALLED++))
        else
            warn "$pkg (not available — skipping)"
            ((FAILED++))
        fi
    fi
done

echo -e "\n${CYAN}[2/5] Python Dependencies${NC}"
echo "─────────────────────────────────────────"

PY_PKGS=(
    google-genai
    requests
    scapy
    netifaces
    pyqt5
    weasyprint
    pyyaml
)

for pkg in "${PY_PKGS[@]}"; do
    if pip3 show "$pkg" &>/dev/null 2>&1; then
        ok "$pkg (already installed)"
    else
        if pip3 install "$pkg" --quiet --break-system-packages 2>/dev/null; then
            ok "$pkg (installed)"
        elif pip3 install "$pkg" --quiet 2>/dev/null; then
            ok "$pkg (installed)"
        else
            warn "$pkg (pip install failed)"
        fi
    fi
done

echo -e "\n${CYAN}[3/5] Wordlists${NC}"
echo "─────────────────────────────────────────"

WORDLIST_DIR="/usr/share/wordlists"
JAMES_WL="$TARGET_HOME/Desktop/james-linux/wordlists"
mkdir -p "$JAMES_WL"

# rockyou.txt
if [ -f "$WORDLIST_DIR/rockyou.txt" ]; then
    ok "rockyou.txt (ready)"
elif [ -f "$WORDLIST_DIR/rockyou.txt.gz" ]; then
    info "Decompressing rockyou.txt.gz..."
    gunzip -k "$WORDLIST_DIR/rockyou.txt.gz" 2>/dev/null || gunzip "$WORDLIST_DIR/rockyou.txt.gz"
    ok "rockyou.txt (decompressed)"
elif [ -f "$TARGET_HOME/Desktop/rockyou.txt" ]; then
    ok "rockyou.txt (found on Desktop)"
else
    warn "rockyou.txt not found — download manually"
fi

# WPS PIN lists
WPS_PINS="$JAMES_WL/wps_pins.txt"
if [ ! -f "$WPS_PINS" ]; then
    info "Generating common WPS PINs..."
    cat > "$WPS_PINS" << 'PINS'
12345670
00000000
01234567
11111110
22222220
33333330
44444440
55555550
66666660
77777770
88888880
99999990
12340000
00001234
01onal01
98765432
PINS
    # Generate sequential 8-digit PINs with valid checksums
    python3 -c "
def wps_checksum(pin7):
    accum = 0
    while pin7:
        accum += 3 * (pin7 % 10)
        pin7 //= 10
        accum += pin7 % 10
        pin7 //= 10
    return (10 - accum % 10) % 10

for i in range(0, 10000000, 1000):
    pin7 = i
    cs = wps_checksum(pin7)
    print(f'{pin7:07d}{cs}')
" >> "$WPS_PINS" 2>/dev/null
    ok "WPS PIN list generated ($WPS_PINS)"
else
    ok "WPS PINs (ready)"
fi

# Common IoT default credentials
IOT_CREDS="$JAMES_WL/iot_default_creds.txt"
if [ ! -f "$IOT_CREDS" ]; then
    cat > "$IOT_CREDS" << 'CREDS'
admin:admin
admin:password
admin:1234
admin:12345
admin:123456
root:root
root:toor
root:password
root:admin
root:12345
user:user
ubnt:ubnt
pi:raspberry
default:default
support:support
admin:
root:
cisco:cisco
admin:motorola
admin:changeme
admin:p@ssw0rd
admin:default
guest:guest
service:service
supervisor:supervisor
tech:tech
CREDS
    ok "IoT default credentials generated"
else
    ok "IoT creds (ready)"
fi

# WiFi password lists (common)
WIFI_COMMON="$JAMES_WL/wifi_common.txt"
if [ ! -f "$WIFI_COMMON" ]; then
    info "Generating common WiFi passwords..."
    cat > "$WIFI_COMMON" << 'WIFIPW'
password
12345678
123456789
1234567890
qwertyuiop
letmein123
password1
iloveyou1
sunshine1
princess1
football1
charlie123
shadow123
master123
dragon123
monkey123
mustang123
access123
batman123
trustno1
welcome1
WIFIPW
    # Add numeric patterns
    for i in $(seq 00000000 00000100); do printf "%08d\n" $i; done >> "$WIFI_COMMON" 2>/dev/null
    ok "WiFi common passwords generated"
else
    ok "WiFi common passwords (ready)"
fi

# dirb/dirbuster wordlists check
if [ -d "/usr/share/wordlists/dirb" ]; then
    ok "dirb wordlists (ready)"
elif [ -d "/usr/share/dirb/wordlists" ]; then
    ok "dirb wordlists (at /usr/share/dirb/wordlists)"
else
    warn "dirb wordlists not found"
fi

# SecLists (optional but recommended)
if [ -d "/usr/share/seclists" ] || [ -d "/usr/share/wordlists/seclists" ]; then
    ok "SecLists (ready)"
else
    info "SecLists not installed (optional: sudo apt install seclists)"
fi

echo -e "\n${CYAN}[4/5] System Configuration${NC}"
echo "─────────────────────────────────────────"

# Enable SSH
systemctl enable ssh 2>/dev/null && ok "SSH service enabled" || warn "SSH service setup issue"
systemctl start ssh 2>/dev/null && ok "SSH service started" || true

# Sudo NOPASSWD for malcolm
SUDOERS_LINE="$TARGET_USER ALL=(ALL) NOPASSWD: ALL"
if grep -q "^$TARGET_USER" /etc/sudoers.d/james 2>/dev/null; then
    ok "Sudo NOPASSWD (already configured)"
else
    echo "$SUDOERS_LINE" > /etc/sudoers.d/james
    chmod 440 /etc/sudoers.d/james
    ok "Sudo NOPASSWD configured for $TARGET_USER"
fi

# Bluetooth
if systemctl is-active bluetooth &>/dev/null; then
    ok "Bluetooth service running"
else
    systemctl enable bluetooth 2>/dev/null && systemctl start bluetooth 2>/dev/null && ok "Bluetooth enabled" || warn "Bluetooth not available"
fi

echo -e "\n${CYAN}[5/5] Tool Verification${NC}"
echo "─────────────────────────────────────────"

TOOLS=(
    "aircrack-ng:aircrack-ng --help"
    "airodump-ng:airodump-ng --help"
    "aireplay-ng:aireplay-ng --help"
    "airmon-ng:airmon-ng --help"
    "reaver:reaver -h"
    "bully:bully -h"
    "wash:wash -h"
    "hcxdumptool:hcxdumptool --help"
    "hcxpcapngtool:hcxpcapngtool --help"
    "nmap:nmap --version"
    "masscan:masscan --version"
    "hashcat:hashcat --version"
    "john:john --help"
    "hydra:hydra -h"
    "sqlmap:sqlmap --version"
    "nikto:nikto -Version"
    "gobuster:gobuster version"
    "ettercap:ettercap --version"
    "responder:responder -h"
    "enum4linux:enum4linux -h"
    "arp-scan:arp-scan --version"
    "sslscan:sslscan --version"
    "theharvester:theHarvester -h"
    "mosquitto_sub:mosquitto_sub --help"
    "hcitool:hcitool --help"
    "macchanger:macchanger -h"
    "x11vnc:x11vnc -version"
    "websockify:websockify --help"
)

AVAILABLE=0
MISSING=0

for entry in "${TOOLS[@]}"; do
    name="${entry%%:*}"
    cmd="${entry##*:}"
    if command -v "$name" &>/dev/null; then
        ok "$name"
        ((AVAILABLE++))
    else
        fail "$name (not found)"
        ((MISSING++))
    fi
done

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   Installation Summary${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "  Packages:  ${GREEN}$INSTALLED installed${NC}, ${YELLOW}$FAILED skipped${NC}"
echo -e "  Tools:     ${GREEN}$AVAILABLE available${NC}, ${RED}$MISSING missing${NC}"
echo ""

# Generate JAMES WiFi-optimized wordlists
echo -e "${CYAN}[BONUS] Generating JAMES WiFi Wordlists${NC}"
echo "─────────────────────────────────────────"
JAMES_DIR="$TARGET_HOME/Desktop/james-linux"
if [ -f "$JAMES_DIR/james/wordlists/generator.py" ]; then
    su - $TARGET_USER -c "cd $JAMES_DIR && python3 -c '
from james.wordlists.generator import WifiWordlistGenerator
gen = WifiWordlistGenerator()
common = gen.generate_wifi_common()
numeric = gen.generate_numeric()
ultimate = gen.get_combined_wordlist()
c1 = sum(1 for _ in open(common))
c2 = sum(1 for _ in open(numeric))
c3 = sum(1 for _ in open(ultimate))
print(f\"  wifi_common.txt:   {c1:,} candidates\")
print(f\"  wifi_numeric.txt:  {c2:,} candidates\")
print(f\"  wifi_ultimate.txt: {c3:,} candidates\")
'" 2>/dev/null && ok "JAMES WiFi wordlists generated" || warn "Wordlist generation skipped"
else
    info "JAMES wordlist generator not found — run from JAMES GUI instead"
fi

echo ""
echo -e "  ${CYAN}JAMES is ready for WPS/WEP/WPA2/WPA3/IoT operations.${NC}"
echo -e "  ${CYAN}Run: python3 main.py${NC}"
echo ""
