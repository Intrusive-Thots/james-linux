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
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QIcon, QFont, QColor
import logging

from james.core.orchestrator import Orchestrator
from james.gui.theme import DARK_STYLESHEET
from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread

from james.gui.tabs.wifi_tab import WiFiArsenalTab
from james.gui.tabs.autopilot_tab import AutoPilotTab
from james.gui.tabs.setup_tab import SetupTab
from james.gui.tabs.troubleshoot_tab import TroubleshootTab
from james.gui.tabs.airgeddon_tab import AirgeddonTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Simplified JAMES GUI - 3 Step Wi-Fi Cracker.
    """

    progress_signal = pyqtSignal(str, int, int)
    log_signal = pyqtSignal(str)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None

        self.setWindowTitle("JAMES - Wi-Fi Pentesting Agent")
        self.setMinimumSize(900, 800)
        self.setStyleSheet(DARK_STYLESHEET)

        # State tracking
        self.active_interface = None
        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None

        self._build_ui()
        self._connect_signals()

        # Route orchestrator output to GUI
        self.orchestrator.on_print = self._append_log
        self.orchestrator.on_progress = self._on_orchestrator_progress

        self._append_log(
            "JAMES Initialized. Select an interface in the Cracker tab to begin."
        )

        # Uptime timer
        self.uptime_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_uptime)
        self.timer.start(1000)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("⚡ JAMES  //  Wi-Fi Cracker")
        header.setObjectName("headerLabel")
        main_layout.addWidget(header)

        # Splitter for top panels and bottom log
        splitter = QSplitter(Qt.Vertical)

        # Top container for panels
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        # ── Tab Widget ──
        self.tabs = QTabWidget()

        self.wifi_tab = WiFiArsenalTab(self)
        self.autopilot_tab = AutoPilotTab(self)
        self.airgeddon_tab = AirgeddonTab(self)
        self.setup_tab = SetupTab(self)
        self.troubleshoot_tab = TroubleshootTab(self)

        self.tabs.addTab(self.wifi_tab, "📡 WiFi Arsenal")
        self.tabs.addTab(self.autopilot_tab, "🤖 Auto-Pilot")
        self.tabs.addTab(self.airgeddon_tab, "👿 Airgeddon GUI")
        self.tabs.addTab(self.setup_tab, "⚙️ Setup")
        self.tabs.addTab(self.troubleshoot_tab, "🔧 Troubleshoot")

        top_layout.addWidget(self.tabs)

        splitter.addWidget(top_container)

        # ── Output Log ──
        log_group = QGroupBox("OUTPUT LOG")
        log_layout = QVBoxLayout(log_group)
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("JetBrains Mono", 10))
        log_layout.addWidget(self.terminal)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        log_layout.addWidget(self.progress_bar)

        splitter.addWidget(log_group)
        main_layout.addWidget(splitter)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status = QLabel("Status: ● IDLE")
        self.lbl_uptime = QLabel("⏱ 00:00:00")
        self.btn_kill = QPushButton("🛑 KILL JAMES")
        self.btn_kill.setObjectName("dangerBtn")
        self.status_bar.addWidget(self.lbl_status)
        self.status_bar.addWidget(self.lbl_uptime)

        self.btn_view_logs = QPushButton("📋 View Logs")
        self.status_bar.addPermanentWidget(self.btn_view_logs)
        self.status_bar.addPermanentWidget(self.btn_kill)

    def _connect_signals(self):
        self.btn_kill.clicked.connect(self.kill_james)
        self.btn_view_logs.clicked.connect(self._show_log_viewer)
        self.progress_signal.connect(self._update_progress_ui)
        self.log_signal.connect(self._on_log_received)

    def _append_log(self, text: str):
        self.log_signal.emit(text)

    def _on_log_received(self, text: str):
        self.terminal.appendPlainText(text)
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_idle(self, idle: bool):
        # Notify tabs to update their UI if needed
        # In a real app we'd broadcast a signal, but for now we just toggle the global status

        if idle:
            self.lbl_status.setText("Status: ● IDLE")
            self.lbl_status.setObjectName("statusOk")
            self.progress_bar.setVisible(False)
        else:
            self.lbl_status.setText("Status: ● BUSY")
            self.lbl_status.setObjectName("statusBad")
            self.progress_bar.setVisible(True)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def _update_uptime(self):
        self.uptime_seconds += 1
        h = self.uptime_seconds // 3600
        m = (self.uptime_seconds % 3600) // 60
        s = self.uptime_seconds % 60
        self.lbl_uptime.setText(f"⏱ {h:02d}:{m:02d}:{s:02d}")

    # ── Utilities ──
    def kill_james(self):
        reply = QMessageBox.question(
            self,
            "Kill JAMES",
            "Abort all operations and restore networking?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._set_idle(False)
            self.worker = WorkerThread(self.orchestrator.kill_james)
            self.worker.finished.connect(lambda r: self._set_idle(True))
            self.worker.start()

    def _on_orchestrator_progress(self, phase, num, total):
        self.progress_signal.emit(phase, num, total)

    @pyqtSlot(str, int, int)
    def _update_progress_ui(self, phase, num, total):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(num)
        self.progress_bar.setFormat(f"{phase} (%v/%m)")

    def closeEvent(self, event):
        self.orchestrator.kill_james()
        event.accept()

    def _show_log_viewer(self):
        """Open a dialog to browse persistent log files."""
        log_dir = Path.home() / ".james" / "logs"
        if not log_dir.exists():
            show_toast(self, "No log directory found", "error")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("JAMES Log Viewer")
        dlg.resize(900, 600)
        layout = QVBoxLayout(dlg)

        # File selector
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Log File:"))
        combo = QComboBox()

        log_files = sorted(
            log_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for lf in log_files:
            size_kb = lf.stat().st_size / 1024
            combo.addItem(f"{lf.name} ({size_kb:.0f} KB)", str(lf))

        selector_row.addWidget(combo)
        btn_refresh_log = QPushButton("↻ Reload")
        selector_row.addWidget(btn_refresh_log)
        layout.addLayout(selector_row)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setFont(QFont("JetBrains Mono", 9))
        layout.addWidget(viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.close)
        layout.addWidget(buttons)

        def load_log():
            path = combo.currentData()
            if path:
                try:
                    with open(
                        path, "r", encoding="utf-8", errors="replace"
                    ) as f:
                        content = f.read()
                    viewer.setPlainText(content)
                    # Scroll to bottom
                    sb = viewer.verticalScrollBar()
                    sb.setValue(sb.maximum())
                except Exception as e:
                    viewer.setPlainText(f"Error reading log: {e}")

        combo.currentIndexChanged.connect(lambda _: load_log())
        btn_refresh_log.clicked.connect(load_log)

        if log_files:
            load_log()

        dlg.exec_()
