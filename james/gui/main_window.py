"""JAMES — Main Window v3 (Design System v3)."""

from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QPlainTextEdit, QProgressBar,
    QMessageBox, QSplitter, QStatusBar, QTabWidget,
    QDialog, QTextEdit, QDialogButtonBox, QComboBox,
    QFrame, QSizePolicy, QShortcut,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QKeySequence
import logging

from james.core.orchestrator import Orchestrator
from james.gui.theme import (
    DARK_STYLESHEET, TERMINAL_STYLE, LOG_STYLE,
    HEADER_STYLE, SESSION_STRIP_STYLE,
)
from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread
from james.gui.tabs.wifi_tab import WiFiArsenalTab
from james.gui.tabs.autopilot_tab import AutoPilotTab
from james.gui.tabs.setup_tab import SetupTab
from james.gui.tabs.troubleshoot_tab import TroubleshootTab
from james.gui.tabs.airgeddon_tab import AirgeddonTab

logger = logging.getLogger(__name__)

# Log severity prefixes for timestamped entries
_SEV = {
    "INFO": "INFO ",
    "WARN": "WARN ",
    "CRIT": "CRIT ",
    "OK":   "OK   ",
}


def _sep_v() -> QFrame:
    f = QFrame()
    f.setObjectName("vline")
    f.setFrameShape(QFrame.VLine)
    return f


def _sep_h() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    f.setFrameShape(QFrame.HLine)
    return f


