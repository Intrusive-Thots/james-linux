"""JAMES — Wi-Fi Arsenal Tab (Design System v3)."""

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
    QShortcut,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QFont, QKeySequence
import time
import logging

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread
from james.gui.theme import LOG_STYLE, METRIC_CARD_STYLE, SURFACE_CARD_STYLE

logger = logging.getLogger(__name__)


def _vsep() -> QFrame:
    f = QFrame()
    f.setObjectName("vline")
    f.setFrameShape(QFrame.VLine)
    return f


def _hsep() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    f.setFrameShape(QFrame.HLine)
    return f


# ── AutoKarmaWorker ────────────────────────────────────────────────────
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
            self.log_signal.emit(f"KARMA crashed: {e}")
            self._safe_cleanup()
            self.finished_signal.emit(False)

    def stop(self):
        self.is_running = False

    def _log(self, msg):
        self.log_signal.emit(msg)

    def _aborted(self):
        if not self.is_running:
            self._log("Aborted by user.")
            return True
        return False

    def _safe_cleanup(self):
        try:
            self.pineap.stop_all()
        except Exception:
            pass

    def _do_workflow(self):
        self.phase_signal.emit(1, "Interface Setup")
        ifaces = self.orchestrator.wifi_interfaces()
        if not ifaces:
            self._log("No wireless interfaces detected.")
            self.finished_signal.emit(False)
            return
        mon_iface = next(
            (
                i["interface"]
                for i in ifaces
                if self.orchestrator.net_guard.check_monitor_safe(
                    i["interface"]
                )[0]
            ),
            None,
        )
        if not mon_iface:
            self._log("No safe interface available.")
            self.finished_signal.emit(False)
            return

        self.phase_signal.emit(2, "Harvesting Probes")
        try:
            probes = self.pineap.harvest_probes(
                mon_iface, duration=self.probe_duration
            )
            self._log(f"Captured {probes.get('count', 0)} probe frames.")
        except Exception as e:
            self._log(f"Probe harvest error: {e}")

        if self._aborted():
            self.finished_signal.emit(False)
            return

        self.phase_signal.emit(3, "Launching KARMA AP")
        try:
            result = self.pineap.start_karma_with_portal(
                interface=mon_iface, ssid=self.ssid, portal=self.portal
            )
            self._log(f"KARMA active: {result.get('status')}")
        except Exception as e:
            self._log(f"KARMA start error: {e}")
            self._safe_cleanup()
            self.finished_signal.emit(False)
            return

        self.phase_signal.emit(4, "Monitoring for Credentials")
        deadline = time.time() + self.monitor_duration
        while time.time() < deadline and not self._aborted():
            time.sleep(5)
            try:
                self.status_signal.emit(self.pineap.get_live_status())
            except Exception:
                pass

        self.phase_signal.emit(5, "Cleanup")
        self._safe_cleanup()
        self._log("KARMA campaign complete.")
        self.finished_signal.emit(True)


