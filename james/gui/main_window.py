"""JAMES — Main Window v4 (Mission Control Layout)."""

from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QComboBox,
    QFrame,
    QShortcut,
    QApplication,
    QMenu,
    QAction,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve, QThread
from PyQt5.QtGui import QFont, QKeySequence
import json
import logging
import os
import subprocess
import sys

from james.core.orchestrator import Orchestrator
from james.gui.theme import (
    DARK_STYLESHEET,
    TERMINAL_STYLE,
    LOG_STYLE,
    HEADER_STYLE,
    SESSION_STRIP_STYLE,
)
from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread
from james.gui.tabs.wifi_tab import WiFiArsenalTab
from james.gui.tabs.autopilot_tab import AutoPilotTab
from james.gui.tabs.setup_tab import SetupTab
from james.gui.tabs.troubleshoot_tab import TroubleshootTab
from james.gui.tabs.airgeddon_tab import AirgeddonTab
from james.gui.tabs.activity_tab import ActivitySidebar
from james.gui.chat_panel import ChatPanel
from james.gui.setup_wizard import SetupWizard

logger = logging.getLogger(__name__)

# Log severity prefixes for timestamped entries
_SEV = {
    "INFO": "INFO ",
    "WARN": "WARN ",
    "CRIT": "CRIT ",
    "OK": "OK   ",
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


# ── Command Bar Worker ────────────────────────────────────────────────

class _CmdWorker(QThread):
    """Run agent command in background thread."""
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, orchestrator, command: str):
        super().__init__()
        self.orchestrator = orchestrator
        self.command = command

    def run(self):
        try:
            if hasattr(self.orchestrator, "agent") and self.orchestrator.agent:
                result = self.orchestrator.agent.process(self.command)
                # agent.process returns a string directly
                if isinstance(result, str):
                    self.result_signal.emit(result)
                    return
                result = {"output": str(result)}
            elif hasattr(self.orchestrator, "handle_command"):
                result = self.orchestrator.handle_command(self.command)
            else:
                result = {"output": f"Received: {self.command!r}"}
            if isinstance(result, dict):
                text = (
                    result.get("output")
                    or result.get("message")
                    or json.dumps(result, indent=2)
                )
            else:
                text = str(result)
            self.result_signal.emit(text)
        except Exception as exc:
            self.error_signal.emit(str(exc))


