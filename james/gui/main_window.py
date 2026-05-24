"""JAMES — Main Window (v2, premium UI)."""

import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QGroupBox,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QComboBox,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
import logging

from james.core.orchestrator import Orchestrator
from james.gui.theme import DARK_STYLESHEET, TERMINAL_STYLE, HEADER_GRADIENT
from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread

from james.gui.tabs.wifi_tab import WiFiArsenalTab
from james.gui.tabs.autopilot_tab import AutoPilotTab
from james.gui.tabs.setup_tab import SetupTab
from james.gui.tabs.troubleshoot_tab import TroubleshootTab
from james.gui.tabs.airgeddon_tab import AirgeddonTab

logger = logging.getLogger(__name__)


# ── Stat badge widget ─────────────────────────────────────────────────
class _StatBadge(QWidget):
    """Small icon + value + label stacked badge for the header stats row."""

    def __init__(self, icon: str, label: str, value: str = "—", color: str = "#00e5ff"):
        super().__init__()
        self._color = color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(1)

        self.val_lbl = QLabel(value)
        self.val_lbl.setAlignment(Qt.AlignCenter)
        self.val_lbl.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 800; "
            f"font-family: 'JetBrains Mono', monospace;"
        )

        cap_lbl = QLabel(f"{icon}  {label}")
        cap_lbl.setAlignment(Qt.AlignCenter)
        cap_lbl.setStyleSheet(
            "color: #3a5a7a; font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )

        layout.addWidget(self.val_lbl)
        layout.addWidget(cap_lbl)

        self.setStyleSheet(
            "background: #080d1c; border: 1px solid #16213a; border-radius: 8px;"
        )
        self.setFixedWidth(110)

    def set_value(self, value: str):
        self.val_lbl.setText(value)

    def flash(self, color: str = "#00ff88"):
        """Briefly change the value colour to signal an update."""
        self.val_lbl.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 800; "
            f"font-family: 'JetBrains Mono', monospace;"
        )
        QTimer.singleShot(
            800,
            lambda: self.val_lbl.setStyleSheet(
                f"color: {self._color}; font-size: 16px; font-weight: 800; "
                f"font-family: 'JetBrains Mono', monospace;"
            ),
        )


