"""
JAMES WiFi Arsenal Tab — Unified Recon + Cracker + KARMA (Layout v2).
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
    QSizePolicy,
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
from james.gui.theme import LOG_STYLE, TERMINAL_STYLE

logger = logging.getLogger(__name__)


# ── AutoKarmaWorker (unchanged logic) ─────────────────────────────────
class AutoKarmaWorker(QThread):
    log_signal    = pyqtSignal(str)
    phase_signal  = pyqtSignal(int, str)
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
        # Phase 1
        self.phase_signal.emit(1, "Phase 1/5: Interface Setup")
        ifaces = self.orchestrator.wifi_interfaces()
        if not ifaces:
            self._log("❌ No wireless interfaces detected.")
            self.finished_signal.emit(False)
            return

        mon_iface = None
        for ifc in ifaces:
            safe, _ = self.orchestrator.net_guard.check_monitor_safe(ifc["interface"])
            if safe:
                mon_iface = ifc["interface"]
                break

        if not mon_iface:
            self._log("❌ No safe interface for monitor mode.")
            self.finished_signal.emit(False)
            return

        # Phase 2 — probe harvest
        self.phase_signal.emit(2, "Phase 2/5: Harvesting Probes")
        self._log(f"Harvesting probe requests on {mon_iface} for {self.probe_duration}s…")
        try:
            probes = self.pineap.harvest_probes(mon_iface, duration=self.probe_duration)
            self._log(f"Captured {probes.get('count', 0)} probe frames.")
        except Exception as e:
            self._log(f"⚠ Probe harvest error: {e}")

        if self._aborted():
            self.finished_signal.emit(False)
            return

        # Phase 3 — KARMA AP
        self.phase_signal.emit(3, "Phase 3/5: Launching KARMA AP")
        self._log(f"Starting KARMA rogue AP: SSID={self.ssid} portal={self.portal}")
        try:
            result = self.pineap.start_karma_with_portal(
                interface=mon_iface,
                ssid=self.ssid,
                portal=self.portal,
            )
            self._log(f"KARMA active: {result.get('status')}")
        except Exception as e:
            self._log(f"❌ KARMA start error: {e}")
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        # Phase 4 — monitor
        self.phase_signal.emit(4, "Phase 4/5: Monitoring for Credentials")
        self._log(f"Monitoring for {self.monitor_duration}s…")
        deadline = time.time() + self.monitor_duration
        while time.time() < deadline and not self._aborted():
            time.sleep(5)
            try:
                status = self.pineap.get_live_status()
                self.status_signal.emit(status)
            except Exception:
                pass

        # Phase 5 — cleanup
        self.phase_signal.emit(5, "Phase 5/5: Cleanup")
        self._safe_cleanup()
        self._log("✅ KARMA campaign complete.")
        self.finished_signal.emit(True)


# ── WiFiArsenalTab ─────────────────────────────────────────────────────
class WiFiArsenalTab(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window  = main_window
        self.orchestrator = main_window.orchestrator
        self.pineap       = self.orchestrator.pineap   # shared with AutoPilotTab
        self.worker       = None
        self.karma_worker = None
        self.recon_proc   = None
        self.deauth_proc  = None

        self.selected_bssid   = None
        self.selected_essid   = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._build_interface_bar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_recon_tab(),   "📡  Recon")
        self.tabs.addTab(self._build_attack_tab(),  "🎯  Attack & Crack")
        self.tabs.addTab(self._build_karma_tab(),   "👹  Rogue AP")
        layout.addWidget(self.tabs)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._do_poll)

        QTimer.singleShot(500, self._refresh_interfaces)

    def _build_interface_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(
            "QFrame { background: #080d1c; border: 1px solid #16213a;"
            " border-radius: 10px; padding: 4px 8px; }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(8)

        iface_lbl = QLabel("Interface")
        iface_lbl.setStyleSheet("color: #3a5a7a; font-size: 11px; font-weight: 600;")
        row.addWidget(iface_lbl)

        self.iface_combo = QComboBox()
        self.iface_combo.setMinimumWidth(170)
        self.iface_combo.setToolTip("Active wireless interface")
        row.addWidget(self.iface_combo)

        self.lbl_iface_status = QLabel("● Unknown")
        self.lbl_iface_status.setObjectName("statusWarn")
        self.lbl_iface_status.setMinimumWidth(90)
        row.addWidget(self.lbl_iface_status)

        row.addWidget(self._vsep())

        self.btn_refresh = QPushButton("↻  Refresh")
        self.btn_refresh.setFixedWidth(90)
        self.btn_refresh.setToolTip("Re-scan wireless interfaces")

        self.btn_hw_info = QPushButton("📊  HW Info")
        self.btn_hw_info.setFixedWidth(90)
        self.btn_hw_info.setToolTip("Show adapter chipset & driver details")

        self.btn_monitor_on  = QPushButton("▶  Monitor ON")
        self.btn_monitor_on.setObjectName("successBtn")
        self.btn_monitor_on.setFixedWidth(110)

        self.btn_monitor_off = QPushButton("■  Monitor OFF")
        self.btn_monitor_off.setObjectName("warnBtn")
        self.btn_monitor_off.setFixedWidth(110)

        for btn in (self.btn_refresh, self.btn_hw_info,
                    self.btn_monitor_on, self.btn_monitor_off):
            row.addWidget(btn)

        row.addStretch()
        return bar

    # ─── Recon tab ────────────────────────────────────────────────────

    def _build_recon_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        # Scan control row
        ctrl = QHBoxLayout()
        self.btn_start_scan = QPushButton("📡  START SCAN")
        self.btn_start_scan.setObjectName("primaryBtn")
        self.btn_start_scan.setMinimumHeight(38)

        self.btn_stop_scan = QPushButton("⏹  STOP")
        self.btn_stop_scan.setObjectName("dangerBtn")
        self.btn_stop_scan.setMinimumHeight(38)
        self.btn_stop_scan.setEnabled(False)

        self.lbl_stats = QLabel("Ready")
        self.lbl_stats.setObjectName("dimLabel")
        self.lbl_stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        ctrl.addWidget(self.btn_start_scan)
        ctrl.addWidget(self.btn_stop_scan)
        ctrl.addStretch()
        ctrl.addWidget(self.lbl_stats)
        layout.addLayout(ctrl)

        splitter = QSplitter(Qt.Vertical)

        # AP table
        ap_group = QGroupBox("Access Points")
        ap_layout = QVBoxLayout(ap_group)
        ap_layout.setContentsMargins(6, 6, 6, 6)
        self.ap_table = QTableWidget()
        self.ap_table.setColumnCount(6)
        self.ap_table.setHorizontalHeaderLabels(
            ["BSSID", "ESSID", "CH", "ENC", "PWR", "SIGNAL"]
        )
        self.ap_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ap_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ap_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ap_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ap_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ap_table.setAlternatingRowColors(True)
        self.ap_table.verticalHeader().setVisible(False)
        ap_layout.addWidget(self.ap_table)
        splitter.addWidget(ap_group)

        # Clients table
        cl_group = QGroupBox("Clients & Probes")
        cl_layout = QVBoxLayout(cl_group)
        cl_layout.setContentsMargins(6, 6, 6, 6)
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(
            ["Client MAC", "Associated AP", "Probed SSIDs", "PWR"]
        )
        self.client_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.client_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.client_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_table.setAlternatingRowColors(True)
        self.client_table.verticalHeader().setVisible(False)
        cl_layout.addWidget(self.client_table)
        splitter.addWidget(cl_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return tab

    # ─── Attack & Crack tab ───────────────────────────────────────────

    def _build_attack_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        # Target info card
        target_card = QFrame()
        target_card.setStyleSheet(
            "QFrame { background: #080d1c; border: 1px solid #16213a;"
            " border-radius: 10px; }"
        )
        tc_layout = QHBoxLayout(target_card)
        tc_layout.setContentsMargins(16, 10, 16, 10)
        tc_layout.setSpacing(20)

        target_icon = QLabel("🎯")
        target_icon.setStyleSheet("font-size: 24px;")
        tc_layout.addWidget(target_icon)

        target_text = QVBoxLayout()
        target_text.setSpacing(2)
        target_cap = QLabel("SELECTED TARGET")
        target_cap.setStyleSheet(
            "color: #3a5a7a; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;"
        )
        self.lbl_target = QLabel("None selected — right-click an AP in Recon")
        self.lbl_target.setStyleSheet(
            "color: #c8d6e5; font-size: 13px; font-weight: 600;"
        )
        target_text.addWidget(target_cap)
        target_text.addWidget(self.lbl_target)
        tc_layout.addLayout(target_text, stretch=1)
        layout.addWidget(target_card)

        # 1. Capture
        cap_group = QGroupBox("1 · Capture")
        cap_layout = QHBoxLayout(cap_group)
        cap_layout.setSpacing(8)
        self.btn_capture = QPushButton("🤝  Capture Handshake")
        self.btn_capture.setObjectName("primaryBtn")
        self.btn_capture.setMinimumHeight(38)
        self.btn_capture.setEnabled(False)
        self.btn_pmkid = QPushButton("⚡  Capture PMKID")
        self.btn_pmkid.setObjectName("primaryBtn")
        self.btn_pmkid.setMinimumHeight(38)
        self.btn_pmkid.setEnabled(False)
        cap_layout.addWidget(self.btn_capture)
        cap_layout.addWidget(self.btn_pmkid)
        layout.addWidget(cap_group)

        # 2. Automated pipeline
        auto_group = QGroupBox("2 · Automated Attack Pipeline")
        auto_layout = QHBoxLayout(auto_group)
        self.btn_airgeddon = QPushButton("👿  Launch Airgeddon Evil Twin")
        self.btn_airgeddon.setObjectName("dangerBtn")
        self.btn_airgeddon.setMinimumHeight(42)
        self.btn_airgeddon.setEnabled(False)
        self.btn_airgeddon_stop = QPushButton("🛑  Stop Airgeddon")
        self.btn_airgeddon_stop.setObjectName("warnBtn")
        self.btn_airgeddon_stop.setMinimumHeight(42)
        self.btn_airgeddon_stop.setEnabled(False)
        auto_layout.addWidget(self.btn_airgeddon, stretch=2)
        auto_layout.addWidget(self.btn_airgeddon_stop, stretch=1)
        layout.addWidget(auto_group)

        # 3. Manual cracker
        crack_group = QGroupBox("3 · Dictionary Attack Engine")
        crack_layout = QVBoxLayout(crack_group)
        crack_layout.setSpacing(8)

        # File row
        file_row = QHBoxLayout()
        file_row.setSpacing(6)

        cap_lbl = QLabel("Capture:")
        cap_lbl.setObjectName("dimLabel")
        cap_lbl.setFixedWidth(55)
        self.lbl_cap_file = QLabel("None")
        self.lbl_cap_file.setStyleSheet("color: #c8d6e5; font-size: 12px;")
        self.btn_browse_cap = QPushButton("📂  Browse")
        self.btn_browse_cap.setFixedWidth(90)

        wl_lbl = QLabel("Wordlist:")
        wl_lbl.setObjectName("dimLabel")
        wl_lbl.setFixedWidth(60)
        self.wl_combo = QComboBox()
        self.wl_combo.setMinimumWidth(180)
        self.btn_browse_wl = QPushButton("📂  Custom")
        self.btn_browse_wl.setFixedWidth(90)

        file_row.addWidget(cap_lbl)
        file_row.addWidget(self.lbl_cap_file, stretch=1)
        file_row.addWidget(self.btn_browse_cap)
        file_row.addWidget(self._vsep())
        file_row.addWidget(wl_lbl)
        file_row.addWidget(self.wl_combo)
        file_row.addWidget(self.btn_browse_wl)
        crack_layout.addLayout(file_row)

        # Engine row
        engine_row = QHBoxLayout()
        engine_row.setSpacing(8)
        self.btn_crack_aircrack = QPushButton("🔓  Aircrack-ng")
        self.btn_crack_aircrack.setMinimumHeight(38)
        self.btn_crack_hashcat  = QPushButton("🔥  Hashcat")
        self.btn_crack_hashcat.setMinimumHeight(38)
        self.btn_crack_smart    = QPushButton("🧠  Smart (Auto)")
        self.btn_crack_smart.setObjectName("primaryBtn")
        self.btn_crack_smart.setMinimumHeight(38)
        engine_row.addWidget(self.btn_crack_aircrack)
        engine_row.addWidget(self.btn_crack_hashcat)
        engine_row.addWidget(self.btn_crack_smart)
        crack_layout.addLayout(engine_row)
        layout.addWidget(crack_group)

        # Result card
        result_card = QFrame()
        result_card.setStyleSheet(
            "QFrame { background: #080d1c; border: 1px solid #16213a;"
            " border-radius: 10px; padding: 4px; }"
        )
        res_layout = QHBoxLayout(result_card)
        res_layout.setContentsMargins(16, 8, 16, 8)
        res_icon = QLabel("🔑")
        res_icon.setStyleSheet("font-size: 20px;")
        self.lbl_result = QLabel("Ready")
        self.lbl_result.setObjectName("statusOk")
        self.lbl_result.setStyleSheet(
            "color: #4a6a8a; font-size: 13px; font-weight: 600;"
        )
        res_layout.addWidget(res_icon)
        res_layout.addWidget(self.lbl_result, stretch=1)
        layout.addWidget(result_card)

        layout.addStretch()
        return tab

    # ─── Rogue AP / KARMA tab ─────────────────────────────────────────

    def _build_karma_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        # Config
        cfg_group = QGroupBox("Campaign Configuration")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(8)

        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(10)

        ssid_lbl = QLabel("Evil Twin SSID:")
        ssid_lbl.setObjectName("dimLabel")
        self.txt_ssid = QLineEdit("Free_WiFi")
        self.txt_ssid.setMinimumWidth(160)

        portal_lbl = QLabel("Portal Template:")
        portal_lbl.setObjectName("dimLabel")
        self.combo_portal = QComboBox()
        self.combo_portal.addItems(["wifi_login", "hotel_login", "social_login"])
        self.combo_portal.setMinimumWidth(130)

        cfg_row.addWidget(ssid_lbl)
        cfg_row.addWidget(self.txt_ssid)
        cfg_row.addWidget(self._vsep())
        cfg_row.addWidget(portal_lbl)
        cfg_row.addWidget(self.combo_portal)
        cfg_row.addStretch()
        cfg_layout.addLayout(cfg_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        self.btn_karma_start = QPushButton("👹  START KARMA CAMPAIGN")
        self.btn_karma_start.setObjectName("dangerBtn")
        self.btn_karma_start.setMinimumHeight(42)
        self.btn_karma_stop = QPushButton("🛑  STOP")
        self.btn_karma_stop.setObjectName("warnBtn")
        self.btn_karma_stop.setMinimumHeight(42)
        self.btn_karma_stop.setEnabled(False)
        ctrl_row.addWidget(self.btn_karma_start, stretch=3)
        ctrl_row.addWidget(self.btn_karma_stop, stretch=1)
        cfg_layout.addLayout(ctrl_row)
        layout.addWidget(cfg_group)

        # Live stats cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._karma_clients_card = self._make_stat_card("💻", "CLIENTS", "0", "#00e5ff")
        self._karma_dns_card     = self._make_stat_card("🌐", "DNS QUERIES", "0", "#a855f7")
        self._karma_creds_card   = self._make_stat_card("🔑", "CREDENTIALS", "0", "#00ff88")
        stats_row.addWidget(self._karma_clients_card)
        stats_row.addWidget(self._karma_dns_card)
        stats_row.addWidget(self._karma_creds_card)
        layout.addLayout(stats_row)

        # Live tables
        dash_group = QGroupBox("Live Dashboard")
        dash_layout = QVBoxLayout(dash_group)
        tbl_split = QSplitter(Qt.Horizontal)

        self.karma_clients_tbl = QTableWidget(0, 2)
        self.karma_clients_tbl.setHorizontalHeaderLabels(["Client IP", "MAC"])
        self.karma_clients_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.karma_clients_tbl.verticalHeader().setVisible(False)

        self.karma_creds_tbl = QTableWidget(0, 2)
        self.karma_creds_tbl.setHorizontalHeaderLabels(["Target IP", "Captured Payload"])
        self.karma_creds_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.karma_creds_tbl.verticalHeader().setVisible(False)

        tbl_split.addWidget(self.karma_clients_tbl)
        tbl_split.addWidget(self.karma_creds_tbl)
        dash_layout.addWidget(tbl_split)
        layout.addWidget(dash_group)

        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(6, 6, 6, 6)
        self.karma_log = QPlainTextEdit()
        self.karma_log.setReadOnly(True)
        self.karma_log.setMinimumHeight(110)
        self.karma_log.setStyleSheet(LOG_STYLE)
        self.karma_log.setFont(QFont("JetBrains Mono", 10))
        log_layout.addWidget(self.karma_log)
        layout.addWidget(log_group)

        return tab

    # ─── Helpers ──────────────────────────────────────────────────────

    def _vsep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setStyleSheet("color: #16213a; margin: 4px 2px;")
        return f

    def _make_stat_card(self, icon: str, label: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #080d1c; border: 1px solid #16213a;"
            " border-radius: 10px; }"
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 8, 14, 8)
        v.setSpacing(2)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 800;"
            f" font-family: 'JetBrains Mono', monospace;"
        )
        val_lbl.setObjectName(f"_karma_{label.lower().replace(' ', '_')}_val")

        cap_lbl = QLabel(f"{icon}  {label}")
        cap_lbl.setAlignment(Qt.AlignCenter)
        cap_lbl.setStyleSheet(
            "color: #3a5a7a; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;"
        )

        v.addWidget(val_lbl)
        v.addWidget(cap_lbl)
        return card

    def _get_karma_val(self, card: QFrame) -> QLabel:
        """Return the value QLabel inside a stat card."""
        for child in card.findChildren(QLabel):
            if child.objectName().startswith("_karma_"):
                return child
        return card.findChildren(QLabel)[0]

    # ── Signals ───────────────────────────────────────────────────────

    def _connect_signals(self):
        self.btn_refresh.clicked.connect(self._refresh_interfaces)
        self.btn_hw_info.clicked.connect(self._show_hw_info)
        self.btn_monitor_on.clicked.connect(self._enable_monitor)
        self.btn_monitor_off.clicked.connect(self._disable_monitor)
        self.iface_combo.currentTextChanged.connect(self._update_iface_status)

        self.btn_start_scan.clicked.connect(self._start_scan)
        self.btn_stop_scan.clicked.connect(self._stop_scan)

        self.ap_table.customContextMenuRequested.connect(self._ap_context_menu)
        self.client_table.customContextMenuRequested.connect(self._client_context_menu)
        self.ap_table.itemSelectionChanged.connect(self._on_ap_selected)

        self.btn_capture.clicked.connect(self._capture_handshake)
        self.btn_pmkid.clicked.connect(self._capture_pmkid)
        self.btn_browse_cap.clicked.connect(self._browse_capture)
        self.btn_browse_wl.clicked.connect(self._browse_wordlist)
        self.btn_crack_aircrack.clicked.connect(
            lambda: self._crack("aircrack")
        )
        self.btn_crack_hashcat.clicked.connect(
            lambda: self._crack("hashcat")
        )
        self.btn_crack_smart.clicked.connect(lambda: self._crack("smart"))

        self.btn_airgeddon.clicked.connect(self._launch_airgeddon)
        self.btn_airgeddon_stop.clicked.connect(self._stop_airgeddon)

        self.btn_karma_start.clicked.connect(self._start_karma)
        self.btn_karma_stop.clicked.connect(self._stop_karma)

    # ── Interface Management ──────────────────────────────────────────

    def _refresh_interfaces(self):
        self.iface_combo.blockSignals(True)
        self.iface_combo.clear()
        ifaces = self.orchestrator.wifi_interfaces()
        colors = {
            "monitor": "#ffaa00",
            "managed": "#00ff88",
        }
        for i, ifc in enumerate(ifaces):
            name  = ifc["interface"]
            mode  = ifc.get("mode", "?").lower()
            label = f"{name}  [{mode}]"
            self.iface_combo.addItem(label, name)
            color = colors.get(mode, "#4a6a8a")
            self.iface_combo.setItemData(i, QColor(color), Qt.ForegroundRole)
        self.iface_combo.blockSignals(False)
        if ifaces:
            self._update_iface_status(self.iface_combo.currentText())
        self._load_wordlists()

    def _update_iface_status(self, text: str):
        iface = self.iface_combo.currentData()
        if not iface:
            return
        self.main_window.active_interface = iface
        self.main_window._badge_iface.set_value(iface)
        if "monitor" in text.lower():
            self.lbl_iface_status.setText("● Monitor")
            self.lbl_iface_status.setObjectName("statusWarn")
        else:
            self.lbl_iface_status.setText("● Managed")
            self.lbl_iface_status.setObjectName("statusOk")
        self.lbl_iface_status.style().unpolish(self.lbl_iface_status)
        self.lbl_iface_status.style().polish(self.lbl_iface_status)

    def _show_hw_info(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "No interface selected", "error")
            return
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.audit_wifi_hardware)
        self.worker.finished.connect(self._on_hw_info)
        self.worker.start()

    def _on_hw_info(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            show_toast(self.main_window, f"HW audit failed: {result}", "error")
            return
        lines = ["── Wi-Fi Hardware Audit ──"]
        for iface, data in result.get("adapters", {}).items():
            lines.append(
                f"  {iface}: driver={data.get('driver','?')}  chipset={data.get('chipset','?')}"
            )
            caps = data.get("capabilities", [])
            if caps:
                lines.append(f"    Modes: {', '.join(caps)}")
        self.main_window._append_log("\n".join(lines))

    def _enable_monitor(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "Select an interface first", "error")
            return
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.ensure_monitor_mode, iface)
        self.worker.finished.connect(self._on_monitor_enabled)
        self.worker.start()

    def _on_monitor_enabled(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            show_toast(self.main_window, f"Monitor mode failed: {result}", "error")
        else:
            show_toast(self.main_window, f"Monitor mode: {result}", "success")
            self._refresh_interfaces()

    def _disable_monitor(self):
        iface = self.iface_combo.currentData()
        if not iface:
            return
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.stop_monitor, iface)
        self.worker.finished.connect(lambda _: (
            self.main_window._set_idle(True),
            self._refresh_interfaces(),
        ))
        self.worker.start()

    # ── Recon ─────────────────────────────────────────────────────────

    def _start_scan(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "Select a monitor-mode interface", "error")
            return
        self.btn_start_scan.setEnabled(False)
        self.btn_stop_scan.setEnabled(True)
        self.lbl_stats.setText("Scanning…")
        self.orchestrator.layer.run(f"rm -f /tmp/james_recon*")
        self.recon_proc = self.orchestrator.aircrack.start_airodump(
            iface, write_prefix="/tmp/james_recon"
        )
        self.poll_timer.start(3000)

    def _stop_scan(self):
        self.poll_timer.stop()
        if self.recon_proc:
            try:
                self.orchestrator.layer.kill_background(self.recon_proc)
            except Exception:
                pass
            self.recon_proc = None
        self.btn_start_scan.setEnabled(True)
        self.btn_stop_scan.setEnabled(False)
        self.lbl_stats.setText(
            f"Scan stopped  —  {self.ap_table.rowCount()} APs"
        )

    def _do_poll(self):
        try:
            result = self.orchestrator.layer.run(
                "cat /tmp/james_recon-01.csv 2>/dev/null", timeout=3
            )
            if result.returncode == 0:
                self._parse_airodump_csv(result.stdout)
        except Exception:
            pass

    def _parse_airodump_csv(self, csv_text: str):
        aps: list[dict] = []
        clients: list[dict] = []
        in_clients = False
        for line in csv_text.splitlines():
            line = line.strip()
            if not line:
                in_clients = True
                continue
            if line.startswith("Station MAC"):
                in_clients = True
                continue
            parts = [p.strip() for p in line.split(",")]
            if in_clients:
                if len(parts) >= 6:
                    clients.append(
                        {
                            "mac": parts[0],
                            "bssid": parts[5],
                            "probes": parts[6] if len(parts) > 6 else "",
                            "power": parts[3],
                        }
                    )
            else:
                if len(parts) >= 14 and len(parts[0]) == 17:
                    aps.append(
                        {
                            "bssid": parts[0],
                            "power": parts[8],
                            "channel": parts[3].strip(),
                            "privacy": parts[5].strip(),
                            "essid": parts[13].strip(),
                            "signal": parts[8],
                        }
                    )

        self._populate_ap_table(aps)
        self._populate_client_table(clients)
        self.lbl_stats.setText(
            f"{len(aps)} APs  ·  {len(clients)} clients"
        )
        self.main_window._badge_aps.set_value(str(len(aps)))

    def _populate_ap_table(self, aps: list):
        self.ap_table.setRowCount(0)
        for ap in aps:
            row = self.ap_table.rowCount()
            self.ap_table.insertRow(row)
            values = [
                ap["bssid"], ap["essid"], ap["channel"],
                ap["privacy"], ap["power"], ap["signal"],
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if "OPN" in ap.get("privacy", ""):
                    item.setForeground(QColor("#4a6a8a"))
                self.ap_table.setItem(row, col, item)

    def _populate_client_table(self, clients: list):
        self.client_table.setRowCount(0)
        for c in clients:
            row = self.client_table.rowCount()
            self.client_table.insertRow(row)
            for col, val in enumerate(
                [c["mac"], c["bssid"], c["probes"], c["power"]]
            ):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.client_table.setItem(row, col, item)

    def _on_ap_selected(self):
        row = self.ap_table.currentRow()
        if row < 0:
            return
        self.selected_bssid   = self.ap_table.item(row, 0).text() if self.ap_table.item(row, 0) else ""
        self.selected_essid   = self.ap_table.item(row, 1).text() if self.ap_table.item(row, 1) else ""
        self.selected_channel = self.ap_table.item(row, 2).text() if self.ap_table.item(row, 2) else ""
        self.lbl_target.setText(
            f"{self.selected_essid or '(hidden)'}  ·  {self.selected_bssid}  ·  ch {self.selected_channel}"
        )
        self.lbl_target.setStyleSheet("color: #00e5ff; font-size: 13px; font-weight: 700;")
        self.btn_capture.setEnabled(True)
        self.btn_pmkid.setEnabled(True)
        self.btn_airgeddon.setEnabled(True)
        self.main_window.selected_bssid   = self.selected_bssid
        self.main_window.selected_essid   = self.selected_essid
        self.main_window.selected_channel = self.selected_channel

    def _ap_context_menu(self, pos: QPoint):
        row = self.ap_table.rowAt(pos.y())
        if row < 0:
            return
        bssid   = self.ap_table.item(row, 0).text() if self.ap_table.item(row, 0) else ""
        essid   = self.ap_table.item(row, 1).text() if self.ap_table.item(row, 1) else ""
        channel = self.ap_table.item(row, 2).text() if self.ap_table.item(row, 2) else ""
        menu = QMenu(self)
        menu.addAction(f"Select: {essid or bssid}", lambda: self.ap_table.selectRow(row))
        menu.addSeparator()
        menu.addAction("📋 Copy BSSID", lambda: __import__('PyQt5.QtWidgets', fromlist=['QApplication']).QApplication.clipboard().setText(bssid))
        menu.exec_(self.ap_table.viewport().mapToGlobal(pos))

    def _client_context_menu(self, pos: QPoint):
        row = self.client_table.rowAt(pos.y())
        if row < 0:
            return
        mac = self.client_table.item(row, 0).text() if self.client_table.item(row, 0) else ""
        menu = QMenu(self)
        menu.addAction("📋 Copy MAC", lambda: __import__('PyQt5.QtWidgets', fromlist=['QApplication']).QApplication.clipboard().setText(mac))
        menu.exec_(self.client_table.viewport().mapToGlobal(pos))

    # ── Attack & Crack ────────────────────────────────────────────────

    def _capture_handshake(self):
        if not self.selected_bssid:
            show_toast(self.main_window, "No target selected", "error")
            return
        iface = self.iface_combo.currentData()
        self.main_window._set_idle(False)
        self.main_window._append_log(
            f"📡 Capturing handshake from {self.selected_essid} ({self.selected_bssid})…"
        )
        def _do():
            cap_file = f"/tmp/james_hs_{self.selected_bssid.replace(':','')}"
            self.orchestrator.layer.run(f"rm -f {cap_file}*")
            proc = self.orchestrator.aircrack.start_airodump(
                iface,
                channel=int(self.selected_channel or 1),
                bssid=self.selected_bssid,
                write_prefix=cap_file,
            )
            for _ in range(3):
                self.orchestrator.aircrack.deauth(iface, self.selected_bssid, count=15)
                import time; time.sleep(8)
                if self.orchestrator.aircrack.check_handshake(cap_file + "-01.cap", self.selected_bssid):
                    self.orchestrator.layer.kill_background(proc)
                    return {"found": True, "file": cap_file + "-01.cap"}
            self.orchestrator.layer.kill_background(proc)
            return {"found": False}

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(self._on_capture_done)
        self.worker.start()

    def _on_capture_done(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            show_toast(self.main_window, f"Capture error: {result}", "error")
            return
        if result.get("found"):
            cap_file = result["file"]
            self.lbl_cap_file.setText(cap_file)
            self.lbl_result.setText(f"✅ Handshake captured → {cap_file}")
            self.lbl_result.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: 600;")
            show_toast(self.main_window, "Handshake captured!", "success")
        else:
            show_toast(self.main_window, "No handshake captured", "error")

    def _capture_pmkid(self):
        if not self.selected_bssid:
            show_toast(self.main_window, "No target selected", "error")
            return
        iface = self.iface_combo.currentData()
        self.main_window._set_idle(False)
        self.main_window._append_log(f"⚡ PMKID capture on {self.selected_essid}…")
        pcap = f"/tmp/james_pmkid_{self.selected_bssid.replace(':', '')}.pcapng"
        hc   = pcap.replace(".pcapng", ".hc22000")

        def _do():
            self.orchestrator.hcxtools.capture_pmkid(iface, pcap, timeout=30)
            return self.orchestrator.hcxtools.extract_hashes(pcap, hc)

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(lambda r: self._on_pmkid_done(r, hc))
        self.worker.start()

    def _on_pmkid_done(self, result, hc_path):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            show_toast(self.main_window, f"PMKID error: {result}", "error")
            return
        count = result.get("pmkid_count", 0) + result.get("eapol_count", 0)
        if count:
            self.lbl_cap_file.setText(hc_path)
            self.lbl_result.setText(f"✅ {count} PMKID/EAPOL hash(es) captured")
            self.lbl_result.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: 600;")
            show_toast(self.main_window, f"PMKID captured: {count} hashes", "success")
        else:
            show_toast(self.main_window, "No PMKID from this AP", "error")

    def _browse_capture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Capture File", str(Path.home()), "Captures (*.cap *.pcap *.hc22000);;All (*)"
        )
        if path:
            self.lbl_cap_file.setText(path)

    def _browse_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Wordlist", str(Path.home()), "Wordlists (*.txt *.lst);;All (*)"
        )
        if path:
            self.wl_combo.insertItem(0, path, path)
            self.wl_combo.setCurrentIndex(0)

    def _load_wordlists(self):
        self.wl_combo.clear()
        wl_dir = Path.home() / ".james" / "wordlists"
        if wl_dir.exists():
            for wl in sorted(wl_dir.glob("*.txt")):
                self.wl_combo.addItem(wl.name, str(wl))
        # Common system wordlists
        for p in ["/usr/share/wordlists/rockyou.txt", "/home/malcolm/Desktop/rockyou.txt"]:
            if Path(p).exists():
                self.wl_combo.addItem(Path(p).name, p)

    def _crack(self, engine: str):
        cap_file = self.lbl_cap_file.text()
        wordlist = self.wl_combo.currentData()
        if cap_file == "None" or not cap_file:
            show_toast(self.main_window, "No capture file selected", "error")
            return
        if not wordlist:
            show_toast(self.main_window, "No wordlist selected", "error")
            return
        self.main_window._set_idle(False)
        self.lbl_result.setText("⏳ Cracking…")
        self.lbl_result.setStyleSheet("color: #ffaa00; font-size: 13px; font-weight: 600;")
        bssid = self.selected_bssid or ""
        essid = self.selected_essid or ""

        def _do():
            if engine == "smart":
                return self.orchestrator.crack_wpa_smart(cap_file, wordlist, bssid=bssid, ssid=essid)
            elif engine == "hashcat":
                return self.orchestrator.hashcat.crack(cap_file, wordlist, hash_mode=22000)
            else:
                return self.orchestrator.aircrack.crack(cap_file, wordlist, bssid=bssid)

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(self._on_crack_done)
        self.worker.start()

    def _on_crack_done(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            self.lbl_result.setText(f"❌ Error: {result}")
            self.lbl_result.setStyleSheet("color: #ff4757; font-size: 13px; font-weight: 600;")
            return
        if result.get("found"):
            key = result.get("key", result.get("cracked_keys", [{}])[0].get("plain", "?"))
            self.lbl_result.setText(f"🔑  {key}")
            self.lbl_result.setStyleSheet("color: #00ff88; font-size: 15px; font-weight: 800;")
            show_toast(self.main_window, f"Key cracked: {key}", "success")
            self.main_window._badge_keys.flash()
        else:
            self.lbl_result.setText("🔒  Not in wordlist")
            self.lbl_result.setStyleSheet("color: #ff4757; font-size: 13px; font-weight: 600;")

    def _launch_airgeddon(self):
        show_toast(self.main_window, "Airgeddon tab handles Evil Twin attacks", "info")
        self.main_window.tabs.setCurrentIndex(2)  # Switch to Airgeddon tab

    def _stop_airgeddon(self):
        self.btn_airgeddon.setEnabled(True)
        self.btn_airgeddon_stop.setEnabled(False)

    # ── KARMA ─────────────────────────────────────────────────────────

    def _start_karma(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "Select an interface first", "error")
            return
        self.btn_karma_start.setEnabled(False)
        self.btn_karma_stop.setEnabled(True)
        self.karma_log.clear()
        self.karma_worker = AutoKarmaWorker(
            self.orchestrator,
            ssid=self.txt_ssid.text() or "Free_WiFi",
            portal=self.combo_portal.currentText(),
        )
        self.karma_worker.log_signal.connect(self._karma_log)
        self.karma_worker.status_signal.connect(self._update_karma_stats)
        self.karma_worker.finished_signal.connect(self._on_karma_done)
        self.karma_worker.start()

    def _stop_karma(self):
        if self.karma_worker and self.karma_worker.isRunning():
            self.karma_worker.stop()
        self.btn_karma_stop.setEnabled(False)

    def _karma_log(self, msg: str):
        self.karma_log.appendPlainText(msg)
        self.main_window._append_log(f"[KARMA] {msg}")

    def _update_karma_stats(self, status: dict):
        self._get_karma_val(self._karma_clients_card).setText(
            str(status.get("client_count", 0))
        )
        self._get_karma_val(self._karma_dns_card).setText(
            str(status.get("dns_count", 0))
        )
        cred_count = status.get("cred_count", 0)
        self._get_karma_val(self._karma_creds_card).setText(str(cred_count))

        # Populate tables
        self.karma_clients_tbl.setRowCount(0)
        for c in status.get("clients", []):
            row = self.karma_clients_tbl.rowCount()
            self.karma_clients_tbl.insertRow(row)
            self.karma_clients_tbl.setItem(row, 0, QTableWidgetItem(c.get("ip", "")))
            self.karma_clients_tbl.setItem(row, 1, QTableWidgetItem(c.get("mac", "")))

        self.karma_creds_tbl.setRowCount(0)
        for cred in status.get("creds", []):
            row = self.karma_creds_tbl.rowCount()
            self.karma_creds_tbl.insertRow(row)
            self.karma_creds_tbl.setItem(row, 0, QTableWidgetItem(cred.get("ip", "")))
            self.karma_creds_tbl.setItem(row, 1, QTableWidgetItem(str(cred.get("password", ""))))

    def _on_karma_done(self, success: bool):
        self.btn_karma_start.setEnabled(True)
        self.btn_karma_stop.setEnabled(False)
        status = "✅ Complete" if success else "❌ Failed / Aborted"
        self._karma_log(f"Campaign {status}")