class MainWindow(QMainWindow):
    """JAMES main window — Design System v3."""

    progress_signal = pyqtSignal(str, int, int)
    log_signal      = pyqtSignal(str, str)   # (message, severity)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None

        self.setWindowTitle("JAMES")
        self.setMinimumSize(1080, 760)
        self.resize(1320, 900)
        self.setStyleSheet(DARK_STYLESHEET)

        # Shared state
        self.active_interface  = None
        self.selected_bssid    = None
        self.selected_essid    = None
        self.selected_channel  = None
        self._log_count        = 0
        self._ap_count         = 0
        self._key_count        = 0
        self._last_action      = "—"
        self._current_mode     = "IDLE"
        self.uptime_seconds    = 0

        self._build_ui()
        self._connect_signals()
        self._build_shortcuts()

        self.orchestrator.on_print    = lambda t: self._append_log(t, "INFO")
        self.orchestrator.on_progress = self._on_orchestrator_progress

        self._append_log("JAMES initialized", "OK")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(10_000)

    # ── Shortcuts ─────────────────────────────────────────────────────

    def _build_shortcuts(self):
        """Build global application shortcuts."""
        # Quit
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

        # Logs
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._show_log_viewer)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self._clear_log)

        # Kill JAMES
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(self.kill_james)

        # Tabs
        for i in range(1, 6):
            # Tab indices are 0-based
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i-1: self._switch_tab(idx))

        # Tab cycling
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self._prev_tab)

    def _switch_tab(self, index: int):
        if index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _next_tab(self):
        count = self.tabs.count()
        if count > 0:
            next_idx = (self.tabs.currentIndex() + 1) % count
            self._switch_tab(next_idx)

    def _prev_tab(self):
        count = self.tabs.count()
        if count > 0:
            prev_idx = (self.tabs.currentIndex() - 1) % count
            self._switch_tab(prev_idx)

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Header band (fixed height)
        root.addWidget(self._build_header())

        # 2. Content lane — tabs + log (flex)
        content_outer = QWidget()
        content_outer.setStyleSheet("background: #08111F;")
        outer_layout = QHBoxLayout(content_outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Centered content lane, max-width 1440
        self._content_lane = QWidget()
        self._content_lane.setMaximumWidth(1440)
        lane_layout = QVBoxLayout(self._content_lane)
        lane_layout.setContentsMargins(24, 12, 24, 0)
        lane_layout.setSpacing(12)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.wifi_tab        = WiFiArsenalTab(self)
        self.autopilot_tab   = AutoPilotTab(self)
        self.airgeddon_tab   = AirgeddonTab(self)
        self.setup_tab       = SetupTab(self)
        self.troubleshoot_tab = TroubleshootTab(self)

        self.tabs.addTab(self.wifi_tab,         "Wi-Fi Arsenal")
        self.tabs.addTab(self.autopilot_tab,    "Auto-Pilot")
        self.tabs.addTab(self.airgeddon_tab,    "Airgeddon")
        self.tabs.addTab(self.setup_tab,        "Setup")
        self.tabs.addTab(self.troubleshoot_tab, "Troubleshoot")

        # Splitter: tabs (flex) + log panel (fixed-ish)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._build_log_panel())
        splitter.setSizes([560, 180])
        splitter.setChildrenCollapsible(False)

        lane_layout.addWidget(splitter)

        outer_layout.addStretch()
        outer_layout.addWidget(self._content_lane, stretch=1)
        outer_layout.addStretch()
        root.addWidget(content_outer, stretch=1)

        # 3. Session strip (fixed)
        root.addWidget(self._build_session_strip())

        # 4. Status bar
        self._build_statusbar()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(72)
        header.setStyleSheet(HEADER_STYLE)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        # Brand (T1 + T4 subtitle)
        brand = QVBoxLayout()
        brand.setSpacing(2)
        title = QLabel("JAMES")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Wi-Fi Pentesting System")
        subtitle.setObjectName("metaLabel")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        layout.addLayout(brand)

        layout.addWidget(_sep_v())

        # Status pill
        self._status_pill = QLabel("● IDLE")
        self._status_pill.setObjectName("statusOk")
        self._status_pill.setMinimumWidth(90)
        layout.addWidget(self._status_pill)

        layout.addStretch()

        # Compact metric row (T4 pairs)
        self._hdr_iface = self._make_hdr_metric("INTERFACE", "none")
        self._hdr_aps   = self._make_hdr_metric("APs", "0")
        self._hdr_keys  = self._make_hdr_metric("CRACKED", "0")
        self._hdr_up    = self._make_hdr_metric("UPTIME", "00:00")

        for w in (self._hdr_iface, self._hdr_aps, self._hdr_keys, self._hdr_up):
            layout.addWidget(w)
            layout.addWidget(_sep_v())

        # Action buttons
        self._btn_logs = QPushButton("Logs")
        self._btn_logs.setMinimumWidth(72)
        self._btn_logs.setToolTip("View log files (Ctrl+L)")
        self._btn_kill = QPushButton("Kill")
        self._btn_kill.setObjectName("dangerBtn")
        self._btn_kill.setMinimumWidth(72)
        self._btn_kill.setToolTip("Kill JAMES and restore networking (Ctrl+K)")

        layout.addWidget(self._btn_logs)
        layout.addWidget(self._btn_kill)

        return header

    def _make_hdr_metric(self, label: str, value: str) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(88)
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 0, 8, 0)
        v.setSpacing(1)
        val = QLabel(value)
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(
            "color: #C8D6E5; font-size: 14px; font-weight: 700;"
            " font-family: 'JetBrains Mono', monospace;"
        )
        cap = QLabel(label)
        cap.setAlignment(Qt.AlignCenter)
        cap.setObjectName("metaLabel")
        v.addWidget(val)
        v.addWidget(cap)
        # Store val label as attribute for updates
        val.setObjectName(f"_hdr_{label.lower().replace(' ', '_')}")
        return w

    def _get_hdr_val(self, widget: QWidget) -> QLabel:
        return widget.findChildren(QLabel)[0]

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #08111F;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        log_label = QLabel("OUTPUT")
        log_label.setObjectName("metaLabel")

        self._lbl_log_count = QLabel("0 lines")
        self._lbl_log_count.setObjectName("dimLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setProperty("textVisible", True)

        btn_copy = QPushButton("Copy")
        btn_copy.setMinimumWidth(64)
        btn_copy.setFixedHeight(26)
        btn_copy.setStyleSheet("font-size: 10px; padding: 0 10px; min-height: 26px;")
        btn_copy.setToolTip("Copy terminal output to clipboard")
        btn_copy.clicked.connect(self._copy_log)

        btn_clear = QPushButton("Clear")
        btn_clear.setMinimumWidth(64)
        btn_clear.setFixedHeight(26)
        btn_clear.setStyleSheet("font-size: 10px; padding: 0 10px; min-height: 26px;")
        btn_clear.setToolTip("Clear terminal output (Ctrl+Shift+C)")
        btn_clear.clicked.connect(self._clear_log)

        toolbar.addWidget(log_label)
        toolbar.addWidget(self._lbl_log_count)
        toolbar.addStretch()
        toolbar.addWidget(self.progress_bar, stretch=1)
        toolbar.addWidget(btn_copy)
        toolbar.addWidget(btn_clear)
        layout.addLayout(toolbar)

        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(3000)
        self.terminal.setStyleSheet(LOG_STYLE)
        self.terminal.setFont(QFont("JetBrains Mono", 10))
        layout.addWidget(self.terminal)

        return panel

    def _build_session_strip(self) -> QWidget:
        strip = QWidget()
        strip.setFixedHeight(28)
        strip.setStyleSheet(SESSION_STRIP_STYLE)
        row = QHBoxLayout(strip)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(16)

        self._sess_iface  = self._make_session_kv("INTERFACE", "none")
        self._sess_mode   = self._make_session_kv("MODE", "IDLE")
        self._sess_last   = self._make_session_kv("LAST ACTION", "—")
        self._sess_uptime = self._make_session_kv("UPTIME", "00:00:00")

        for i, widget in enumerate(
            (self._sess_iface, self._sess_mode, self._sess_last, self._sess_uptime)
        ):
            row.addWidget(widget)
            if i < 3:
                row.addWidget(_sep_v())

        row.addStretch()
        return strip

    def _make_session_kv(self, key: str, val: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        k_lbl = QLabel(key)
        k_lbl.setObjectName("metaLabel")
        v_lbl = QLabel(val)
        v_lbl.setObjectName("dimLabel")
        v_lbl.setObjectName(f"_sess_{key.lower().replace(' ', '_')}")
        h.addWidget(k_lbl)
        h.addWidget(v_lbl)
        return w

    def _get_sess_val(self, widget: QWidget) -> QLabel:
        return widget.findChildren(QLabel)[1]

    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self.lbl_status = QLabel("● IDLE")
        self.lbl_status.setObjectName("statusOk")
        bar.addWidget(self.lbl_status)

    # ── Signal wiring ─────────────────────────────────────────────────

    def _connect_signals(self):
        self._btn_kill.clicked.connect(self.kill_james)
        self._btn_logs.clicked.connect(self._show_log_viewer)
        self.progress_signal.connect(self._update_progress_ui)
        self.log_signal.connect(self._on_log_received)

    # ── Logging with timestamps + severity ───────────────────────────

    def _append_log(self, text: str, severity: str = "INFO"):
        self.log_signal.emit(str(text), severity)

    @pyqtSlot(str, str)
    def _on_log_received(self, text: str, severity: str):
        ts = datetime.now().strftime("%H:%M")
        sev = _SEV.get(severity.upper(), "INFO ")
        formatted = f"[{ts}]  {sev}  {text}"
        self.terminal.appendPlainText(formatted)
        self.terminal.verticalScrollBar().setValue(
            self.terminal.verticalScrollBar().maximum()
        )
        self._log_count += 1
        self._lbl_log_count.setText(f"{self._log_count} lines")
        self._last_action = text[:48] + ("…" if len(text) > 48 else "")
        self._get_sess_val(self._sess_last).setText(self._last_action)

    def _clear_log(self):
        self.terminal.clear()
        self._log_count = 0
        self._lbl_log_count.setText("0 lines")

    def _copy_log(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.terminal.toPlainText())
        show_toast(self, "Log copied", "info")

    # ── State ─────────────────────────────────────────────────────────

    def _set_idle(self, idle: bool):
        if idle:
            self._status_pill.setText("● IDLE")
            self._status_pill.setObjectName("statusOk")
            self.lbl_status.setText("● IDLE")
            self.lbl_status.setObjectName("statusOk")
            self.progress_bar.setVisible(False)
            self._current_mode = "IDLE"
        else:
            self._status_pill.setText("● BUSY")
            self._status_pill.setObjectName("statusWarn")
            self.lbl_status.setText("● BUSY")
            self.lbl_status.setObjectName("statusWarn")
            self.progress_bar.setVisible(True)
            self._current_mode = "BUSY"
        for lbl in (self._status_pill, self.lbl_status):
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self._get_sess_val(self._sess_mode).setText(self._current_mode)

    # ── Timers ────────────────────────────────────────────────────────

    def _tick(self):
        self.uptime_seconds += 1
        h = self.uptime_seconds // 3600
        m = (self.uptime_seconds % 3600) // 60
        s = self.uptime_seconds % 60
        up_str = f"{h:02d}:{m:02d}:{s:02d}"
        self._get_hdr_val(self._hdr_up).setText(up_str)
        self._get_sess_val(self._sess_uptime).setText(up_str)

        if self.active_interface:
            self._get_hdr_val(self._hdr_iface).setText(self.active_interface)
            self._get_sess_val(self._sess_iface).setText(self.active_interface)

    def _refresh_stats(self):
        try:
            summary  = self.orchestrator.get_loot_summary()
            n_loot   = summary.get("total_handshakes", 0)
            n_keys   = summary.get("total_cracked", 0)
            self._get_hdr_val(self._hdr_keys).setText(str(n_keys))
            if n_keys != self._key_count and n_keys > 0:
                self._get_hdr_val(self._hdr_keys).setStyleSheet(
                    "color: #C8961A; font-size: 14px; font-weight: 700;"
                    " font-family: 'JetBrains Mono', monospace;"
                )
            self._key_count = n_keys
        except Exception:
            pass

    # ── Progress ──────────────────────────────────────────────────────

    def _on_orchestrator_progress(self, phase: str, num: int, total: int):
        self.progress_signal.emit(phase, num, total)

    @pyqtSlot(str, int, int)
    def _update_progress_ui(self, phase: str, num: int, total: int):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(num)
        self.progress_bar.setFormat(f"  {phase}  {num}/{total}")
        self._set_idle(False)

    # ── Public helpers for tab updates ────────────────────────────────

    def set_ap_count(self, n: int):
        self._ap_count = n
        self._get_hdr_val(self._hdr_aps).setText(str(n))

    # ── Actions ───────────────────────────────────────────────────────

    def kill_james(self):
        reply = QMessageBox.question(
            self, "Kill JAMES",
            "Abort all operations and restore networking?\n\n"
            "This will stop all tools, restore Wi-Fi interfaces,\n"
            "and restart NetworkManager.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._set_idle(False)
            self.worker = WorkerThread(self.orchestrator.kill_james)
            self.worker.finished.connect(lambda _: self._set_idle(True))
            self.worker.start()

    def closeEvent(self, event):
        self.orchestrator.kill_james()
        event.accept()

    # ── Log viewer dialog ─────────────────────────────────────────────

    def _show_log_viewer(self):
        log_dir = Path.home() / ".james" / "logs"
        if not log_dir.exists():
            show_toast(self, "No log directory found", "error")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("JAMES — Log Viewer")
        dlg.resize(1000, 640)
        dlg.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        hdr = QLabel("Log Viewer")
        hdr.setObjectName("sectionLabel")
        layout.addWidget(hdr)

        sel = QHBoxLayout()
        sel.setSpacing(8)
        combo = QComboBox()
        combo.setMinimumWidth(320)
        log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for lf in log_files:
            combo.addItem(f"{lf.name}  ({lf.stat().st_size / 1024:.0f} KB)", str(lf))
        btn_reload = QPushButton("Reload")
        btn_reload.setFixedWidth(72)
        sel.addWidget(combo, stretch=1)
        sel.addWidget(btn_reload)
        layout.addLayout(sel)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setStyleSheet(LOG_STYLE)
        viewer.setFont(QFont("JetBrains Mono", 10))
        layout.addWidget(viewer)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.close)
        layout.addWidget(btns)

        def load():
            path = combo.currentData()
            if path:
                try:
                    viewer.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))
                    viewer.verticalScrollBar().setValue(viewer.verticalScrollBar().maximum())
                except Exception as e:
                    viewer.setPlainText(f"Error: {e}")

        combo.currentIndexChanged.connect(lambda _: load())
        btn_reload.clicked.connect(load)
        if log_files:
            load()
        dlg.exec_()