# ── Main Window ───────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """JAMES premium GUI — v2."""

    progress_signal = pyqtSignal(str, int, int)
    log_signal = pyqtSignal(str)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None
        self._log_count = 0

        self.setWindowTitle("JAMES  ·  Wi-Fi Pentesting Agent")
        self.setMinimumSize(1080, 820)
        self.resize(1280, 880)
        self.setStyleSheet(DARK_STYLESHEET)

        # Context tracking
        self.active_interface = None
        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()

        # Wire orchestrator callbacks
        self.orchestrator.on_print = self._append_log
        self.orchestrator.on_progress = self._on_orchestrator_progress

        self._append_log("⚡ JAMES v2 ready. Select an interface in Wi-Fi Arsenal to begin.")

        # Uptime timer
        self.uptime_seconds = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        # Loot stats refresh (every 10 s)
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(10_000)

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralwidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(12)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.wifi_tab = WiFiArsenalTab(self)
        self.autopilot_tab = AutoPilotTab(self)
        self.airgeddon_tab = AirgeddonTab(self)
        self.setup_tab = SetupTab(self)
        self.troubleshoot_tab = TroubleshootTab(self)

        self.tabs.addTab(self.wifi_tab,        "📡  Wi-Fi Arsenal")
        self.tabs.addTab(self.autopilot_tab,   "🤖  Auto-Pilot")
        self.tabs.addTab(self.airgeddon_tab,   "👿  Airgeddon")
        self.tabs.addTab(self.setup_tab,       "⚙️  Setup")
        self.tabs.addTab(self.troubleshoot_tab,"🔧  Troubleshoot")

        # Vertical splitter: tabs on top, log panel on bottom
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(3)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._make_log_panel())
        splitter.setSizes([580, 220])
        splitter.setChildrenCollapsible(False)

        content_layout.addWidget(splitter)
        root.addWidget(content, stretch=1)

        # Status bar
        self._build_statusbar()

    def _make_header(self) -> QWidget:
        """Build the top gradient header bar with stats badges."""
        header = QWidget()
        header.setStyleSheet(HEADER_GRADIENT)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        # Logo / title block
        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title = QLabel("⚡ JAMES")
        title.setObjectName("headerLabel")
        subtitle = QLabel("Just Another Multipurpose Exploitation System")
        subtitle.setObjectName("subHeader")

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)

        layout.addStretch()

        # Stats badges
        self._badge_iface  = _StatBadge("🔌", "INTERFACE", "none")
        self._badge_aps    = _StatBadge("📡", "APs SEEN",  "0")
        self._badge_loot   = _StatBadge("💾", "LOOT",      "0",    "#00ff88")
        self._badge_keys   = _StatBadge("🔑", "CRACKED",   "0",    "#ffaa00")
        self._badge_uptime = _StatBadge("⏱", "UPTIME",    "00:00","#a855f7")

        for badge in (
            self._badge_iface,
            self._badge_aps,
            self._badge_loot,
            self._badge_keys,
            self._badge_uptime,
        ):
            layout.addWidget(badge)

        # Quick-action buttons on header
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #16213a;")
        layout.addWidget(sep)

        btn_kill = QPushButton("🛑 KILL")
        btn_kill.setObjectName("dangerBtn")
        btn_kill.setFixedWidth(80)
        btn_kill.setToolTip("Abort all operations and restore networking")
        btn_kill.clicked.connect(self.kill_james)

        btn_logs = QPushButton("📋 LOGS")
        btn_logs.setFixedWidth(80)
        btn_logs.setToolTip("Browse persistent log files")
        btn_logs.clicked.connect(self._show_log_viewer)

        layout.addWidget(btn_logs)
        layout.addWidget(btn_kill)

        return header

    def _make_log_panel(self) -> QWidget:
        """Build the bottom terminal output panel."""
        panel = QGroupBox("OUTPUT")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(6)

        # Toolbar row
        toolbar = QHBoxLayout()

        self._lbl_log_count = QLabel("0 lines")
        self._lbl_log_count.setObjectName("dimLabel")

        btn_clear = QPushButton("✕  Clear")
        btn_clear.setFixedWidth(80)
        btn_clear.setFixedHeight(24)
        btn_clear.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; border-radius: 5px;"
        )
        btn_clear.clicked.connect(self._clear_log)

        btn_copy = QPushButton("⧉  Copy")
        btn_copy.setFixedWidth(80)
        btn_copy.setFixedHeight(24)
        btn_copy.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; border-radius: 5px;"
        )
        btn_copy.clicked.connect(self._copy_log)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)

        toolbar.addWidget(self._lbl_log_count)
        toolbar.addStretch()
        toolbar.addWidget(self.progress_bar, stretch=1)
        toolbar.addWidget(btn_copy)
        toolbar.addWidget(btn_clear)
        panel_layout.addLayout(toolbar)

        # Terminal output
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(4000)
        self.terminal.setStyleSheet(TERMINAL_STYLE)
        self.terminal.setFont(QFont("JetBrains Mono", 10))
        panel_layout.addWidget(self.terminal)

        return panel

    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)

        self.lbl_status = QLabel("●  IDLE")
        self.lbl_status.setObjectName("statusOk")

        self.lbl_mode = QLabel("GUI MODE")
        self.lbl_mode.setObjectName("dimLabel")

        bar.addWidget(self.lbl_status)
        bar.addWidget(self._vsep())
        bar.addWidget(self.lbl_mode)

    def _vsep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setStyleSheet("color: #16213a; margin: 4px 4px;")
        return f

    # ── Signal wiring ─────────────────────────────────────────────────

    def _connect_signals(self):
        self.progress_signal.connect(self._update_progress_ui)
        self.log_signal.connect(self._on_log_received)

    # ── Logging ───────────────────────────────────────────────────────

    def _append_log(self, text: str):
        self.log_signal.emit(str(text))

    @pyqtSlot(str)
    def _on_log_received(self, text: str):
        self.terminal.appendPlainText(text)
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._log_count += 1
        self._lbl_log_count.setText(f"{self._log_count} lines")

    def _clear_log(self):
        self.terminal.clear()
        self._log_count = 0
        self._lbl_log_count.setText("0 lines")

    def _copy_log(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.terminal.toPlainText())
        show_toast(self, "Log copied to clipboard", "info")

    # ── State helpers ─────────────────────────────────────────────────

    def _set_idle(self, idle: bool):
        if idle:
            self.lbl_status.setText("●  IDLE")
            self.lbl_status.setObjectName("statusOk")
            self.progress_bar.setVisible(False)
        else:
            self.lbl_status.setText("●  BUSY")
            self.lbl_status.setObjectName("statusBad")
            self.progress_bar.setVisible(True)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    # ── Timers ────────────────────────────────────────────────────────

    def _tick(self):
        self.uptime_seconds += 1
        h = self.uptime_seconds // 3600
        m = (self.uptime_seconds % 3600) // 60
        s = self.uptime_seconds % 60
        self._badge_uptime.set_value(f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")

        # Update interface badge
        if self.active_interface:
            self._badge_iface.set_value(self.active_interface)

    def _refresh_stats(self):
        """Refresh loot / cracked-key badges from orchestrator cache."""
        try:
            summary = self.orchestrator.get_loot_summary()
            n_loot = summary.get("total_handshakes", 0)
            n_keys = summary.get("total_cracked", 0)
            self._badge_loot.set_value(str(n_loot))
            self._badge_keys.set_value(str(n_keys))
            if n_keys > 0:
                self._badge_keys.flash("#ffaa00")
        except Exception:
            pass

    # ── Progress from orchestrator ────────────────────────────────────

    def _on_orchestrator_progress(self, phase: str, num: int, total: int):
        self.progress_signal.emit(phase, num, total)

    @pyqtSlot(str, int, int)
    def _update_progress_ui(self, phase: str, num: int, total: int):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(num)
        self.progress_bar.setFormat(f"  {phase}  ({num}/{total})")
        self._set_idle(False)

    # ── Actions ───────────────────────────────────────────────────────

    def kill_james(self):
        reply = QMessageBox.question(
            self,
            "Kill JAMES",
            "Abort all operations and restore networking?\n\n"
            "This will stop all active tools, restore Wi-Fi interfaces,\n"
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
        dlg.setWindowTitle("JAMES  ·  Log Viewer")
        dlg.resize(1000, 640)
        dlg.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # Header row
        hdr = QLabel("📋  Log Viewer")
        hdr.setObjectName("sectionLabel")
        layout.addWidget(hdr)

        # File selector row
        sel_row = QHBoxLayout()
        sel_lbl = QLabel("File:")
        sel_lbl.setObjectName("dimLabel")
        combo = QComboBox()
        combo.setMinimumWidth(360)

        log_files = sorted(
            log_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for lf in log_files:
            size_kb = lf.stat().st_size / 1024
            combo.addItem(f"{lf.name}  ({size_kb:.0f} KB)", str(lf))

        btn_reload = QPushButton("↻  Reload")
        btn_reload.setFixedWidth(90)

        sel_row.addWidget(sel_lbl)
        sel_row.addWidget(combo, stretch=1)
        sel_row.addWidget(btn_reload)
        layout.addLayout(sel_row)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setStyleSheet(TERMINAL_STYLE)
        viewer.setFont(QFont("JetBrains Mono", 9))
        layout.addWidget(viewer)

        btn_bar = QDialogButtonBox(QDialogButtonBox.Close)
        btn_bar.rejected.connect(dlg.close)
        layout.addWidget(btn_bar)

        def load_log():
            path = combo.currentData()
            if path:
                try:
                    content = Path(path).read_text(encoding="utf-8", errors="replace")
                    viewer.setPlainText(content)
                    viewer.verticalScrollBar().setValue(
                        viewer.verticalScrollBar().maximum()
                    )
                except Exception as e:
                    viewer.setPlainText(f"Error reading log: {e}")

        combo.currentIndexChanged.connect(lambda _: load_log())
        btn_reload.clicked.connect(load_log)
        if log_files:
            load_log()

        dlg.exec_()