class MainWindow(QMainWindow):
    """JAMES main window — Mission Control layout."""

    progress_signal = pyqtSignal(str, int, int)
    log_signal = pyqtSignal(str, str)  # (message, severity)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None
        self._cmd_worker = None

        self.setWindowTitle("JAMES")
        self.setMinimumSize(1080, 760)
        self.resize(1420, 920)
        self.setStyleSheet(DARK_STYLESHEET)

        # Shared state
        self.active_interface = None
        self.selected_bssid = None
        self.selected_essid = None
        self.selected_channel = None
        self._log_count = 0
        self._ap_count = 0
        self._key_count = 0
        self._last_action = "—"
        self._current_mode = "IDLE"
        self._current_operation = ""
        self.uptime_seconds = 0

        self._build_ui()
        self._connect_signals()
        self._build_shortcuts()

        # Wire orchestrator print/progress into main log FIRST
        self.orchestrator.on_print = lambda t: self._append_log(t, "INFO")
        self.orchestrator.on_progress = self._on_orchestrator_progress

        # Explicitly initialize persistent animation reference to avoid premature garbage collection
        self._log_scroll_anim = None

        # Now let the activity sidebar hook in (chains to callbacks above)
        self.activity_sidebar._hook_orchestrator()

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

        # Command bar focus
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(
            self._focus_command_bar
        )

        # Logs
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(
            self._show_log_viewer
        )
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(
            self._clear_log
        )
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(
            self._copy_log
        )

        # Emergency stop
        QShortcut(QKeySequence("Ctrl+Shift+K"), self).activated.connect(
            self.emergency_stop
        )

        # Restart JAMES
        QShortcut(QKeySequence("Ctrl+Shift+R"), self).activated.connect(
            self.restart_james
        )

        # Tabs (now 1-5)
        for i in range(1, 6):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i - 1: self._switch_tab(idx))

        # Tab cycling
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(
            self._next_tab
        )
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(
            self._prev_tab
        )

        # Toggle sidebar
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(
            self._toggle_sidebar
        )

        # Show setup wizard on first run
        if SetupWizard.should_show():
            QTimer.singleShot(500, self._show_setup_wizard)

    def _switch_tab(self, index: int):
        if index < self.tabs.count():
            if index == self.tabs.currentIndex():
                self._on_tab_changed(index)
            else:
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

    def _toggle_sidebar(self):
        if self.activity_sidebar._collapsed:
            self.activity_sidebar._expand()
        else:
            self.activity_sidebar._collapse()

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Header band (fixed height)
        root.addWidget(self._build_header())

        # 2. Content: Sidebar + (Tabs + Log)
        content_outer = QWidget()
        content_outer.setStyleSheet("background: #1F1F1F;")
        outer_layout = QHBoxLayout(content_outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Activity Sidebar (left)
        self.activity_sidebar = ActivitySidebar(self)

        # Main content lane (right)
        self._content_lane = QWidget()
        self._content_lane.setMaximumWidth(1440)
        lane_layout = QVBoxLayout(self._content_lane)
        lane_layout.setContentsMargins(24, 12, 24, 0)
        lane_layout.setSpacing(12)

        # Tab widget — reduced tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.chat_panel = ChatPanel(self.orchestrator, self)
        self.wifi_tab = WiFiArsenalTab(self)
        self.autopilot_tab = AutoPilotTab(self)
        self.airgeddon_tab = AirgeddonTab(self)

        # Merged Config tab (Setup + Troubleshoot)
        self.config_tab = self._build_config_tab()

        self.tabs.addTab(self.chat_panel, "Agent")
        self.tabs.setTabToolTip(0, "Conversational AI (Ctrl+1)")

        self.tabs.addTab(self.wifi_tab, "Wi-Fi Arsenal")
        self.tabs.setTabToolTip(1, "Wi-Fi auditing and tools (Ctrl+2)")

        self.tabs.addTab(self.autopilot_tab, "Auto-Pilot")
        self.tabs.setTabToolTip(2, "Automated routines (Ctrl+3)")

        self.tabs.addTab(self.airgeddon_tab, "Airgeddon")
        self.tabs.setTabToolTip(3, "Evil Twin pipeline (Ctrl+4)")

        self.tabs.addTab(self.config_tab, "⚙ Config")
        self.tabs.setTabToolTip(4, "System configuration and diagnostics (Ctrl+5)")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Splitter: tabs (flex) + log panel (fixed-ish)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._build_log_panel())
        splitter.setSizes([560, 180])
        splitter.setChildrenCollapsible(False)

        lane_layout.addWidget(splitter)

        # Assemble: sidebar | content
        outer_layout.addWidget(self.activity_sidebar)
        outer_layout.addWidget(_sep_v())
        outer_layout.addStretch()
        outer_layout.addWidget(self._content_lane, stretch=1)
        outer_layout.addStretch()
        root.addWidget(content_outer, stretch=1)

        # 3. Global Command Bar (replaces session strip)
        root.addWidget(self._build_command_bar())

        # 4. Status bar
        self._build_statusbar()

    def _on_tab_changed(self, index: int):
        widget = self.tabs.widget(index)
        if hasattr(widget, "_input") and widget == self.chat_panel:
            widget._input.setFocus()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet(HEADER_STYLE)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Brand
        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = QLabel("JAMES")
        title.setObjectName("titleLabel")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #CCCCCC;"
            " letter-spacing: 0.3px;"
        )
        subtitle = QLabel("Pentesting System")
        subtitle.setObjectName("metaLabel")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        layout.addLayout(brand)

        layout.addWidget(_sep_v())

        # Operation context (replaces static "IDLE/BUSY")
        self._op_context = QWidget()
        op_layout = QVBoxLayout(self._op_context)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setSpacing(1)

        self._status_pill = QLabel("● IDLE")
        self._status_pill.setObjectName("statusOk")
        self._status_pill.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
        )

        self._op_label = QLabel("")
        self._op_label.setObjectName("metaLabel")
        self._op_label.setStyleSheet(
            "font-size: 11px; color: #3C3C3C;"
        )

        op_layout.addWidget(self._status_pill)
        op_layout.addWidget(self._op_label)
        self._op_context.setMinimumWidth(180)
        layout.addWidget(self._op_context)

        layout.addStretch()

        # Compact metrics
        self._hdr_iface = self._make_hdr_metric("INTERFACE", "none")
        self._hdr_aps = self._make_hdr_metric("APs", "0")
        self._hdr_keys = self._make_hdr_metric("CRACKED", "0")
        self._hdr_up = self._make_hdr_metric("UPTIME", "00:00")

        for w in (
            self._hdr_iface,
            self._hdr_aps,
            self._hdr_keys,
            self._hdr_up,
        ):
            layout.addWidget(w)
            layout.addWidget(_sep_v())

        # Action buttons
        self._btn_sidebar = QPushButton("◀")
        self._btn_sidebar.setFixedSize(32, 32)
        self._btn_sidebar.setToolTip("Toggle activity sidebar (Ctrl+B)")
        self._btn_sidebar.setStyleSheet(
            "QPushButton { background: #202020; color: #4daafc;"
            " border: 1px solid #2B2B2B; border-radius: 6px;"
            " font-size: 14px; font-weight: 700; }"
            "QPushButton:hover { background: #2B2B2B; border-color: #4daafc; }"
        )
        self._btn_sidebar.clicked.connect(self._toggle_sidebar)

        self._btn_logs = QPushButton("Logs")
        self._btn_logs.setMinimumWidth(60)
        self._btn_logs.setToolTip("View log files (Ctrl+L)")

        # Power menu — replaces the old single "Kill" button
        self._btn_power = QPushButton("⏻ Power")
        self._btn_power.setObjectName("dangerBtn")
        self._btn_power.setMinimumWidth(90)
        self._btn_power.setToolTip("Restart, stop, or reboot")

        power_menu = QMenu(self)
        power_menu.setStyleSheet(
            "QMenu {"
            "  background: #181818; color: #CCCCCC;"
            "  border: 1px solid #2B2B2B; border-radius: 6px;"
            "  padding: 6px 0;"
            "  font-size: 13px;"
            "}"
            "QMenu::item {"
            "  padding: 8px 20px; margin: 2px 6px;"
            "  border-radius: 4px;"
            "}"
            "QMenu::item:selected {"
            "  background: #2B2B2B;"
            "}"
            "QMenu::separator {"
            "  height: 1px; background: #2B2B2B;"
            "  margin: 4px 12px;"
            "}"
        )

        act_restart = QAction("🔄  Restart JAMES", self)
        act_restart.setShortcut("Ctrl+Shift+R")
        act_restart.setToolTip("Close and relaunch JAMES (keeps network)")
        act_restart.triggered.connect(self.restart_james)

        act_stop = QAction("🛑  Emergency Stop", self)
        act_stop.setShortcut("Ctrl+Shift+K")
        act_stop.setToolTip("Kill all tools, restore interfaces, restart NetworkManager")
        act_stop.triggered.connect(self.emergency_stop)

        act_reboot = QAction("⚡  Reboot PC", self)
        act_reboot.setToolTip("Cleanly reboot the entire system")
        act_reboot.triggered.connect(self.reboot_pc)

        act_quit = QAction("✕  Quit JAMES", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)

        power_menu.addAction(act_restart)
        power_menu.addSeparator()
        power_menu.addAction(act_stop)
        power_menu.addSeparator()
        power_menu.addAction(act_reboot)
        power_menu.addSeparator()
        power_menu.addAction(act_quit)

        self._btn_power.setMenu(power_menu)

        layout.addWidget(self._btn_sidebar)
        layout.addWidget(self._btn_logs)
        layout.addWidget(self._btn_power)

        return header

    def _make_hdr_metric(self, label: str, value: str) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(80)
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 0, 6, 0)
        v.setSpacing(1)
        val = QLabel(value)
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(
            "color: #CCCCCC; font-size: 15px; font-weight: 700;"
            " font-family: 'JetBrains Mono', monospace;"
        )
        cap = QLabel(label)
        cap.setAlignment(Qt.AlignCenter)
        cap.setObjectName("metaLabel")
        v.addWidget(val)
        v.addWidget(cap)
        val.setObjectName(f"_hdr_{label.lower().replace(' ', '_')}")
        return w

    def _get_hdr_val(self, widget: QWidget) -> QLabel:
        return widget.findChildren(QLabel)[0]

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: #1F1F1F;")
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
        btn_copy.setStyleSheet(
            "font-size: 10px; padding: 0 10px; min-height: 26px;"
        )
        btn_copy.setToolTip("Copy terminal output to clipboard (Ctrl+C)")
        btn_copy.clicked.connect(self._copy_log)

        btn_clear = QPushButton("Clear")
        btn_clear.setMinimumWidth(64)
        btn_clear.setFixedHeight(26)
        btn_clear.setStyleSheet(
            "font-size: 10px; padding: 0 10px; min-height: 26px;"
        )
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
        self.terminal.setFont(QFont("JetBrains Mono", 13))
        layout.addWidget(self.terminal)

        return panel

    # ── Global Command Bar (replaces session strip) ───────────────────

    def _build_command_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            "background: #181818; border-top: 1px solid #2B2B2B;"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(8)

        # Command prompt icon
        prompt = QLabel("⌨")
        prompt.setStyleSheet(
            "color: #3C3C3C; font-size: 16px;"
        )
        layout.addWidget(prompt)

        # Command input
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText(
            "Type a command…  (Ctrl+K to focus)"
        )
        self._cmd_input.setStyleSheet(
            "QLineEdit {"
            "  background: #202020; color: #CCCCCC;"
            "  border: 1px solid #2B2B2B; border-radius: 6px;"
            "  padding: 6px 12px; font-size: 13px;"
            "  font-family: 'JetBrains Mono', monospace;"
            "}"
            "QLineEdit:focus {"
            "  border: 1px solid #4daafc;"
            "  background-color: #1A2333;"
            "}"
            "QLineEdit::placeholder { color: #3C3C3C; }"
        )
        self._cmd_input.returnPressed.connect(self._on_cmd_submit)
        layout.addWidget(self._cmd_input, stretch=1)

        # Status indicators in the bar
        self._cmd_status = QLabel("")
        self._cmd_status.setStyleSheet(
            "color: #3C3C3C; font-size: 12px;"
        )
        layout.addWidget(self._cmd_status)

        # Quick info
        iface_lbl = QLabel("IFACE")
        iface_lbl.setObjectName("metaLabel")
        self._cmd_iface = QLabel("none")
        self._cmd_iface.setStyleSheet(
            "color: #6E7681; font-size: 12px; font-weight: 600;"
        )

        mode_lbl = QLabel("MODE")
        mode_lbl.setObjectName("metaLabel")
        self._cmd_mode = QLabel("IDLE")
        self._cmd_mode.setStyleSheet(
            "color: #6E7681; font-size: 12px; font-weight: 600;"
        )

        layout.addWidget(_sep_v())
        layout.addWidget(iface_lbl)
        layout.addWidget(self._cmd_iface)
        layout.addWidget(_sep_v())
        layout.addWidget(mode_lbl)
        layout.addWidget(self._cmd_mode)

        return bar

    def _focus_command_bar(self):
        """Focus the global command bar input."""
        self._cmd_input.setFocus()
        self._cmd_input.selectAll()

    def _on_cmd_submit(self):
        """Handle command bar submission."""
        text = self._cmd_input.text().strip()
        if not text:
            return
        if self._cmd_worker and self._cmd_worker.isRunning():
            show_toast(self, "Please wait — processing…", "info")
            return

        self._cmd_input.clear()
        self._cmd_status.setText("⏳ Processing…")
        self._cmd_status.setStyleSheet(
            "color: #BB8009; font-size: 12px;"
        )
        self._append_log(f"[Cmd] {text}", "INFO")

        # Also mirror to chat panel if it's visible
        if hasattr(self.chat_panel, '_add_bubble'):
            self.chat_panel._add_bubble(text, is_user=True)

        self._cmd_worker = _CmdWorker(self.orchestrator, text)
        self._cmd_worker.result_signal.connect(self._on_cmd_result)
        self._cmd_worker.error_signal.connect(self._on_cmd_error)
        self._cmd_worker.start()

    @pyqtSlot(str)
    def _on_cmd_result(self, result: str):
        self._cmd_status.setText("✓ Done")
        self._cmd_status.setStyleSheet(
            "color: #2EA043; font-size: 12px;"
        )
        QTimer.singleShot(3000, lambda: (
            self._cmd_status.setText(""),
            self._cmd_status.setStyleSheet("color: #3C3C3C; font-size: 12px;"),
        ))

        # Show result as toast (truncated)
        preview = result[:100].replace("\n", " ")
        if len(result) > 100:
            preview += "…"
        show_toast(self, preview, "info")

        # Mirror to chat panel
        if hasattr(self.chat_panel, '_add_bubble'):
            self.chat_panel._add_bubble(result, is_user=False)

        self._append_log(f"[Cmd] → {result[:200]}", "OK")

    @pyqtSlot(str)
    def _on_cmd_error(self, error: str):
        self._cmd_status.setText("✗ Error")
        self._cmd_status.setStyleSheet(
            "color: #F85149; font-size: 12px;"
        )
        show_toast(self, f"Command error: {error}", "error")
        self._append_log(f"[Cmd] Error: {error}", "CRIT")

    # ── Merged Config Tab ─────────────────────────────────────────────

    def _build_config_tab(self) -> QWidget:
        """Merge Setup + Troubleshoot into a single Config tab with sub-tabs."""
        config = QWidget()
        layout = QVBoxLayout(config)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        inner_tabs = QTabWidget()
        inner_tabs.setDocumentMode(True)

        self.setup_tab = SetupTab(self)
        self.troubleshoot_tab = TroubleshootTab(self)

        inner_tabs.addTab(self.setup_tab, "⚙️ Setup")
        inner_tabs.addTab(self.troubleshoot_tab, "🔧 Diagnostics")

        layout.addWidget(inner_tabs)
        return config

    # ── Status bar ────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self.lbl_status = QLabel("● IDLE")
        self.lbl_status.setObjectName("statusOk")
        bar.addWidget(self.lbl_status)

    # ── Signal wiring ─────────────────────────────────────────────────

    def _connect_signals(self):
        # Power menu is self-wired via QActions (no separate click handler)
        self._btn_logs.clicked.connect(self._show_log_viewer)
        self.progress_signal.connect(self._update_progress_ui)
        self.log_signal.connect(self._on_log_received)
        # Mirror chat panel output into the main log
        self.chat_panel.on_output.connect(
            lambda t: self._append_log(t, "INFO")
        )

    # ── Logging with timestamps + severity ───────────────────────────

    def _append_log(self, text: str, severity: str = "INFO"):
        self.log_signal.emit(str(text), severity)

    @pyqtSlot(str, str)
    def _on_log_received(self, text: str, severity: str):
        ts = datetime.now().strftime("%H:%M")
        sev = _SEV.get(severity.upper(), "INFO ")
        formatted = f"[{ts}]  {sev}  {text}"
        self.terminal.appendPlainText(formatted)

        sb = self.terminal.verticalScrollBar()
        # Keep animation instance persistently alive on `self` to prevent GC and enable smooth scrolling
        self._log_scroll_anim = QPropertyAnimation(sb, b"value", self)
        self._log_scroll_anim.setDuration(250)
        self._log_scroll_anim.setStartValue(sb.value())
        self._log_scroll_anim.setEndValue(sb.maximum())
        self._log_scroll_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._log_scroll_anim.start()

        self._log_count += 1
        self._lbl_log_count.setText(f"{self._log_count} lines")
        self._last_action = text[:48] + ("…" if len(text) > 48 else "")

    def _clear_log(self):
        self.terminal.clear()
        self._log_count = 0
        self._lbl_log_count.setText("0 lines")

    def _copy_log(self):
        QApplication.clipboard().setText(self.terminal.toPlainText())
        show_toast(self, "Log copied", "info")

    # ── State ─────────────────────────────────────────────────────────

    def _set_idle(self, idle: bool):
        if idle:
            self._status_pill.setText("● IDLE")
            self._status_pill.setObjectName("statusOk")
            self.lbl_status.setText("● IDLE")
            self.lbl_status.setObjectName("statusOk")
            self._op_label.setText("")
            self.progress_bar.setVisible(False)
            self._current_mode = "IDLE"
        else:
            self._status_pill.setText("● RUNNING")
            self._status_pill.setObjectName("statusWarn")
            self.lbl_status.setText("● RUNNING")
            self.lbl_status.setObjectName("statusWarn")
            self.progress_bar.setVisible(True)
            self._current_mode = "RUNNING"
        for lbl in (self._status_pill, self.lbl_status):
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        self._cmd_mode.setText(self._current_mode)

    def _set_operation(self, operation: str):
        """Set the active operation context in the header."""
        self._current_operation = operation
        self._op_label.setText(operation)
        if operation:
            self._op_label.setStyleSheet(
                "font-size: 11px; color: #BB8009;"
            )
        else:
            self._op_label.setStyleSheet(
                "font-size: 11px; color: #3C3C3C;"
            )

    # ── Timers ────────────────────────────────────────────────────────

    def _tick(self):
        self.uptime_seconds += 1
        h = self.uptime_seconds // 3600
        m = (self.uptime_seconds % 3600) // 60
        s = self.uptime_seconds % 60
        up_str = f"{h:02d}:{m:02d}:{s:02d}"
        self._get_hdr_val(self._hdr_up).setText(up_str)

        if self.active_interface:
            self._get_hdr_val(self._hdr_iface).setText(self.active_interface)
            self._cmd_iface.setText(self.active_interface)

    def _refresh_stats(self):
        try:
            summary = self.orchestrator.get_loot_summary()
            n_loot = summary.get("total_handshakes", 0)
            n_keys = summary.get("total_cracked", 0)
            self._get_hdr_val(self._hdr_keys).setText(str(n_keys))
            if n_keys != self._key_count and n_keys > 0:
                self._get_hdr_val(self._hdr_keys).setStyleSheet(
                    "color: #0078D4; font-size: 15px; font-weight: 700;"
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
        # Update operation context
        self._set_operation(f"{phase}  [{num}/{total}]")
        if num >= total:
            QTimer.singleShot(3000, lambda: self._set_idle(True))

    # ── Public helpers for tab updates ────────────────────────────────

    def set_ap_count(self, n: int):
        self._ap_count = n
        self._get_hdr_val(self._hdr_aps).setText(str(n))

    # ── Actions — Lifecycle ────────────────────────────────────────────

    def _is_tools_running(self) -> bool:
        """Check if JAMES has active tool processes or is mid-operation."""
        # Check mode state
        if self._current_mode != "IDLE":
            return True
        # Check if background process registry has entries
        try:
            if hasattr(self.orchestrator, 'layer'):
                registry = getattr(self.orchestrator.layer, '_bg_procs', [])
                if registry:
                    return True
        except Exception:
            pass
        return False

    def restart_james(self):
        """Soft restart — relaunch JAMES without killing tools/interfaces."""
        reply = QMessageBox.question(
            self,
            "Restart JAMES",
            "Restart the JAMES application?\n\n"
            "This will close and relaunch the GUI.\n"
            "Network interfaces will NOT be changed.\n"
            "Running background tools will be orphaned.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._append_log("🔄 Restarting JAMES…", "WARN")

        # Get the command used to launch this process
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        args = sys.argv[1:]

        # Launch new instance then exit
        try:
            subprocess.Popen(
                [python, script] + args,
                start_new_session=True,
            )
            # Force-close without triggering closeEvent cleanup
            self._force_quit = True
            QApplication.quit()
        except Exception as e:
            show_toast(self, f"Restart failed: {e}", "error")
            self._append_log(f"❌ Restart failed: {e}", "CRIT")

    def emergency_stop(self):
        """Hard stop — kill all tools, restore interfaces, flush iptables."""
        reply = QMessageBox.question(
            self,
            "🛑 Emergency Stop",
            "Kill ALL pentesting tools and restore networking?\n\n"
            "This will:\n"
            "  • Kill all background tool processes\n"
            "  • Restore Wi-Fi interfaces to managed mode\n"
            "  • Flush iptables rules\n"
            "  • Restart NetworkManager\n\n"
            "JAMES will remain open.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._set_idle(False)
            self._set_operation("Emergency Stop")
            self._append_log("🛑 Emergency Stop initiated", "CRIT")
            self.worker = WorkerThread(self.orchestrator.kill_james)
            self.worker.finished.connect(self._on_emergency_stop_done)
            self.worker.start()

    def _on_emergency_stop_done(self, result):
        self._set_idle(True)
        self._set_operation("")
        if isinstance(result, Exception):
            show_toast(self, f"Stop error: {result}", "error")
        else:
            show_toast(self, "Emergency stop complete — network restored", "success")
            self._append_log("✅ Emergency stop complete", "OK")

    def reboot_pc(self):
        """Reboot the entire system with confirmation."""
        reply = QMessageBox.warning(
            self,
            "⚡ Reboot PC",
            "Reboot this computer?\n\n"
            "This will:\n"
            "  • Run Emergency Stop first (kill tools, restore network)\n"
            "  • Then reboot the system\n\n"
            "Unsaved data in other applications may be lost.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Second confirmation — this is destructive
        reply2 = QMessageBox.critical(
            self,
            "⚡ Confirm Reboot",
            "Are you sure? The system will reboot NOW.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply2 != QMessageBox.Yes:
            return

        self._append_log("⚡ Rebooting system…", "CRIT")
        self._set_operation("Rebooting…")

        # Run emergency stop first, then reboot
        def _stop_then_reboot():
            try:
                self.orchestrator.kill_james()
            except Exception:
                pass
            return "reboot"

        self.worker = WorkerThread(_stop_then_reboot)
        self.worker.finished.connect(self._do_reboot)
        self.worker.start()

    def _do_reboot(self, result):
        """Execute the actual system reboot."""
        try:
            subprocess.run(
                ["systemctl", "reboot"],
                timeout=10,
            )
        except Exception:
            try:
                subprocess.run(["reboot"], timeout=10)
            except Exception as e:
                show_toast(self, f"Reboot failed: {e}", "error")

    # ── Legacy alias for tabs/troubleshoot ─────────────────────────

    def kill_james(self):
        """Legacy alias — redirects to emergency_stop."""
        self.emergency_stop()

    # ── Smart close ───────────────────────────────────────────────

    def closeEvent(self, event):
        """Smart close: skip cleanup if nothing is running."""
        # Force-quit path (from restart_james)
        if getattr(self, '_force_quit', False):
            event.accept()
            return

        if self._is_tools_running():
            reply = QMessageBox.question(
                self,
                "Tools Running",
                "JAMES has active background tools.\n\n"
                "• Yes — Run Emergency Stop then close\n"
                "• No — Close without stopping (tools keep running)\n"
                "• Cancel — Don't close",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.Yes:
                try:
                    self.orchestrator.kill_james()
                except Exception:
                    pass
            # QMessageBox.No → close without cleanup
        event.accept()

    # ── Setup wizard ──────────────────────────────────────────────────

    def _show_setup_wizard(self):
        wizard = SetupWizard(self.orchestrator, self)
        wizard.exec_()

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
        log_files = sorted(
            log_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for lf in log_files:
            combo.addItem(
                f"{lf.name}  ({lf.stat().st_size / 1024:.0f} KB)", str(lf)
            )
        btn_reload = QPushButton("Reload")
        btn_reload.setFixedWidth(72)
        sel.addWidget(combo, stretch=1)
        sel.addWidget(btn_reload)
        layout.addLayout(sel)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setStyleSheet(LOG_STYLE)
        viewer.setFont(QFont("JetBrains Mono", 13))
        layout.addWidget(viewer)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.close)
        layout.addWidget(btns)

        def load():
            path = combo.currentData()
            if path:
                try:
                    viewer.setPlainText(
                        Path(path).read_text(
                            encoding="utf-8", errors="replace"
                        )
                    )
                    viewer.verticalScrollBar().setValue(
                        viewer.verticalScrollBar().maximum()
                    )
                except Exception as e:
                    viewer.setPlainText(f"Error: {e}")

        combo.currentIndexChanged.connect(lambda _: load())
        btn_reload.clicked.connect(load)
        if log_files:
            load()
        dlg.exec_()