# ── WiFiArsenalTab ─────────────────────────────────────────────────────
class WiFiArsenalTab(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self.pineap = self.orchestrator.pineap
        self.worker = None
        self.karma_worker = None
        self.recon_proc = None

        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()
        self._build_shortcuts()

    # ── Shortcuts ─────────────────────────────────────────────────────

    def _build_shortcuts(self):
        """Build keyboard shortcuts for the Wi-Fi Arsenal tab."""
        # Refresh Interfaces
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(
            self.btn_refresh.click
        )

        # Toggle Scan
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            self._toggle_scan
        )

        # Toggle Monitor Mode
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(
            self._toggle_monitor
        )

        # Copy Selected AP BSSID or Client MAC (only when tables are focused to avoid blocking global copy)
        ap_copy = QShortcut(QKeySequence("Ctrl+C"), self.ap_table)
        ap_copy.setContext(Qt.WidgetShortcut)
        ap_copy.activated.connect(self._copy_selected)

        client_copy = QShortcut(QKeySequence("Ctrl+C"), self.client_table)
        client_copy.setContext(Qt.WidgetShortcut)
        client_copy.activated.connect(self._copy_selected)

    def _toggle_scan(self):
        if self.btn_start_scan.isEnabled():
            self.btn_start_scan.click()
        elif self.btn_stop_scan.isEnabled():
            self.btn_stop_scan.click()

    def _toggle_monitor(self):
        iface = self.iface_combo.currentData()
        if not iface:
            return
        # A simple toggle: if it ends with 'mon', disable, else enable.
        if iface.endswith("mon"):
            self.btn_monitor_off.click()
        else:
            self.btn_monitor_on.click()

    def _copy_selected(self):
        # Check if ap_table has focus or selection
        if self.ap_table.hasFocus():
            row = self.ap_table.currentRow()
            if row >= 0:
                bssid = (
                    self.ap_table.item(row, 0) or QTableWidgetItem("")
                ).text()
                if bssid:
                    QApplication.clipboard().setText(bssid)
                    show_toast(self.main_window, "BSSID copied", "info")
            return

        # Check if client_table has focus or selection
        if self.client_table.hasFocus():
            row = self.client_table.currentRow()
            if row >= 0:
                mac = (
                    self.client_table.item(row, 0) or QTableWidgetItem("")
                ).text()
                if mac:
                    QApplication.clipboard().setText(mac)
                    show_toast(self.main_window, "Client MAC copied", "info")
            return

    # ── Build ─────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        # Interface row — flat, no card frame
        layout.addWidget(self._build_interface_row())
        layout.addWidget(_hsep())

        # Sub-tabs
        self.inner_tabs = QTabWidget()
        self.inner_tabs.setDocumentMode(True)
        self.inner_tabs.addTab(self._build_recon_tab(), "Recon")
        self.inner_tabs.addTab(self._build_attack_tab(), "Attack & Crack")
        self.inner_tabs.addTab(self._build_karma_tab(), "Rogue AP")
        layout.addWidget(self.inner_tabs)

        # Timers
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._do_poll)
        QTimer.singleShot(400, self._refresh_interfaces)

    # ─── Interface row ────────────────────────────────────────────────

    def _build_interface_row(self) -> QWidget:
        row = QWidget()
        row.setFixedHeight(48)
        row.setStyleSheet("background: #181818;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        iface_lbl = QLabel("Interface")
        iface_lbl.setObjectName("metaLabel")
        iface_lbl.setFixedWidth(60)

        self.iface_combo = QComboBox()
        self.iface_combo.setFixedWidth(180)
        self.iface_combo.setToolTip("Active wireless interface")

        self.lbl_iface_status = QLabel("● —")
        self.lbl_iface_status.setObjectName("dimLabel")
        self.lbl_iface_status.setFixedWidth(80)

        layout.addWidget(iface_lbl)
        layout.addWidget(self.iface_combo)
        layout.addWidget(self.lbl_iface_status)
        layout.addWidget(_vsep())

        self.btn_refresh = QPushButton("↻  Refresh")
        self.btn_refresh.setMinimumWidth(88)
        self.btn_refresh.setToolTip("Refresh network interfaces (Ctrl+R)")
        self.btn_hw_info = QPushButton("HW Info")
        self.btn_hw_info.setMinimumWidth(76)
        self.btn_monitor_on = QPushButton("▶ Mon ON")
        self.btn_monitor_on.setObjectName("successBtn")
        self.btn_monitor_on.setMinimumWidth(88)
        self.btn_monitor_on.setToolTip(
            "Enable monitor mode on the selected interface (Ctrl+M)"
        )
        self.btn_monitor_off = QPushButton("■ Mon OFF")
        self.btn_monitor_off.setObjectName("warnBtn")
        self.btn_monitor_off.setMinimumWidth(88)
        self.btn_monitor_off.setToolTip(
            "Disable monitor mode on the selected interface (Ctrl+M)"
        )

        for btn in (
            self.btn_refresh,
            self.btn_hw_info,
            self.btn_monitor_on,
            self.btn_monitor_off,
        ):
            btn.setFixedHeight(32)
            layout.addWidget(btn)

        layout.addStretch()
        return row

    # ─── Recon tab ────────────────────────────────────────────────────

    def _build_recon_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Primary action — gold, dominant
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_start_scan = QPushButton("  START SCAN  ")
        self.btn_start_scan.setObjectName("primaryBtn")
        self.btn_start_scan.setMinimumWidth(220)
        self.btn_start_scan.setToolTip(
            "Scan for nearby Wi-Fi networks (Ctrl+S)"
        )

        self.btn_stop_scan = QPushButton("Stop")
        self.btn_stop_scan.setObjectName("secondaryBtn")
        self.btn_stop_scan.setMinimumWidth(80)
        self.btn_stop_scan.setEnabled(False)
        self.btn_stop_scan.setToolTip("Stop ongoing Wi-Fi scan (Ctrl+S)")

        action_row.addWidget(self.btn_start_scan)
        action_row.addWidget(self.btn_stop_scan)
        action_row.addStretch()
        layout.addLayout(action_row)

        # Metrics strip — compact, always visible
        layout.addWidget(self._build_metrics_strip())

        # AP + Client tables in splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)

        ap_group = QGroupBox("Access Points")
        ap_layout = QVBoxLayout(ap_group)
        ap_layout.setContentsMargins(8, 8, 8, 8)
        self.ap_table = QTableWidget()
        self.ap_table.setColumnCount(6)
        self.ap_table.setHorizontalHeaderLabels(
            ["BSSID", "ESSID", "CH", "ENC", "PWR", "SIG"]
        )
        self.ap_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.ap_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ap_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ap_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ap_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ap_table.setAlternatingRowColors(True)
        self.ap_table.verticalHeader().setVisible(False)
        ap_layout.addWidget(self.ap_table)
        splitter.addWidget(ap_group)

        cl_group = QGroupBox("Clients & Probes")
        cl_layout = QVBoxLayout(cl_group)
        cl_layout.setContentsMargins(8, 8, 8, 8)
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(
            ["MAC", "Associated AP", "Probed SSIDs", "PWR"]
        )
        self.client_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
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

    def _build_metrics_strip(self) -> QWidget:
        """Compact horizontal metrics row: APs | Clients | Channel | Status."""
        strip = QWidget()
        strip.setFixedHeight(40)
        strip.setStyleSheet(METRIC_CARD_STYLE + " border-radius: 6px;")
        row = QHBoxLayout(strip)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(24)

        self._m_aps = self._make_metric("APs", "0")
        self._m_clients = self._make_metric("Clients", "0")
        self._m_chan = self._make_metric("Channel", "—")
        self._m_status = self._make_metric("Status", "Ready")

        for m in (self._m_aps, self._m_clients, self._m_chan, self._m_status):
            row.addWidget(m)
        row.addStretch()
        return strip

    def _make_metric(self, label: str, value: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName("metaLabel")
        val = QLabel(value)
        val.setStyleSheet("color: #CCCCCC; font-size: 14px; font-weight: 600;")
        val.setObjectName(f"_metric_{label.lower().replace(' ', '_')}")
        h.addWidget(lbl)
        h.addWidget(val)
        return w

    def _set_metric(self, widget: QWidget, value: str, color: str = "#CCCCCC"):
        lbl = widget.findChildren(QLabel)[1]
        lbl.setText(value)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 600;"
        )

    # ─── Attack tab ───────────────────────────────────────────────────

    def _build_attack_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Target info — single compact row
        target_row = QWidget()
        target_row.setFixedHeight(44)
        target_row.setStyleSheet(METRIC_CARD_STYLE + " border-radius: 6px;")
        tr = QHBoxLayout(target_row)
        tr.setContentsMargins(16, 0, 16, 0)
        tr.setSpacing(12)

        target_cap = QLabel("TARGET")
        target_cap.setObjectName("metaLabel")
        target_cap.setFixedWidth(52)
        self.lbl_target = QLabel("None selected — right-click an AP in Recon")
        self.lbl_target.setObjectName("dimLabel")

        tr.addWidget(target_cap)
        tr.addWidget(self.lbl_target, stretch=1)
        layout.addWidget(target_row)

        # 1. Capture
        cap_group = QGroupBox("1 · Capture")
        cap_layout = QHBoxLayout(cap_group)
        cap_layout.setSpacing(8)
        self.btn_capture = QPushButton("Capture Handshake")
        self.btn_capture.setObjectName("secondaryBtn")
        self.btn_capture.setEnabled(False)
        self.btn_pmkid = QPushButton("Capture PMKID")
        self.btn_pmkid.setObjectName("secondaryBtn")
        self.btn_pmkid.setEnabled(False)
        cap_layout.addWidget(self.btn_capture)
        cap_layout.addWidget(self.btn_pmkid)
        cap_layout.addStretch()
        layout.addWidget(cap_group)

        # 2. Evil Twin
        et_group = QGroupBox("2 · Evil Twin Pipeline")
        et_layout = QHBoxLayout(et_group)
        et_layout.setSpacing(8)
        self.btn_airgeddon = QPushButton("Launch Airgeddon Evil Twin")
        self.btn_airgeddon.setObjectName("dangerBtn")
        self.btn_airgeddon.setFixedHeight(36)
        self.btn_airgeddon.setEnabled(False)
        self.btn_airgeddon.setToolTip("Launch Evil Twin attack pipeline")
        self.btn_airgeddon_stop = QPushButton("Stop")
        self.btn_airgeddon_stop.setObjectName("warnBtn")
        self.btn_airgeddon_stop.setMinimumWidth(80)
        self.btn_airgeddon_stop.setEnabled(False)
        self.btn_airgeddon_stop.setToolTip("Stop Evil Twin pipeline")
        et_layout.addWidget(self.btn_airgeddon, stretch=2)
        et_layout.addWidget(self.btn_airgeddon_stop)
        layout.addWidget(et_group)

        # 3. Crack
        crack_group = QGroupBox("3 · Dictionary Attack")
        crack_layout = QVBoxLayout(crack_group)
        crack_layout.setSpacing(8)

        # File selectors
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        cap_lbl = QLabel("Capture")
        cap_lbl.setObjectName("dimLabel")
        cap_lbl.setMinimumWidth(52)
        self.lbl_cap_file = QLabel("None")
        self.lbl_cap_file.setStyleSheet("color: #CCCCCC; font-size: 14px;")
        self.btn_browse_cap = QPushButton("Browse")
        self.btn_browse_cap.setMinimumWidth(80)

        wl_lbl = QLabel("Wordlist")
        wl_lbl.setObjectName("dimLabel")
        wl_lbl.setMinimumWidth(56)
        self.wl_combo = QComboBox()
        self.wl_combo.setMinimumWidth(160)
        self.btn_browse_wl = QPushButton("Custom")
        self.btn_browse_wl.setMinimumWidth(80)

        file_row.addWidget(cap_lbl)
        file_row.addWidget(self.lbl_cap_file, stretch=1)
        file_row.addWidget(self.btn_browse_cap)
        file_row.addWidget(_vsep())
        file_row.addWidget(wl_lbl)
        file_row.addWidget(self.wl_combo)
        file_row.addWidget(self.btn_browse_wl)
        crack_layout.addLayout(file_row)

        # Engine buttons — primary is Smart
        engine_row = QHBoxLayout()
        engine_row.setSpacing(8)
        self.btn_crack_smart = QPushButton("  Run Smart Crack  ")
        self.btn_crack_smart.setObjectName("primaryBtn")
        self.btn_crack_aircrack = QPushButton("Aircrack-ng")
        self.btn_crack_aircrack.setObjectName("secondaryBtn")
        self.btn_crack_hashcat = QPushButton("Hashcat")
        self.btn_crack_hashcat.setObjectName("secondaryBtn")
        engine_row.addWidget(self.btn_crack_smart)
        engine_row.addWidget(self.btn_crack_aircrack)
        engine_row.addWidget(self.btn_crack_hashcat)
        engine_row.addStretch()
        crack_layout.addLayout(engine_row)
        layout.addWidget(crack_group)

        # Result display
        result_row = QWidget()
        result_row.setFixedHeight(40)
        result_row.setStyleSheet(METRIC_CARD_STYLE + " border-radius: 6px;")
        rr = QHBoxLayout(result_row)
        rr.setContentsMargins(16, 0, 16, 0)
        rr.setSpacing(12)
        res_cap = QLabel("RESULT")
        res_cap.setObjectName("metaLabel")
        res_cap.setFixedWidth(52)
        self.lbl_result = QLabel("Ready")
        self.lbl_result.setObjectName("dimLabel")
        rr.addWidget(res_cap)
        rr.addWidget(self.lbl_result, stretch=1)
        layout.addWidget(result_row)

        layout.addStretch()
        return tab

    # ─── Rogue AP tab ─────────────────────────────────────────────────

    def _build_karma_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Config
        cfg_group = QGroupBox("Campaign Configuration")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(8)

        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(8)
        ssid_lbl = QLabel("SSID")
        ssid_lbl.setObjectName("dimLabel")
        ssid_lbl.setMinimumWidth(40)
        self.txt_ssid = QLineEdit("Free_WiFi")
        self.txt_ssid.setMinimumWidth(160)
        portal_lbl = QLabel("Portal")
        portal_lbl.setObjectName("dimLabel")
        portal_lbl.setMinimumWidth(40)
        self.combo_portal = QComboBox()
        self.combo_portal.addItems(
            ["wifi_login", "hotel_login", "social_login"]
        )
        self.combo_portal.setMinimumWidth(130)
        cfg_row.addWidget(ssid_lbl)
        cfg_row.addWidget(self.txt_ssid)
        cfg_row.addWidget(_vsep())
        cfg_row.addWidget(portal_lbl)
        cfg_row.addWidget(self.combo_portal)
        cfg_row.addStretch()
        cfg_layout.addLayout(cfg_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        self.btn_karma_start = QPushButton("  START KARMA CAMPAIGN  ")
        self.btn_karma_start.setObjectName("primaryBtn")
        self.btn_karma_stop = QPushButton("Stop")
        self.btn_karma_stop.setObjectName("dangerBtn")
        self.btn_karma_stop.setMinimumWidth(80)
        self.btn_karma_stop.setEnabled(False)
        ctrl_row.addWidget(self.btn_karma_start)
        ctrl_row.addWidget(self.btn_karma_stop)
        ctrl_row.addStretch()
        cfg_layout.addLayout(ctrl_row)
        layout.addWidget(cfg_group)

        # Live stats — 3 compact metric cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._k_clients = self._make_kpi("Clients", "0", "#4daafc")
        self._k_dns = self._make_kpi("DNS Queries", "0", "#6E7681")
        self._k_creds = self._make_kpi("Credentials", "0", "#2EA043")
        for k in (self._k_clients, self._k_dns, self._k_creds):
            stats_row.addWidget(k)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Dashboard
        dash_group = QGroupBox("Live Dashboard")
        dash_layout = QVBoxLayout(dash_group)
        tbl_split = QSplitter(Qt.Horizontal)
        tbl_split.setHandleWidth(1)

        self.karma_clients_tbl = QTableWidget(0, 2)
        self.karma_clients_tbl.setHorizontalHeaderLabels(["Client IP", "MAC"])
        self.karma_clients_tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.karma_clients_tbl.verticalHeader().setVisible(False)

        self.karma_creds_tbl = QTableWidget(0, 2)
        self.karma_creds_tbl.setHorizontalHeaderLabels(
            ["IP", "Captured Payload"]
        )
        self.karma_creds_tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.karma_creds_tbl.verticalHeader().setVisible(False)

        tbl_split.addWidget(self.karma_clients_tbl)
        tbl_split.addWidget(self.karma_creds_tbl)
        dash_layout.addWidget(tbl_split)
        layout.addWidget(dash_group)

        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)
        self.karma_log = QPlainTextEdit()
        self.karma_log.setReadOnly(True)
        self.karma_log.setMaximumHeight(120)
        self.karma_log.setStyleSheet(LOG_STYLE)
        self.karma_log.setFont(QFont("JetBrains Mono", 13))
        log_layout.addWidget(self.karma_log)
        layout.addWidget(log_group)
        return tab

    def _make_kpi(self, label: str, value: str, color: str) -> QWidget:
        card = QWidget()
        card.setFixedHeight(56)
        card.setFixedWidth(140)
        card.setStyleSheet(METRIC_CARD_STYLE + " border-radius: 6px;")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(2)
        val = QLabel(value)
        val.setAlignment(Qt.AlignLeft)
        val.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700;"
            f" font-family: 'JetBrains Mono', monospace; border: none;"
        )
        cap = QLabel(label)
        cap.setObjectName("metaLabel")
        v.addWidget(val)
        v.addWidget(cap)
        return card

    def _get_kpi_val(self, card: QWidget) -> QLabel:
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
        self.client_table.customContextMenuRequested.connect(
            self._client_context_menu
        )
        self.ap_table.itemSelectionChanged.connect(self._on_ap_selected)

        self.btn_capture.clicked.connect(self._capture_handshake)
        self.btn_pmkid.clicked.connect(self._capture_pmkid)
        self.btn_browse_cap.clicked.connect(self._browse_capture)
        self.btn_browse_wl.clicked.connect(self._browse_wordlist)
        self.btn_crack_aircrack.clicked.connect(
            lambda: self._crack("aircrack")
        )
        self.btn_crack_hashcat.clicked.connect(lambda: self._crack("hashcat"))
        self.btn_crack_smart.clicked.connect(lambda: self._crack("smart"))
        self.btn_airgeddon.clicked.connect(self._launch_airgeddon)
        self.btn_airgeddon_stop.clicked.connect(self._stop_airgeddon)

        self.btn_karma_start.clicked.connect(self._start_karma)
        self.btn_karma_stop.clicked.connect(self._stop_karma)

    # ── Interface ─────────────────────────────────────────────────────

    def _refresh_interfaces(self):
        self.iface_combo.blockSignals(True)
        self.iface_combo.clear()
        ifaces = self.orchestrator.wifi_interfaces()
        for i, ifc in enumerate(ifaces):
            name = ifc["interface"]
            mode = ifc.get("mode", "?").lower()
            self.iface_combo.addItem(f"{name}  [{mode}]", name)
            color = "#BB8009" if mode == "monitor" else "#2EA043"
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
            return
        for iface, data in result.get("adapters", {}).items():
            self.main_window._append_log(
                f"{iface}: driver={data.get('driver','?')}  "
                f"chipset={data.get('chipset','?')}  "
                f"modes={', '.join(data.get('capabilities', []))}",
                "INFO",
            )

    def _enable_monitor(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "Select an interface first", "error")
            return
        self.main_window._set_idle(False)
        self.worker = WorkerThread(
            self.orchestrator.ensure_monitor_mode, iface
        )
        self.worker.finished.connect(self._on_monitor_enabled)
        self.worker.start()

    def _on_monitor_enabled(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            show_toast(
                self.main_window, f"Monitor mode failed: {result}", "error"
            )
        else:
            show_toast(self.main_window, f"Monitor: {result}", "success")
            self._refresh_interfaces()

    def _disable_monitor(self):
        iface = self.iface_combo.currentData()
        if not iface:
            return
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.stop_monitor, iface)
        self.worker.finished.connect(
            lambda _: (
                self.main_window._set_idle(True),
                self._refresh_interfaces(),
            )
        )
        self.worker.start()

    # ── Recon ─────────────────────────────────────────────────────────

    def _start_scan(self):
        iface = self.iface_combo.currentData()
        if not iface:
            show_toast(self.main_window, "Select an interface", "error")
            return
        self.btn_start_scan.setEnabled(False)
        self.btn_stop_scan.setEnabled(True)
        self._set_metric(self._m_status, "Scanning…", "#0078D4")
        self.orchestrator.layer.run("rm -f /tmp/james_recon*")
        self.recon_proc = self.orchestrator.aircrack.start_airodump(
            iface, write_prefix="/tmp/james_recon"
        )
        self.poll_timer.start(3000)
        self.main_window._append_log(f"Scan started on {iface}", "INFO")

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
        n = self.ap_table.rowCount()
        self._set_metric(self._m_status, f"Stopped  ({n} APs)")
        self.main_window._append_log(f"Scan stopped — {n} APs found", "INFO")

    def _do_poll(self):
        try:
            r = self.orchestrator.layer.run(
                "cat /tmp/james_recon-01.csv 2>/dev/null", timeout=3
            )
            if r.returncode == 0:
                self._parse_airodump_csv(r.stdout)
        except Exception:
            pass

    def _parse_airodump_csv(self, csv_text: str):
        aps, clients = [], []
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

        # Update metrics
        self._set_metric(self._m_aps, str(len(aps)))
        self._set_metric(self._m_clients, str(len(clients)))
        chans = sorted({a["channel"] for a in aps if a["channel"].isdigit()})
        self._set_metric(self._m_chan, ", ".join(chans[:4]) or "—")
        self._set_metric(self._m_status, "Live", "#2EA043")

        # Update header
        self.main_window.set_ap_count(len(aps))

    def _populate_ap_table(self, aps: list):
        self.ap_table.setRowCount(0)
        for ap in aps:
            row = self.ap_table.rowCount()
            self.ap_table.insertRow(row)
            values = [
                ap["bssid"],
                ap["essid"],
                ap["channel"],
                ap["privacy"],
                ap["power"],
                ap["signal"],
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if "OPN" in ap.get("privacy", ""):
                    item.setForeground(QColor("#3C3C3C"))
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

        def cell(c):
            return (self.ap_table.item(row, c) or QTableWidgetItem("")).text()

        self.selected_bssid = cell(0)
        self.selected_essid = cell(1)
        self.selected_channel = cell(2)
        self.lbl_target.setText(
            f"{self.selected_essid or '(hidden)'}  ·  {self.selected_bssid}  ·  ch {self.selected_channel}"
        )
        self.lbl_target.setStyleSheet(
            "color: #0078D4; font-size: 14px; font-weight: 600;"
        )
        self.btn_capture.setEnabled(True)
        self.btn_pmkid.setEnabled(True)
        self.btn_airgeddon.setEnabled(True)
        self.main_window.selected_bssid = self.selected_bssid
        self.main_window.selected_essid = self.selected_essid
        self.main_window.selected_channel = self.selected_channel

    def _ap_context_menu(self, pos: QPoint):
        row = self.ap_table.rowAt(pos.y())
        if row < 0:
            return
        bssid = (self.ap_table.item(row, 0) or QTableWidgetItem("")).text()
        essid = (self.ap_table.item(row, 1) or QTableWidgetItem("")).text()
        menu = QMenu(self)
        menu.addAction(
            f"Select: {essid or bssid}", lambda: self.ap_table.selectRow(row)
        )
        menu.addAction(
            "Copy BSSID",
            lambda: (
                __import__("PyQt5.QtWidgets", fromlist=["QApplication"])
                .QApplication.clipboard()
                .setText(bssid)
            ),
        )
        menu.exec_(self.ap_table.viewport().mapToGlobal(pos))

    def _client_context_menu(self, pos: QPoint):
        row = self.client_table.rowAt(pos.y())
        if row < 0:
            return
        mac = (self.client_table.item(row, 0) or QTableWidgetItem("")).text()
        menu = QMenu(self)
        menu.addAction(
            "Copy MAC",
            lambda: (
                __import__("PyQt5.QtWidgets", fromlist=["QApplication"])
                .QApplication.clipboard()
                .setText(mac)
            ),
        )
        menu.exec_(self.client_table.viewport().mapToGlobal(pos))

    # ── Attack ────────────────────────────────────────────────────────

    def _capture_handshake(self):
        if not self.selected_bssid:
            show_toast(self.main_window, "No target selected", "error")
            return
        iface = self.iface_combo.currentData()
        self.main_window._set_idle(False)
        self.main_window._append_log(
            f"Capturing handshake from {self.selected_essid} ({self.selected_bssid})",
            "INFO",
        )
        bssid = self.selected_bssid
        essid = self.selected_essid
        channel = self.selected_channel

        def _do():
            cap = f"/tmp/james_hs_{bssid.replace(':','')}"
            self.orchestrator.layer.run(f"rm -f {cap}*")
            proc = self.orchestrator.aircrack.start_airodump(
                iface, channel=int(channel or 1), bssid=bssid, write_prefix=cap
            )
            for _ in range(3):
                self.orchestrator.aircrack.deauth(iface, bssid, count=15)
                import time

                time.sleep(8)
                if self.orchestrator.aircrack.check_handshake(
                    cap + "-01.cap", bssid
                ):
                    self.orchestrator.layer.kill_background(proc)
                    return {"found": True, "file": cap + "-01.cap"}
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
            f = result["file"]
            self.lbl_cap_file.setText(f)
            self.lbl_result.setText(f"Handshake captured → {f}")
            self.lbl_result.setStyleSheet(
                "color: #2EA043; font-size: 14px; font-weight: 600;"
            )
            show_toast(self.main_window, "Handshake captured", "success")
        else:
            show_toast(self.main_window, "No handshake captured", "error")

    def _capture_pmkid(self):
        if not self.selected_bssid:
            show_toast(self.main_window, "No target selected", "error")
            return
        iface = self.iface_combo.currentData()
        bssid = self.selected_bssid
        pcap = f"/tmp/james_pmkid_{bssid.replace(':', '')}.pcapng"
        hc = pcap.replace(".pcapng", ".hc22000")
        self.main_window._set_idle(False)

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
            self.lbl_result.setText(f"{count} PMKID/EAPOL hash(es)")
            self.lbl_result.setStyleSheet(
                "color: #2EA043; font-size: 14px; font-weight: 600;"
            )
            show_toast(self.main_window, f"PMKID: {count} hashes", "success")
        else:
            show_toast(self.main_window, "No PMKID from this AP", "error")

    def _browse_capture(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Capture File",
            str(Path.home()),
            "Captures (*.cap *.pcap *.hc22000);;All (*)",
        )
        if path:
            self.lbl_cap_file.setText(path)

    def _browse_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wordlist",
            str(Path.home()),
            "Wordlists (*.txt *.lst);;All (*)",
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
        for p in [
            "/usr/share/wordlists/rockyou.txt",
            str(Path.home() / "Desktop" / "rockyou.txt"),
        ]:
            if Path(p).exists():
                self.wl_combo.addItem(Path(p).name, p)

    def _crack(self, engine: str):
        cap_file = self.lbl_cap_file.text()
        wordlist = self.wl_combo.currentData()
        if cap_file == "None" or not cap_file:
            show_toast(self.main_window, "No capture file", "error")
            return
        if not wordlist:
            show_toast(self.main_window, "No wordlist selected", "error")
            return
        self.main_window._set_idle(False)
        self.lbl_result.setText("Cracking…")
        self.lbl_result.setStyleSheet(
            "color: #BB8009; font-size: 14px; font-weight: 600;"
        )
        bssid = self.selected_bssid or ""
        essid = self.selected_essid or ""

        def _do():
            if engine == "smart":
                return self.orchestrator.crack_wpa_smart(
                    cap_file, wordlist, bssid=bssid, ssid=essid
                )
            elif engine == "hashcat":
                return self.orchestrator.hashcat.crack(
                    cap_file, wordlist, hash_mode=22000
                )
            else:
                return self.orchestrator.aircrack.crack(
                    cap_file, wordlist, bssid=bssid
                )

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(self._on_crack_done)
        self.worker.start()

    def _on_crack_done(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            self.lbl_result.setText(f"Error: {result}")
            self.lbl_result.setStyleSheet("color: #F85149; font-size: 14px;")
            return
        if result.get("found"):
            key = result.get("key", "?")
            self.lbl_result.setText(f"KEY FOUND:  {key}")
            self.lbl_result.setStyleSheet(
                "color: #0078D4; font-size: 16px; font-weight: 700;"
                " font-family: 'JetBrains Mono', monospace;"
            )
            show_toast(self.main_window, f"Cracked: {key}", "success")
            self.main_window._append_log(f"Key cracked: {key}", "OK")
        else:
            self.lbl_result.setText("Not in wordlist")
            self.lbl_result.setStyleSheet("color: #F85149; font-size: 14px;")

    def _launch_airgeddon(self):
        self.main_window.tabs.setCurrentIndex(2)

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
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M")
        self.karma_log.appendPlainText(f"[{ts}]  {msg}")
        self.main_window._append_log(f"[KARMA] {msg}", "INFO")

    def _update_karma_stats(self, status: dict):
        self._get_kpi_val(self._k_clients).setText(
            str(status.get("client_count", 0))
        )
        self._get_kpi_val(self._k_dns).setText(str(status.get("dns_count", 0)))
        self._get_kpi_val(self._k_creds).setText(
            str(status.get("cred_count", 0))
        )

        self.karma_clients_tbl.setRowCount(0)
        for c in status.get("clients", []):
            row = self.karma_clients_tbl.rowCount()
            self.karma_clients_tbl.insertRow(row)
            self.karma_clients_tbl.setItem(
                row, 0, QTableWidgetItem(c.get("ip", ""))
            )
            self.karma_clients_tbl.setItem(
                row, 1, QTableWidgetItem(c.get("mac", ""))
            )

        self.karma_creds_tbl.setRowCount(0)
        for cred in status.get("creds", []):
            row = self.karma_creds_tbl.rowCount()
            self.karma_creds_tbl.insertRow(row)
            self.karma_creds_tbl.setItem(
                row, 0, QTableWidgetItem(cred.get("ip", ""))
            )
            self.karma_creds_tbl.setItem(
                row, 1, QTableWidgetItem(str(cred.get("password", "")))
            )

    def _on_karma_done(self, success: bool):
        self.btn_karma_start.setEnabled(True)
        self.btn_karma_stop.setEnabled(False)
        self._karma_log(
            "Campaign complete" if success else "Campaign failed/aborted"
        )
