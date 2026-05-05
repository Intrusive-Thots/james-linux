"""
JAMES Dashboard — main PyQt5 window.

Panels:
  • Agent Chat      — conversational AI interface
  • Dashboard       — system status + terminal
  • One-Click Tests — categorised skill browser with search
  • Recon           — nmap scan results
  • Wi-Fi           — monitor mode, deauth, autopwn
  • Cracking        — WPA + hash cracking
  • Log             — task history export
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QGroupBox,
    QGridLayout, QComboBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QStatusBar, QFrame, QScrollArea,
    QToolButton, QSizePolicy, QShortcut, QAction, QApplication, QMenu,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor, QKeySequence

from james.core.orchestrator import Orchestrator
from james.gui.chat_panel import ChatPanel
from james.gui.toast import show_toast

# Skill categories for the One-Click Tests tab
SKILL_CATEGORIES = {
    "🔍 Recon": ["network_sweep", "arp_scan_discover", "full_recon", "stealth_recon",
                 "masscan_sweep", "osint_recon", "dns_zone_transfer", "ad_domain_recon"],
    "📡 Wi-Fi": ["wifi_audit", "wifi_full_auto", "wifi_dos", "wifi_sniff",
                 "handshake_harvest", "evil_twin", "pmkid_attack",
                 "wps_bruteforce", "wps_pixie"],
    "🌐 Web": ["web_recon", "full_web_audit", "dir_bruteforce", "sql_injection",
              "ssl_audit", "waf_bypass_recon"],
    "🔓 Cracking": ["brute_ssh", "brute_ftp", "brute_multi", "password_spray"],
    "🕸️ Network": ["mitm_arp", "responder_poison", "packet_analysis", "smb_audit"],
    "💣 Exploit": ["vuln_scan", "msf_exploit", "reverse_shell", "post_exploit",
                   "privesc_linux", "pivot_tunnel", "full_chain"],
    "🎯 One-Click": ["wifi_blitz", "network_dominate", "web_pwn",
                    "stealth_recon", "evil_twin_auto"],
}


# ── worker thread for non-blocking operations ───────────────────

class WorkerThread(QThread):
    """Run an orchestrator action off the main thread."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._func(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):

    MAX_TERMINAL_LINES = 5000  # prevent OOM from tool output spam

    append_output = pyqtSignal(str)   # thread-safe terminal append
    refresh_log = pyqtSignal()        # thread-safe log table refresh

    def __init__(self):
        super().__init__()
        self.orch = Orchestrator()
        self.orch.on_task_update = self._on_task_update
        self._workers: list[WorkerThread] = []
        self.known_targets = set()
        self.target_comboboxes = []
        self._targets_file = Path.home() / ".james" / "loot" / "known_targets.json"
        self._load_targets()

        self.setWindowTitle("JAMES — Linux Pentesting Agent")
        self.setMinimumSize(1100, 720)

        # ── Global dark theme stylesheet ────────────────────────
        self.setStyleSheet("""
            /* ── Base ── */
            QMainWindow, QWidget {
                background-color: #0a0f1a;
                color: #c8d6e5;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
            }

            /* ── Tab bar ── */
            QTabWidget::pane {
                border: none;
                background: #0a0f1a;
            }
            QTabBar::tab {
                background: #0b1120;
                color: #5a7a9a;
                border: 1px solid #141e30;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #0d1a2a;
                color: #00f0ff;
                border-color: #00f0ff40;
                border-bottom: 2px solid #00f0ff;
            }
            QTabBar::tab:hover:!selected {
                background: #101828;
                color: #8ab0d0;
            }

            /* ── Buttons ── */
            QPushButton {
                background: #0d1528;
                color: #8a9abf;
                border: 1px solid #1a2e48;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #142040;
                color: #00f0ff;
                border-color: #00f0ff60;
            }
            QPushButton:pressed {
                background: #00f0ff20;
            }
            QPushButton:disabled {
                background: #080c14;
                color: #2a3a4a;
                border-color: #0f1520;
            }
            QPushButton#dangerBtn {
                background: #1a0808;
                color: #ff4757;
                border-color: #ff475740;
            }
            QPushButton#dangerBtn:hover {
                background: #2d0a0a;
                border-color: #ff4757;
            }

            /* ── Inputs ── */
            QLineEdit, QComboBox {
                background: #0b1120;
                color: #c8d6e5;
                border: 1px solid #1a2e48;
                border-radius: 4px;
                padding: 5px 8px;
                selection-background-color: #00f0ff30;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #00f0ff60;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: #0b1120;
                color: #c8d6e5;
                border: 1px solid #1a2e48;
                selection-background-color: #00f0ff30;
                selection-color: #00f0ff;
            }

            /* ── Tables ── */
            QTableWidget {
                background: #060a12;
                alternate-background-color: #0a0f18;
                gridline-color: #141e30;
                border: 1px solid #141e30;
                border-radius: 4px;
                selection-background-color: #00f0ff15;
                selection-color: #00f0ff;
            }
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #0f1520;
            }
            QTableWidget::item:selected {
                background: #00f0ff15;
                color: #00f0ff;
            }
            QHeaderView::section {
                background: #0b1120;
                color: #5a8aaa;
                border: none;
                border-bottom: 2px solid #1a2e48;
                border-right: 1px solid #141e30;
                padding: 6px 8px;
                font-weight: bold;
                font-size: 11px;
            }

            /* ── Group boxes ── */
            QGroupBox {
                border: 1px solid #1a2e48;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 12px;
                color: #5a8aaa;
            }

            /* ── Scrollbars ── */
            QScrollBar:vertical {
                background: #080c14;
                width: 10px;
                border: none;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #1a2e48;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2a4a6a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #080c14;
                height: 10px;
                border: none;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #1a2e48;
                min-width: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #2a4a6a;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
                width: 0px;
            }

            /* ── PlainTextEdit (terminal) ── */
            QPlainTextEdit {
                background: #060a12;
                color: #c8d6e5;
                border: 1px solid #141e30;
                border-radius: 4px;
                font-family: 'JetBrains Mono', monospace;
            }

            /* ── Status bar ── */
            QStatusBar {
                background: #080c14;
                color: #3a5a7a;
                border-top: 1px solid #141e30;
                font-size: 11px;
            }
            QStatusBar::item {
                border: none;
            }

            /* ── Labels ── */
            QLabel {
                background: transparent;
            }

            /* ── Splitter ── */
            QSplitter::handle {
                background: #141e30;
                width: 2px;
            }

            /* ── Tool tips ── */
            QToolTip {
                background: #0d1a2a;
                color: #c8d6e5;
                border: 1px solid #00f0ff40;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }

            /* ── Message Box ── */
            QMessageBox {
                background: #0a0f1a;
            }
            QMessageBox QLabel {
                color: #c8d6e5;
            }

            /* ── Scroll Area ── */
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self._build_ui()
        self.append_output.connect(self._do_append)
        self.refresh_log.connect(self._refresh_log_table)
        
        self.orch.on_print = self._term_print

        # Share known_targets with agent for reporting
        self.chat_panel.agent._gui_known_targets = self.known_targets

        # initial system check and load interfaces
        QTimer.singleShot(300, self._run_system_check)
        QTimer.singleShot(400, self._refresh_interfaces)

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header bar
        header = self._make_header()
        root.addWidget(header)

        # context badge strip
        self.ctx_strip = self._make_context_strip()
        root.addWidget(self.ctx_strip)

        # tab widget
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # AI Agent chat — the primary interface (with Quick Actions sidebar)
        self.chat_panel = ChatPanel(self.orch)
        agent_tab = self._make_agent_tab()
        self.tabs.addTab(agent_tab, "🤖 Agent")
        self.tabs.setTabToolTip(0, "Conversational AI — talk to JAMES in plain English")

        self.tabs.addTab(self._make_dashboard_tab(), "⚡ Dashboard")
        self.tabs.setTabToolTip(1, "System status + interactive terminal")

        self.tabs.addTab(self._make_oneclick_tab(), "🧪 Skills")
        self.tabs.setTabToolTip(2, "Browse and run automated skill workflows")

        self.tabs.addTab(self._make_recon_tab(), "🔍 Recon")
        self.tabs.setTabToolTip(3, "nmap scanning — quick and full port scans")

        self.tabs.addTab(self._make_wifi_tab(), "📡 Wi-Fi")
        self.tabs.setTabToolTip(4, "Wi-Fi auditing — monitor mode, deauth, AutoPwn")

        self.tabs.addTab(self._make_cracking_tab(), "🔓 Cracking")
        self.tabs.setTabToolTip(5, "WPA handshake + hash cracking")

        self.tabs.addTab(self._make_log_tab(), "📋 Log")
        self.tabs.setTabToolTip(6, "Task history and JSON export")

        # status bar with activity pulse
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Target display in status bar
        self._status_target = QLabel("🎯 No target")
        self._status_target.setStyleSheet(
            "color: #3a5a7a; font-size: 10px; font-weight: bold; padding: 0 8px;"
        )
        self.status.addWidget(self._status_target)

        # Worker count
        self._status_workers = QLabel("⚙ 0 workers")
        self._status_workers.setStyleSheet(
            "color: #2a4a5a; font-size: 10px; padding: 0 8px;"
        )
        self.status.addWidget(self._status_workers)

        # Uptime
        self._uptime_seconds = 0
        self._status_uptime = QLabel("⏱ 0:00:00")
        self._status_uptime.setStyleSheet(
            "color: #1a3a5a; font-size: 10px; padding: 0 8px;"
        )
        self.status.addWidget(self._status_uptime)
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._tick_uptime)
        self._uptime_timer.start(1000)

        self.status.showMessage("JAMES ready.", 3000)

        # Activity pulse indicator (animated during ops)
        self._activity_label = QLabel("  ● IDLE")
        self._activity_label.setStyleSheet(
            "color: #2a4a5a; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        self.status.addPermanentWidget(self._activity_label)
        self._active_ops = 0

        # Shortcut hints
        shortcut_hint = QLabel("Ctrl+1-7: Tabs │ Ctrl+K: Kill │ Ctrl+R: Reboot │ Ctrl+/: Chat")
        shortcut_hint.setStyleSheet(
            "color: #1a3050; font-size: 10px; padding-right: 12px;"
        )
        self.status.addPermanentWidget(shortcut_hint)

        # Tab badge counters (track unread events per tab)
        self._tab_badges: dict[int, int] = {}
        self._tab_base_labels = {}
        for i in range(self.tabs.count()):
            self._tab_base_labels[i] = self.tabs.tabText(i)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Refresh context badges every 5 seconds
        self._ctx_timer = QTimer(self)
        self._ctx_timer.timeout.connect(self._refresh_context_strip)
        self._ctx_timer.start(5000)

    def _setup_shortcuts(self):
        """Register keyboard shortcuts."""
        # Tab switching: Ctrl+1 through Ctrl+7
        for i in range(min(7, self.tabs.count())):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            shortcut.activated.connect(lambda idx=i: self.tabs.setCurrentIndex(idx))

        # Ctrl+K: Kill James
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(self._do_kill_james)

        # Ctrl+R: Reboot James
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._do_reboot_james)

        # Ctrl+L: Clear terminal
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(
            lambda: self.terminal.clear()
        )

        # Ctrl+/: Focus agent chat input
        QShortcut(QKeySequence("Ctrl+/"), self).activated.connect(self._focus_chat)

        # Escape: Return to agent tab
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            lambda: self.tabs.setCurrentIndex(0)
        )

    def _focus_chat(self):
        """Focus the agent chat input field."""
        self.tabs.setCurrentIndex(0)
        self.chat_panel.input_field.setFocus()

    def _notify_tab(self, tab_index: int):
        """Add a notification badge to a tab."""
        current = self.tabs.currentIndex()
        if current == tab_index:
            return  # don't badge the active tab
        count = self._tab_badges.get(tab_index, 0) + 1
        self._tab_badges[tab_index] = count
        base = self._tab_base_labels.get(tab_index, self.tabs.tabText(tab_index))
        self.tabs.setTabText(tab_index, f"{base} ({count})")

    def _on_tab_changed(self, index: int):
        """Clear badge when user switches to a tab."""
        if index in self._tab_badges:
            del self._tab_badges[index]
            base = self._tab_base_labels.get(index, "")
            if base:
                self.tabs.setTabText(index, base)

    def _start_activity(self, label: str = "WORKING"):
        """Show activity pulse in status bar."""
        self._active_ops += 1
        self._activity_label.setText(f"  ◉ {label}")
        self._activity_label.setStyleSheet(
            "color: #00f0ff; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        self._update_worker_count()

    def _stop_activity(self):
        """Return to idle when all ops complete."""
        self._active_ops = max(0, self._active_ops - 1)
        if self._active_ops == 0:
            self._activity_label.setText("  ● IDLE")
            self._activity_label.setStyleSheet(
                "color: #2a4a5a; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
            )
        self._update_worker_count()

    def _tick_uptime(self):
        """Increment session uptime counter."""
        self._uptime_seconds += 1
        h = self._uptime_seconds // 3600
        m = (self._uptime_seconds % 3600) // 60
        s = self._uptime_seconds % 60
        self._status_uptime.setText(f"⏱ {h}:{m:02d}:{s:02d}")

        # Periodically update target in status bar
        try:
            target = self.chat_panel.agent.context.get("target", "")
            if target:
                self._status_target.setText(f"🎯 {target}")
                self._status_target.setStyleSheet(
                    "color: #00f0ff; font-size: 10px; font-weight: bold; padding: 0 8px;"
                )
            else:
                self._status_target.setText("🎯 No target")
                self._status_target.setStyleSheet(
                    "color: #3a5a7a; font-size: 10px; font-weight: bold; padding: 0 8px;"
                )
        except Exception:
            pass

    def _update_worker_count(self):
        """Update worker count display in status bar."""
        active = len([w for w in self._workers if w.isRunning()])
        self._status_workers.setText(f"⚙ {active} worker{'s' if active != 1 else ''}")
        if active > 0:
            self._status_workers.setStyleSheet(
                "color: #00f0ff; font-size: 10px; padding: 0 8px; font-weight: bold;"
            )
        else:
            self._status_workers.setStyleSheet(
                "color: #2a4a5a; font-size: 10px; padding: 0 8px;"
            )

    # ── Agent tab with Quick Actions sidebar ───────────────────

    def _make_agent_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self.chat_panel, 1)

        # Quick Actions panel
        qa = self._make_quick_actions_panel()
        lay.addWidget(qa)
        return w

    def _make_quick_actions_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(200)
        panel.setStyleSheet("""
            QWidget { background-color: #080c14; border-left: 1px solid #141e30; }
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(8)

        title = QLabel("QUICK ACTIONS")
        title.setStyleSheet(
            "color: #2a4a6a; font-size: 10px; font-weight: bold; "
            "letter-spacing: 2px; background: transparent;"
        )
        lay.addWidget(title)

        actions = [
            ("🔍 Scan Target",     "scan {target}",      "scan <IP/range>"),
            ("📡 List Interfaces", "list interfaces",     None),
            ("⚙️  System Check",   "status",              None),
            ("📋 List Skills",     "list skills",         None),
            ("📄 Report",          "report",              None),
            ("❓ Help",            "help",                None),
        ]

        for label, cmd, placeholder in actions:
            btn = QPushButton(label)
            btn.setToolTip(placeholder or cmd)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0b1120;
                    color: #7a9abf;
                    border: 1px solid #141e30;
                    border-radius: 6px;
                    padding: 8px 10px;
                    text-align: left;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #101e30;
                    color: #00f0ff;
                    border-color: #1a3050;
                }
            """)
            btn.clicked.connect(lambda _, c=cmd: self._qa_send(c))
            lay.addWidget(btn)

        # One-click hack shortcuts
        hack_sep = QLabel("ONE-CLICK HACKS")
        hack_sep.setStyleSheet(
            "color: #ff6b35; font-size: 10px; font-weight: bold; "
            "letter-spacing: 2px; background: transparent; margin-top: 10px;"
        )
        lay.addWidget(hack_sep)

        hack_actions = [
            ("🔥 Wi-Fi Blitz",     "wifi blitz"),
            ("💀 Net Dominate",    "network dominate {target}"),
            ("🌐 Web Pwn",        "web pwn {target}"),
            ("👁️ Stealth Recon",  "stealth recon {target}"),
            ("🔑 Show Loot",      "show loot"),
        ]

        for label, cmd in hack_actions:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1a0d00;
                    color: #ff6b35;
                    border: 1px solid #ff6b3530;
                    border-radius: 6px;
                    padding: 6px 10px;
                    text-align: left;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #2a1a00;
                    border-color: #ff6b35;
                }
            """)
            btn.clicked.connect(lambda _, c=cmd: self._qa_send(c))
            lay.addWidget(btn)

        lay.addStretch()

        # Current context display
        ctx_title = QLabel("SESSION CONTEXT")
        ctx_title.setStyleSheet(
            "color: #2a4a6a; font-size: 10px; font-weight: bold; "
            "letter-spacing: 2px; background: transparent; margin-top: 8px;"
        )
        lay.addWidget(ctx_title)

        self.qa_ctx_label = QLabel("(none set)")
        self.qa_ctx_label.setWordWrap(True)
        self.qa_ctx_label.setStyleSheet(
            "color: #3a5a7a; font-size: 11px; background: transparent; line-height: 1.6;"
        )
        lay.addWidget(self.qa_ctx_label)
        return panel

    def _qa_send(self, cmd: str):
        """Inject a quick-action command into the chat panel, using context for targets."""
        if "{target}" in cmd:
            target = self.chat_panel.agent.context.get("target", "")
            if not target and self.known_targets:
                target = sorted(self.known_targets)[0]
            if target:
                cmd = cmd.replace("{target}", target)
            else:
                show_toast(self, "Set a target first: type 'set target <IP>'", "warning", 2500)
                self.tabs.setCurrentIndex(0)
                self.chat_panel.input_field.setText("set target ")
                self.chat_panel.input_field.setFocus()
                return
        if "{interface}" in cmd:
            iface = self.chat_panel.agent.context.get("interface", "")
            if iface:
                cmd = cmd.replace("{interface}", iface)
            else:
                cmd = cmd.replace(" {interface}", "")  # let agent auto-detect

        self.tabs.setCurrentIndex(0)
        self.chat_panel.input_field.setText(cmd)
        self.chat_panel._on_send()

    # ── Context badge strip ──────────────────────────────────────

    def _make_context_strip(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(32)
        w.setStyleSheet("""
            QWidget { background-color: #080c14; border-bottom: 1px solid #0f1a28; }
            QLabel { background: transparent; }
        """)
        self._ctx_layout = QHBoxLayout(w)
        self._ctx_layout.setContentsMargins(16, 4, 16, 4)
        self._ctx_layout.setSpacing(8)

        prefix = QLabel("CTX:")
        prefix.setStyleSheet("color: #1a3050; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self._ctx_layout.addWidget(prefix)
        self._ctx_layout.addStretch()
        self._ctx_badges: dict[str, QLabel] = {}
        return w

    def _refresh_context_strip(self):
        """Update context badges from the chat panel's agent context."""
        try:
            ctx = self.chat_panel.agent.context
        except AttributeError:
            return

        interesting = ["target", "interface", "monitor_interface", "wordlist", "domain", "target_bssid", "target_ssid"]
        colors = {
            "target": "#00f0ff", "domain": "#00f0ff",
            "interface": "#00ff88", "monitor_interface": "#ffcc00",
            "wordlist": "#aa88ff",
        }

        for key in interesting:
            val = ctx.get(key)
            if val:
                color = colors.get(key, "#5a9abf")
                if key not in self._ctx_badges:
                    lbl = QLabel()
                    lbl.setStyleSheet(f"""
                        color: {color}; font-size: 10px; font-weight: bold;
                        background: {color}18; border: 1px solid {color}40;
                        border-radius: 10px; padding: 1px 10px;
                    """)
                    self._ctx_layout.insertWidget(
                        self._ctx_layout.count() - 1, lbl
                    )
                    self._ctx_badges[key] = lbl
                short_val = val if len(val) < 30 else val[-27:] + "…"
                self._ctx_badges[key].setText(f"{key}: {short_val}")
                self._ctx_badges[key].setVisible(True)
            else:
                if key in self._ctx_badges:
                    self._ctx_badges[key].setVisible(False)

        # Live session stats
        stats = {
            "targets": (f"🎯 {len(self.known_targets)}", "#00f0ff"),
            "tasks": (f"📋 {len(self.orch.export_log())}", "#5a9abf"),
        }
        try:
            loot = self.orch.get_loot_summary()
            if loot["cracked_count"] > 0:
                stats["loot"] = (f"🔑 {loot['cracked_count']}", "#00ff88")
        except Exception:
            pass

        # Network guard status
        try:
            guard = self.orch.net_guard.get_status()
            if guard["enabled"]:
                if guard["is_wifi"]:
                    ssid = guard["ssid"] or "Wi-Fi"
                    stats["guard"] = (f"🛡️ {ssid}", "#00ff88")
                elif guard["connected"]:
                    stats["guard"] = ("🛡️ Wired", "#5a9abf")
                else:
                    stats["guard"] = ("🛡️ No conn", "#ff5555")
            # Update Wi-Fi tab indicator
            if hasattr(self, "net_guard_label"):
                if guard["is_wifi"] and guard["bssid"]:
                    self.net_guard_label.setText("🛡️")
                    self.net_guard_label.setToolTip(
                        f"Protected: {guard['ssid']} ({guard['bssid']})\n"
                        f"Deauth & monitor mode blocked on {guard['interface']}"
                    )
                    self.net_guard_label.setStyleSheet(
                        "color: #00ff88; font-size: 14px; background: transparent; padding: 0 4px;"
                    )
                elif guard["connected"]:
                    self.net_guard_label.setText("🔌")
                    self.net_guard_label.setToolTip(
                        f"Wired connection via {guard['interface']}\n"
                        f"Wi-Fi attacks unrestricted on other adapters"
                    )
                    self.net_guard_label.setStyleSheet(
                        "color: #5a9abf; font-size: 14px; background: transparent; padding: 0 4px;"
                    )
                else:
                    self.net_guard_label.setText("⚠️")
                    self.net_guard_label.setToolTip("No connection detected — guard inactive")
                    self.net_guard_label.setStyleSheet(
                        "color: #ff5555; font-size: 14px; background: transparent; padding: 0 4px;"
                    )
        except Exception:
            pass

        for key, (text, color) in stats.items():
            stat_key = f"_stat_{key}"
            if stat_key not in self._ctx_badges:
                lbl = QLabel()
                lbl.setStyleSheet(f"""
                    color: {color}; font-size: 10px; font-weight: bold;
                    background: {color}10; border: 1px solid {color}30;
                    border-radius: 10px; padding: 1px 8px;
                """)
                self._ctx_layout.insertWidget(
                    self._ctx_layout.count() - 1, lbl
                )
                self._ctx_badges[stat_key] = lbl
            self._ctx_badges[stat_key].setText(text)

        # Also update quick actions sidebar context
        try:
            lines = [f"{k}: {v}" for k, v in ctx.items() if v][:5]
            self.qa_ctx_label.setText("\n".join(lines) if lines else "(none set)")
        except Exception:
            pass

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(60)
        w.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0b1120, stop:0.5 #0d1528, stop:1 #0b1120);
                border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff00, stop:0.3 #00f0ff, stop:0.7 #00ff88, stop:1 #00f0ff00);
            }
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel("⚡ JAMES")
        title.setObjectName("headerLabel")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00f0ff; letter-spacing: 4px; background: transparent;")
        lay.addWidget(title)

        subtitle = QLabel("Autonomous Pentesting Agent")
        subtitle.setStyleSheet("color: #3a5a7a; font-size: 11px; letter-spacing: 1px; background: transparent;")
        lay.addWidget(subtitle)
        lay.addStretch()

        # version badge
        ver = QLabel("v0.5.0")
        ver.setStyleSheet("""
            background-color: #00f0ff18;
            color: #00f0ff;
            border: 1px solid #00f0ff40;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        lay.addWidget(ver)

        # status indicator
        self.status_indicator = QLabel("● ONLINE")
        self.status_indicator.setStyleSheet("""
            color: #00ff88;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        lay.addWidget(self.status_indicator)

        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #3a5a7a; font-size: 12px; background: transparent;")
        lay.addWidget(self.clock_label)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # REBOOT JAMES button
        self.reboot_btn = QPushButton("🔄 REBOOT")
        self.reboot_btn.setToolTip("Reboot JAMES: kill tools, clear context, re-init everything")
        self.reboot_btn.setFixedHeight(32)
        self.reboot_btn.setFixedWidth(100)
        self.reboot_btn.setStyleSheet("""
            QPushButton {
                background: #0d1a2a;
                color: #00f0ff;
                border: 1px solid #00f0ff40;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #142540;
                border-color: #00f0ff;
                color: #40ffff;
            }
            QPushButton:pressed {
                background: #00f0ff;
                color: #000000;
            }
        """)
        self.reboot_btn.clicked.connect(self._do_reboot_james)
        lay.addWidget(self.reboot_btn)

        # KILL JAMES button — emergency stop
        self.kill_btn = QPushButton("🛑 KILL")
        self.kill_btn.setToolTip("Kill all tools, restore interfaces, reconnect Wi-Fi")
        self.kill_btn.setFixedHeight(32)
        self.kill_btn.setFixedWidth(80)
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background: #1a0808;
                color: #ff4757;
                border: 1px solid #ff475740;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #2d0a0a;
                border-color: #ff4757;
                color: #ff6b7a;
            }
            QPushButton:pressed {
                background: #ff4757;
                color: #ffffff;
            }
        """)
        self.kill_btn.clicked.connect(self._do_kill_james)
        lay.addWidget(self.kill_btn)

        return w

    # ── Dashboard tab ───────────────────────────────────────────

    def _make_dashboard_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── LEFT: Command Palette (replaces the need for typing) ──
        palette_panel = QWidget()
        palette_panel.setFixedWidth(320)
        palette_panel.setStyleSheet("""
            QWidget { background-color: #060a12; border-right: 1px solid #141e30; }
        """)
        p_lay = QVBoxLayout(palette_panel)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(0)

        # Palette header
        p_header = QLabel("  ⚡ COMMAND PALETTE")
        p_header.setFixedHeight(36)
        p_header.setStyleSheet(
            "color: #00f0ff; font-size: 11px; font-weight: bold; "
            "letter-spacing: 2px; background: #080c18; border-bottom: 1px solid #141e30;"
        )
        p_lay.addWidget(p_header)

        # Target selector at top of palette
        target_row = QWidget()
        target_row.setStyleSheet("background: #0a0f1a; border-bottom: 1px solid #141e30;")
        target_row.setFixedHeight(44)
        tr_lay = QHBoxLayout(target_row)
        tr_lay.setContentsMargins(12, 6, 12, 6)
        tr_lay.addWidget(QLabel("🎯"))
        self.palette_target = QComboBox()
        self.palette_target.setEditable(True)
        self.palette_target.lineEdit().setPlaceholderText("Target (IP / domain)")
        self.palette_target.setMinimumWidth(200)
        self.target_comboboxes.append(self.palette_target)
        if self.known_targets:
            self.palette_target.addItems(sorted(list(self.known_targets)))
        tr_lay.addWidget(self.palette_target)
        p_lay.addWidget(target_row)

        # Scrollable button grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        grid = QVBoxLayout(btn_container)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(6)

        # Define all clickable command categories
        PALETTE_SECTIONS = [
            ("🔍 RECON", "#00f0ff", [
                ("Quick Scan",      "quick scan",       "fast nmap scan"),
                ("Full Scan",       "full scan",        "deep service + script scan"),
                ("OS Detect",       "os detect",        "OS fingerprinting"),
                ("Masscan",         "masscan",          "65535 port scan"),
                ("Stealth Recon",   "stealth recon",    "passive OSINT chain"),
                ("Net Sweep",       "run skill network_sweep", "ARP + ping sweep"),
            ]),
            ("📡 WI-FI", "#ff6b35", [
                ("List Interfaces", "list interfaces",  None),
                ("Scan APs",        "scan aps",         "nearby Wi-Fi networks"),
                ("Wi-Fi Blitz",     "wifi blitz",       "PMKID + handshake + WPS"),
                ("AutoPwn",         "autopwn",          "end-to-end Wi-Fi crack"),
                ("Show Loot",       "show loot",        "cracked keys"),
            ]),
            ("🌐 WEB", "#a855f7", [
                ("Web Scan",        "nikto",            "Nikto vulnerability scan"),
                ("Dir Brute",       "gobuster",         "directory enumeration"),
                ("SQL Inject",      "sqlmap",           "automated SQL injection"),
                ("SSL Audit",       "ssl scan",         "TLS/SSL check"),
                ("WAF Detect",      "waf detect",       "firewall detection"),
                ("Web Pwn",         "web pwn",          "full web attack chain"),
            ]),
            ("🕵️ OSINT", "#5a9abf", [
                ("OSINT Harvest",   "osint",            "emails + subdomains"),
                ("WHOIS",           "whois",            "domain registration"),
                ("DNS Enum",        "dns enum",         "DNS records"),
            ]),
            ("💣 EXPLOIT", "#ff4757", [
                ("Brute SSH",       "brute",            "Hydra brute-force"),
                ("MITM",            "mitm",             "ARP poisoning"),
                ("Responder",       "responder",        "LLMNR/NBT-NS capture"),
                ("Reverse Shell",   "reverse shell",    "payload + listener"),
                ("Net Dominate",    "network dominate", "full network attack chain"),
            ]),
            ("⚙️ SYSTEM", "#2a6a4a", [
                ("System Check",    "status",           "tool status"),
                ("List Skills",     "list skills",      "38 skill workflows"),
                ("List Wordlists",  "list wordlists",   "wordlist arsenal"),
                ("Net Guard",       "net guard",        "protection status"),
                ("Show Primers",    "show primers",     "AI guidance"),
                ("Report",          "report",           "HTML session report"),
            ]),
        ]

        for section_name, section_color, buttons in PALETTE_SECTIONS:
            # Section header
            sec_lbl = QLabel(f"  {section_name}")
            sec_lbl.setFixedHeight(24)
            sec_lbl.setStyleSheet(
                f"color: {section_color}; font-size: 10px; font-weight: bold; "
                f"letter-spacing: 2px; background: transparent; margin-top: 4px;"
            )
            grid.addWidget(sec_lbl)

            # Button row (2 columns)
            row_lay = None
            for i, (label, cmd, tooltip) in enumerate(buttons):
                if i % 2 == 0:
                    row_lay = QHBoxLayout()
                    row_lay.setSpacing(4)
                    grid.addLayout(row_lay)

                btn = QPushButton(label)
                btn.setFixedHeight(34)
                btn.setToolTip(tooltip or cmd)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #0b1120;
                        color: #8a9aaf;
                        border: 1px solid #141e30;
                        border-radius: 6px;
                        padding: 4px 8px;
                        font-size: 11px;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background: #101e30;
                        color: {section_color};
                        border-color: {section_color}60;
                    }}
                    QPushButton:pressed {{
                        background: {section_color}30;
                    }}
                """)
                btn.clicked.connect(lambda _, c=cmd: self._palette_send(c))
                row_lay.addWidget(btn)

            # If odd number of buttons, pad the last row
            if len(buttons) % 2 == 1 and row_lay:
                row_lay.addStretch()

        grid.addStretch()
        scroll.setWidget(btn_container)
        p_lay.addWidget(scroll)
        lay.addWidget(palette_panel)

        # ── RIGHT: System Status + Terminal ──
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(8)

        # System status (compact)
        status_group = QGroupBox("System Status")
        self.status_grid = QGridLayout(status_group)
        self.tool_labels: dict[str, QLabel] = {}
        right_lay.addWidget(status_group)

        # Terminal output
        term_group = QGroupBox("Terminal Output")
        term_lay = QVBoxLayout(term_group)

        # Terminal toolbar
        term_toolbar = QHBoxLayout()
        self._term_auto_scroll = True
        auto_scroll_btn = QPushButton("📌 Auto-scroll: ON")
        auto_scroll_btn.setFixedWidth(150)
        auto_scroll_btn.setCheckable(True)
        auto_scroll_btn.setChecked(True)
        def _toggle_scroll(checked):
            self._term_auto_scroll = checked
            auto_scroll_btn.setText(f"📌 Auto-scroll: {'ON' if checked else 'OFF'}")
        auto_scroll_btn.toggled.connect(_toggle_scroll)
        term_toolbar.addWidget(auto_scroll_btn)

        copy_term_btn = QPushButton("📋 Copy All")
        copy_term_btn.setFixedWidth(90)
        copy_term_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.terminal.toPlainText())
        )
        term_toolbar.addWidget(copy_term_btn)

        term_line_count = QLabel("0 lines")
        term_line_count.setStyleSheet("color: #3a5a7a; font-size: 10px;")
        self._term_line_label = term_line_count
        term_toolbar.addWidget(term_line_count)

        term_toolbar.addStretch()
        term_lay.addLayout(term_toolbar)

        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(5000)
        self.terminal.setFont(QFont("JetBrains Mono", 11))
        term_lay.addWidget(self.terminal)

        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Shell command (optional — use buttons instead!)")
        self.cmd_input.returnPressed.connect(self._run_manual_cmd)
        cmd_row.addWidget(self.cmd_input)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self._run_manual_cmd)
        cmd_row.addWidget(run_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.terminal.clear)
        clear_btn.setFixedWidth(60)
        cmd_row.addWidget(clear_btn)
        term_lay.addLayout(cmd_row)

        right_lay.addWidget(term_group, 1)  # terminal stretches
        lay.addWidget(right, 1)
        return w

    def _palette_send(self, cmd: str):
        """Execute a command palette action, auto-filling target from the palette target box."""
        target = self.palette_target.currentText().strip()

        # Commands that need a target — auto-fill from the palette target combobox
        TARGET_CMDS = {
            "quick scan", "full scan", "os detect", "masscan", "stealth recon",
            "nikto", "gobuster", "sqlmap", "ssl scan", "waf detect", "web pwn",
            "osint", "whois", "dns enum", "brute", "mitm", "network dominate",
        }

        full_cmd = cmd
        for prefix in TARGET_CMDS:
            if cmd == prefix:
                if not target:
                    # Focus the target input so user can type/select
                    self.palette_target.setFocus()
                    show_toast(self, "Enter a target first →", "warning", 2000)
                    return
                full_cmd = f"{cmd} {target}"
                # Save to known targets
                if target not in self.known_targets:
                    self.known_targets.add(target)
                    self._update_all_target_comboboxes()
                break

        # Send through the agent (switch to Agent tab to see response)
        self.tabs.setCurrentIndex(0)
        self.chat_panel.input_field.setText(full_cmd)
        self.chat_panel._on_send()

    # ── One-Click Tests tab — categorised + searchable ──────────

    def _make_oneclick_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Search bar
        search_bar = QWidget()
        search_bar.setFixedHeight(48)
        search_bar.setStyleSheet("background: #0a0f1a; border-bottom: 1px solid #141e30;")
        sb_lay = QHBoxLayout(search_bar)
        sb_lay.setContentsMargins(16, 8, 16, 8)
        sb_lay.addWidget(QLabel("🔎"))
        self.skill_search = QLineEdit()
        self.skill_search.setPlaceholderText("Search skills…")
        self.skill_search.textChanged.connect(self._filter_skills)
        sb_lay.addWidget(self.skill_search)
        outer.addWidget(search_bar)

        # Scrollable skill cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._skill_container = QWidget()
        self._skill_layout = QVBoxLayout(self._skill_container)
        self._skill_layout.setContentsMargins(12, 12, 12, 12)
        self._skill_layout.setSpacing(12)

        self._skill_groups: list[tuple[QGroupBox, list[QWidget], list[str]]] = []
        self._build_skill_cards()

        self._skill_layout.addStretch()
        scroll.setWidget(self._skill_container)
        outer.addWidget(scroll)
        return w

    def _build_skill_cards(self):
        all_skills = {s: self.orch.load_skill(s) for s in self.orch.list_skills()}

        for cat_name, skill_names in SKILL_CATEGORIES.items():
            cat_group = QGroupBox(cat_name)
            cat_group.setStyleSheet(
                "QGroupBox { border-color: #1a2e48; } "
                "QGroupBox::title { color: #7ab0d0; }"
            )
            cat_lay = QVBoxLayout(cat_group)
            cat_lay.setSpacing(8)
            card_widgets: list[QWidget] = []
            card_keywords: list[str] = []

            for sname in skill_names:
                skill_data = all_skills.get(sname)
                if not skill_data or "error" in skill_data:
                    # Try loading it directly
                    skill_data = self.orch.load_skill(sname)
                    if "error" in skill_data:
                        continue

                card, keywords = self._make_skill_card(sname, skill_data)
                cat_lay.addWidget(card)
                card_widgets.append(card)
                card_keywords.append(keywords)

            # Also show uncategorised skills under an "Other" bucket
            if cat_name == list(SKILL_CATEGORIES.keys())[-1]:
                categorised = {s for names in SKILL_CATEGORIES.values() for s in names}
                for sname, skill_data in all_skills.items():
                    if sname not in categorised and "error" not in skill_data:
                        card, keywords = self._make_skill_card(sname, skill_data)
                        cat_lay.addWidget(card)
                        card_widgets.append(card)
                        card_keywords.append(keywords)

            if card_widgets:
                self._skill_layout.addWidget(cat_group)
                self._skill_groups.append((cat_group, card_widgets, card_keywords))

    def _make_skill_card(self, skill_name: str, skill_data: dict) -> tuple:
        """Build a single skill card widget. Returns (widget, keyword_string)."""
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #0a0f1a; border: 1px solid #141e30; "
            "border-radius: 8px; padding: 2px; }"
        )
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        display_name = skill_data.get("name", skill_name).replace("_", " ").title()
        title_lbl = QLabel(display_name)
        title_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        c_lay.addLayout(title_row)

        # Description
        desc = skill_data.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #6a8aaa; font-size: 11px; font-style: italic;")
            c_lay.addWidget(desc_lbl)

        # Extract variables (both standalone {{var}} and inline e.g. "http://{{target}}:{{port}}")
        import re
        vars_needed = set()
        for step in skill_data.get("steps", []):
            for _, v in step.get("params", {}).items():
                if isinstance(v, str):
                    for m in re.finditer(r'\{\{(\w+)\}\}', v):
                        vars_needed.add(m.group(1))

        input_fields = {}
        if vars_needed:
            form = QGridLayout()
            form.setSpacing(4)
            for idx, var in enumerate(sorted(vars_needed)):
                lbl = QLabel(f"{var.replace('_', ' ').title()}:")
                lbl.setStyleSheet("color: #4a6a8a; font-size: 11px;")
                form.addWidget(lbl, idx, 0)
                inp = QComboBox()
                inp.setEditable(True)
                inp.lineEdit().setPlaceholderText(f"e.g. {var}")
                inp.setFixedHeight(28)
                self.target_comboboxes.append(inp)
                if self.known_targets:
                    inp.addItems(sorted(list(self.known_targets)))
                form.addWidget(inp, idx, 1)
                input_fields[var] = inp
            c_lay.addLayout(form)

        # Run button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        run_btn = QPushButton("▶  Run")
        run_btn.setFixedHeight(30)
        run_btn.setFixedWidth(90)
        run_btn.setStyleSheet(
            "background: #0d2e1a; color: #00ff88; border: 1px solid #00ff8840; "
            "border-radius: 6px; font-weight: bold; font-size: 12px;"
        )
        run_btn.clicked.connect(
            lambda _, s=skill_data, f=input_fields: self._run_oneclick_test(s, f)
        )
        btn_row.addWidget(run_btn)
        c_lay.addLayout(btn_row)

        keywords = f"{skill_name} {display_name} {desc}".lower()
        return card, keywords

    def _filter_skills(self, query: str):
        """Show/hide skill cards based on search query."""
        q = query.strip().lower()
        for cat_group, cards, keywords_list in self._skill_groups:
            any_visible = False
            for card, kw in zip(cards, keywords_list):
                visible = not q or q in kw
                card.setVisible(visible)
                if visible:
                    any_visible = True
            cat_group.setVisible(any_visible)

    def _run_oneclick_test(self, skill_data, fields):
        context = {}
        for var_name, combo_box in fields.items():
            val = combo_box.currentText().strip()
            if not val:
                QMessageBox.warning(self, "Missing Input", f"Please provide a value for '{var_name}'.")
                return
            context[var_name] = val
            
        self._term_print(f"[TEST] Starting 1-click test: {skill_data.get('name')} ...")
        w = WorkerThread(self.orch.execute_skill_steps, skill_data, context)
        w.finished.connect(lambda _: self._term_print(f"[TEST] Finished 1-click test: {skill_data.get('name')}"))
        w.error.connect(lambda e: self._term_print(f"[ERROR] Test failed: {e}"))
        self._start_worker(w)

    # ── Recon tab ───────────────────────────────────────────────

    def _make_recon_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        # target input
        row = QHBoxLayout()
        row.addWidget(QLabel("Target:"))
        self.recon_target = QComboBox()
        self.recon_target.setEditable(True)
        self.recon_target.lineEdit().setPlaceholderText("e.g. 192.168.1.0/24 or scanme.nmap.org")
        self.target_comboboxes.append(self.recon_target)
        if self.known_targets:
            self.recon_target.addItems(sorted(list(self.known_targets)))
        row.addWidget(self.recon_target)
        lay.addLayout(row)

        # Scan action buttons (2 rows — no typing needed)
        btn_row1 = QHBoxLayout()
        scan_actions_1 = [
            ("🔍 Quick Scan",   self._do_quick_scan,   "Fast nmap scan (top 1000 ports)"),
            ("📋 Full Scan",    self._do_full_scan,    "Deep scan with service detection + scripts"),
            ("🖥️ OS Detect",    lambda: self._do_recon_cmd("os detect"), "OS fingerprinting via nmap"),
            ("⚡ Masscan",      lambda: self._do_recon_cmd("masscan"),   "All 65535 ports at max speed"),
        ]
        for label, callback, tooltip in scan_actions_1:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(34)
            btn.clicked.connect(callback)
            btn_row1.addWidget(btn)
        lay.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        scan_actions_2 = [
            ("👁️ Stealth",      lambda: self._do_recon_cmd("stealth recon"), "Passive OSINT chain"),
            ("🌐 OSINT",        lambda: self._do_recon_cmd("osint"),         "Email + subdomain harvest"),
            ("📡 DNS Enum",     lambda: self._do_recon_cmd("dns enum"),      "DNS records + zone transfer"),
            ("🔓 Vuln Scan",    lambda: self._do_recon_cmd("run skill vuln_scan"), "Vulnerability assessment"),
        ]
        for label, callback, tooltip in scan_actions_2:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(34)
            btn.clicked.connect(callback)
            btn_row2.addWidget(btn)
        lay.addLayout(btn_row2)

        # results table
        self.recon_table = QTableWidget(0, 5)
        self.recon_table.setHorizontalHeaderLabels(["Host", "Port", "State", "Service", "Version"])
        self.recon_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recon_table.setAlternatingRowColors(True)
        self.recon_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recon_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recon_table.customContextMenuRequested.connect(self._recon_context_menu)
        lay.addWidget(self.recon_table)

        return w

    def _recon_context_menu(self, pos):
        """Right-click context menu for recon results table."""
        from PyQt5.QtWidgets import QMenu
        item = self.recon_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        host = self.recon_table.item(row, 0)
        host_text = host.text() if host else ""
        port_item = self.recon_table.item(row, 1)
        port_text = port_item.text() if port_item else ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0d1528; color: #c8d6e5; border: 1px solid #1a2e48; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #00f0ff20; color: #00f0ff; }
        """)

        if host_text:
            copy_ip = menu.addAction(f"📋 Copy: {host_text}")
            copy_ip.triggered.connect(lambda: QApplication.clipboard().setText(host_text))

            menu.addSeparator()

            full_scan = menu.addAction(f"📋 Full Scan → {host_text}")
            full_scan.triggered.connect(lambda: self._run_agent_cmd(f"full scan {host_text}"))

            web_pwn = menu.addAction(f"🌐 Web Pwn → {host_text}")
            web_pwn.triggered.connect(lambda: self._run_agent_cmd(f"web pwn http://{host_text}"))

            brute = menu.addAction(f"🔓 Brute → {host_text}")
            brute.triggered.connect(lambda: self._run_agent_cmd(f"brute {host_text}"))

            menu.addSeparator()

            set_target = menu.addAction(f"🎯 Set as Target")
            set_target.triggered.connect(lambda: self._set_target_from_menu(host_text))

        if port_text:
            copy_port = menu.addAction(f"📋 Copy: {host_text}:{port_text}")
            copy_port.triggered.connect(lambda: QApplication.clipboard().setText(f"{host_text}:{port_text}"))

        menu.exec_(self.recon_table.mapToGlobal(pos))

    def _do_recon_cmd(self, cmd: str):
        """Run a recon command from the Recon tab buttons."""
        target = self.recon_target.currentText().strip()
        if not target:
            QMessageBox.warning(self, "No Target", "Enter a target IP/domain first.")
            return
        if target not in self.known_targets:
            self.known_targets.add(target)
            self._update_all_target_comboboxes()
        full_cmd = f"{cmd} {target}"
        self.tabs.setCurrentIndex(0)
        self.chat_panel.input_field.setText(full_cmd)
        self.chat_panel._on_send()

    # ── Wi-Fi tab ───────────────────────────────────────────────

    def _make_wifi_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        # interface controls
        iface_row = QHBoxLayout()
        iface_row.addWidget(QLabel("Interface:"))
        self.wifi_iface = QComboBox()
        self.wifi_iface.setMinimumWidth(180)
        iface_row.addWidget(self.wifi_iface)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_interfaces)
        iface_row.addWidget(refresh_btn)

        self.mon_btn = QPushButton("Enable Monitor")
        self.mon_btn.clicked.connect(self._toggle_monitor)
        iface_row.addWidget(self.mon_btn)

        self.autopwn_btn = QPushButton("🔥 AutoPwn (End-to-End)")
        self.autopwn_btn.setStyleSheet("background-color: #5a1a1a; color: #ff5555; font-weight: bold;")
        self.autopwn_btn.clicked.connect(self._do_autopwn)
        iface_row.addWidget(self.autopwn_btn)

        # NetworkGuard status indicator
        self.net_guard_label = QLabel("🛡️")
        self.net_guard_label.setToolTip("Network self-protection active")
        self.net_guard_label.setStyleSheet(
            "color: #00ff88; font-size: 14px; background: transparent; padding: 0 4px;"
        )
        iface_row.addWidget(self.net_guard_label)

        iface_row.addStretch()
        lay.addLayout(iface_row)

        # Wi-Fi wordlist selector row
        wl_row = QHBoxLayout()
        wl_row.addWidget(QLabel("Wordlist:"))
        self.wifi_wl_combo = QComboBox()
        self.wifi_wl_combo.setEditable(True)
        self.wifi_wl_combo.setMinimumWidth(350)
        self._populate_wordlist_combo(self.wifi_wl_combo, "wifi")
        wl_row.addWidget(self.wifi_wl_combo)
        wifi_wl_browse = QPushButton("Browse")
        wifi_wl_browse.clicked.connect(lambda: self._browse_combo(self.wifi_wl_combo, "*"))
        wl_row.addWidget(wifi_wl_browse)
        wl_row.addStretch()
        lay.addLayout(wl_row)

        # ── One-Click Hack buttons ──────────────────────────────
        hack_group = QGroupBox("⚡ One-Click Hacks")
        hack_group.setStyleSheet(
            "QGroupBox { border: 2px solid #ff440040; border-radius: 8px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { color: #ff6b35; font-weight: bold; }"
        )
        hack_lay = QHBoxLayout(hack_group)
        hack_lay.setSpacing(8)

        hack_buttons = [
            ("🔥 Wi-Fi Blitz", "PMKID + Handshake + WPS (all vectors)", self._do_wifi_blitz,
             "background:#1a0d00; color:#ff6b35; border:1px solid #ff6b3540;"),
            ("💀 Network Dominate", "Scan + Fingerprint + Brute-force", self._do_network_dominate,
             "background:#1a000d; color:#ff3565; border:1px solid #ff356540;"),
            ("🌐 Web Pwn", "WAF + DirBust + SQLi + SSL + Nikto", self._do_web_pwn,
             "background:#001a0d; color:#35ff65; border:1px solid #35ff6540;"),
            ("👁️ Stealth Recon", "Passive: OSINT + DNS + WHOIS", self._do_stealth_recon,
             "background:#0d001a; color:#9b59b6; border:1px solid #9b59b640;"),
        ]

        for label, tooltip, handler, style in hack_buttons:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{ {style} border-radius:8px; font-weight:bold; font-size:12px; padding:4px 12px; }}"
                f"QPushButton:hover {{ border-width:2px; }}"
            )
            btn.clicked.connect(handler)
            hack_lay.addWidget(btn)

        lay.addWidget(hack_group)

        # ── Live AP Scanner ────────────────────────────────────
        ap_group = QGroupBox("📡 Nearby Access Points")
        ap_group.setStyleSheet(
            "QGroupBox { border: 2px solid #00f0ff20; border-radius: 8px; margin-top: 8px; padding-top: 12px; }"
            "QGroupBox::title { color: #00f0ff; font-weight: bold; }"
        )
        ap_lay = QVBoxLayout(ap_group)

        ap_btn_row = QHBoxLayout()
        scan_ap_btn = QPushButton("🔍 Scan Nearby APs (10s)")
        scan_ap_btn.setStyleSheet(
            "QPushButton { background:#0a1a2d; color:#00f0ff; border:1px solid #00f0ff40; "
            "border-radius:6px; padding:6px 16px; font-weight:bold; }"
            "QPushButton:hover { border-color:#00f0ff; }"
        )
        scan_ap_btn.clicked.connect(self._do_ap_scan)
        ap_btn_row.addWidget(scan_ap_btn)
        ap_btn_row.addStretch()
        ap_lay.addLayout(ap_btn_row)

        self.ap_table = QTableWidget(0, 5)
        self.ap_table.setHorizontalHeaderLabels(["BSSID", "ESSID", "Channel", "Encryption", "Signal"])
        self.ap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ap_table.setMaximumHeight(180)
        self.ap_table.setAlternatingRowColors(True)
        self.ap_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ap_table.itemDoubleClicked.connect(self._ap_table_select)
        self.ap_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ap_table.customContextMenuRequested.connect(self._ap_context_menu)
        ap_lay.addWidget(self.ap_table)
        lay.addWidget(ap_group)

        # ── Loot / Cracked Keys ────────────────────────────────
        loot_group = QGroupBox("🔑 Cracked Keys (Persistent)")
        loot_group.setStyleSheet(
            "QGroupBox { border: 2px solid #00ff8820; border-radius: 8px; margin-top: 4px; padding-top: 12px; }"
            "QGroupBox::title { color: #00ff88; font-weight: bold; }"
        )
        loot_lay = QVBoxLayout(loot_group)
        self.loot_label = QLabel("No keys cracked yet.")
        self.loot_label.setWordWrap(True)
        self.loot_label.setStyleSheet("color: #6a8aaa; font-size: 11px;")
        loot_lay.addWidget(self.loot_label)
        refresh_loot_btn = QPushButton("↻ Refresh Loot")
        refresh_loot_btn.setFixedWidth(120)
        refresh_loot_btn.setStyleSheet(
            "QPushButton { background:#0d2e1a; color:#00ff88; border:1px solid #00ff8840; "
            "border-radius:6px; padding:4px 10px; font-size:11px; }"
        )
        refresh_loot_btn.clicked.connect(self._refresh_loot)
        loot_lay.addWidget(refresh_loot_btn)
        lay.addWidget(loot_group)

        # deauth controls
        deauth_group = QGroupBox("Deauthentication")
        dlay = QHBoxLayout(deauth_group)
        dlay.addWidget(QLabel("BSSID:"))
        self.deauth_bssid = QComboBox()
        self.deauth_bssid.setEditable(True)
        self.deauth_bssid.lineEdit().setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.target_comboboxes.append(self.deauth_bssid)
        if self.known_targets:
            self.deauth_bssid.addItems(sorted(list(self.known_targets)))
        dlay.addWidget(self.deauth_bssid)
        dlay.addWidget(QLabel("Count:"))
        self.deauth_count = QLineEdit("10")
        self.deauth_count.setFixedWidth(60)
        dlay.addWidget(self.deauth_count)
        deauth_btn = QPushButton("Send Deauth")
        deauth_btn.setObjectName("dangerBtn")
        deauth_btn.clicked.connect(self._do_deauth)
        dlay.addWidget(deauth_btn)
        lay.addWidget(deauth_group)

        # output
        self.wifi_output = QPlainTextEdit()
        self.wifi_output.setReadOnly(True)
        self.wifi_output.setMaximumBlockCount(3000)
        lay.addWidget(self.wifi_output)

        return w

    # ── Cracking tab ────────────────────────────────────────────

    def _make_cracking_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        # WPA cracking
        wpa_group = QGroupBox("🔓 WPA Handshake Crack (aircrack-ng)")
        glay = QGridLayout(wpa_group)

        glay.addWidget(QLabel("Capture:"), 0, 0)
        self.cap_path = QComboBox()
        self.cap_path.setEditable(True)
        self.cap_path.setMinimumWidth(300)
        self.cap_path.lineEdit().setPlaceholderText("Select or browse for .cap file")
        self._populate_captures()
        glay.addWidget(self.cap_path, 0, 1)

        cap_btn_row = QHBoxLayout()
        cap_browse = QPushButton("Browse")
        cap_browse.clicked.connect(lambda: self._browse_combo(self.cap_path, "*.cap *.hccapx *.pcap"))
        cap_btn_row.addWidget(cap_browse)
        cap_refresh = QPushButton("↻ Detect")
        cap_refresh.setToolTip("Scan ~/.james/captures/ for new capture files")
        cap_refresh.clicked.connect(self._populate_captures)
        cap_btn_row.addWidget(cap_refresh)
        glay.addLayout(cap_btn_row, 0, 2)

        glay.addWidget(QLabel("Wordlist:"), 1, 0)
        self.wl_path = QComboBox()
        self.wl_path.setEditable(True)
        self.wl_path.setMinimumWidth(300)
        self._populate_wordlist_combo(self.wl_path, "wifi")
        glay.addWidget(self.wl_path, 1, 1)
        wl_browse = QPushButton("Browse")
        wl_browse.clicked.connect(lambda: self._browse_combo(self.wl_path, "*"))
        glay.addWidget(wl_browse, 1, 2)

        crack_btn = QPushButton("⚡ Crack WPA")
        crack_btn.setStyleSheet("""
            QPushButton { background: #1a1a00; color: #ffcc00; border: 1px solid #ffcc0040;
                border-radius: 6px; font-weight: bold; font-size: 12px; padding: 8px 16px; }
            QPushButton:hover { background: #2a2a00; border-color: #ffcc00; }
        """)
        crack_btn.clicked.connect(self._do_crack_wpa)
        glay.addWidget(crack_btn, 2, 1)
        lay.addWidget(wpa_group)

        # Hash cracking
        hash_group = QGroupBox("🔐 Hash Crack (hashcat)")
        hlay = QGridLayout(hash_group)
        hlay.addWidget(QLabel("Hash File:"), 0, 0)
        self.hash_path = QLineEdit()
        self.hash_path.setPlaceholderText("Path to hash file or paste hash directly")
        hlay.addWidget(self.hash_path, 0, 1)
        h_browse = QPushButton("Browse")
        h_browse.clicked.connect(lambda: self._browse(self.hash_path, "*"))
        hlay.addWidget(h_browse, 0, 2)

        hlay.addWidget(QLabel("Mode:"), 1, 0)
        self.hash_mode = QComboBox()
        self.hash_mode.addItems([
            "0 - MD5",
            "100 - SHA1",
            "500 - md5crypt",
            "900 - MD4",
            "1000 - NTLM",
            "1400 - SHA256",
            "1700 - SHA512",
            "1800 - sha512crypt",
            "2500 - WPA/WPA2",
            "2501 - WPA-EAPOL-PMK",
            "3000 - LM",
            "3200 - bcrypt",
            "5500 - NetNTLMv1",
            "5600 - NetNTLMv2",
            "7500 - Kerberos 5 AS-REQ",
            "13100 - Kerberos 5 TGS-REP",
            "16800 - WPA-PMKID-PBKDF2",
            "22000 - WPA-PBKDF2-PMKID+EAPOL",
        ])
        hlay.addWidget(self.hash_mode, 1, 1)

        hlay.addWidget(QLabel("Wordlist:"), 2, 0)
        self.hash_wl_path = QComboBox()
        self.hash_wl_path.setEditable(True)
        self.hash_wl_path.setMinimumWidth(300)
        self._populate_wordlist_combo(self.hash_wl_path, "password")
        hlay.addWidget(self.hash_wl_path, 2, 1)
        hwl_browse = QPushButton("Browse")
        hwl_browse.clicked.connect(lambda: self._browse_combo(self.hash_wl_path, "*"))
        hlay.addWidget(hwl_browse, 2, 2)

        hcrack_btn = QPushButton("⚡ Crack Hash")
        hcrack_btn.setStyleSheet("""
            QPushButton { background: #1a0018; color: #a855f7; border: 1px solid #a855f740;
                border-radius: 6px; font-weight: bold; font-size: 12px; padding: 8px 16px; }
            QPushButton:hover { background: #2a0028; border-color: #a855f7; }
        """)
        hcrack_btn.clicked.connect(self._do_crack_hash)
        hlay.addWidget(hcrack_btn, 3, 1)
        lay.addWidget(hash_group)

        # result output
        out_header = QHBoxLayout()
        out_label = QLabel("📋 Output")
        out_label.setStyleSheet("color: #5a8aaa; font-weight: bold; font-size: 12px;")
        out_header.addWidget(out_label)
        out_header.addStretch()
        clear_out_btn = QPushButton("Clear")
        clear_out_btn.setFixedWidth(60)
        clear_out_btn.clicked.connect(lambda: self.crack_output.clear())
        out_header.addWidget(clear_out_btn)
        lay.addLayout(out_header)

        self.crack_output = QPlainTextEdit()
        self.crack_output.setReadOnly(True)
        lay.addWidget(self.crack_output)

        return w

    def _populate_captures(self):
        """Auto-detect .cap/.hccapx/.pcap/.pmkid files from captures directory."""
        captures_dir = Path.home() / ".james" / "captures"
        self.cap_path.clear()
        if captures_dir.exists():
            caps = sorted(captures_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            for cap in caps:
                if cap.suffix.lower() in (".cap", ".hccapx", ".pcap", ".pmkid", ".22000"):
                    # Show filename but store full path
                    self.cap_path.addItem(f"{cap.name}  ({cap.stat().st_size // 1024}KB)", str(cap))
        if self.cap_path.count() == 0:
            self.cap_path.lineEdit().setPlaceholderText("No captures found — use Browse or run AutoPwn first")

    def _populate_wordlist_combo(self, combo: QComboBox, category: str = "password"):
        """Fill a combo box with available wordlists, preferring the given category."""
        try:
            inventory = self.orch.list_wordlists()
            # Put matching category first, then the rest
            matched = [wl for wl in inventory if wl["category"] == category]
            others = [wl for wl in inventory if wl["category"] != category]
            for wl in matched + others:
                label = f"{wl['name']}  ({wl['lines']:,} entries)"
                combo.addItem(label, wl["path"])
            # Select the first item (best match)
            if combo.count() > 0:
                combo.setCurrentIndex(0)
        except Exception:
            combo.addItem("/usr/share/wordlists/rockyou.txt")

    def _browse_combo(self, combo: QComboBox, filt: str):
        """Open a file browser and set the result as the combo's current text."""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", f"Files ({filt})")
        if path:
            combo.setCurrentText(path)

    def _get_wordlist_path(self, combo: QComboBox) -> str:
        """Extract the actual file path from a wordlist combo box."""
        # If user data is set (picked from dropdown), use that
        data = combo.currentData()
        if data:
            return data
        # Otherwise use the raw text (user typed/browsed a custom path)
        return combo.currentText().strip()

    # ── Log tab ─────────────────────────────────────────────────

    def _make_log_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        # Header row
        header_row = QHBoxLayout()
        self.log_count_label = QLabel("📋 0 tasks logged")
        self.log_count_label.setStyleSheet("color: #5a8aaa; font-weight: bold; font-size: 12px;")
        header_row.addWidget(self.log_count_label)
        header_row.addStretch()

        refresh_log_btn = QPushButton("↻ Refresh")
        refresh_log_btn.clicked.connect(self._refresh_log_table)
        header_row.addWidget(refresh_log_btn)
        lay.addLayout(header_row)

        self.log_table = QTableWidget(0, 5)
        self.log_table.setHorizontalHeaderLabels(["Time", "Action", "Tool", "Status", "Details"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.log_table)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("📤 Export Log (JSON)")
        export_btn.clicked.connect(self._export_log)
        btn_row.addWidget(export_btn)

        report_btn = QPushButton("📋 Generate HTML Report")
        report_btn.setStyleSheet("""
            QPushButton {
                background: #0a1a30; color: #00f0ff;
                border: 1px solid #00f0ff40; border-radius: 6px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover {
                background: #102040; border-color: #00f0ff;
            }
        """)
        report_btn.clicked.connect(self._generate_gui_report)
        btn_row.addWidget(report_btn)

        clear_log_btn = QPushButton("🗑️ Clear Log")
        clear_log_btn.clicked.connect(lambda: self.log_table.setRowCount(0))
        btn_row.addWidget(clear_log_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)
        return w

    # ── context menu helpers ─────────────────────────────────────

    def _run_agent_cmd(self, cmd: str):
        """Send a command through the agent chat — universal entry point for all buttons/menus."""
        self.tabs.setCurrentIndex(0)
        self.chat_panel.input_field.setText(cmd)
        self.chat_panel._on_send()

    def _set_target_from_menu(self, target: str):
        """Set a target from a right-click menu."""
        self.chat_panel.agent.context["target"] = target
        if target not in self.known_targets:
            self.known_targets.add(target)
            self._update_all_target_comboboxes()
        self._refresh_context_strip()
        show_toast(self, f"Target set: {target}", "info", 2000)

    def _ap_context_menu(self, pos):
        """Right-click context menu for the AP table."""
        from PyQt5.QtWidgets import QMenu
        item = self.ap_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        bssid = self.ap_table.item(row, 0).text() if self.ap_table.item(row, 0) else ""
        essid = self.ap_table.item(row, 1).text() if self.ap_table.item(row, 1) else ""
        channel = self.ap_table.item(row, 2).text() if self.ap_table.item(row, 2) else ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0d1528; color: #c8d6e5; border: 1px solid #1a2e48; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #ff6b3520; color: #ff6b35; }
        """)

        if bssid:
            copy_bssid = menu.addAction(f"📋 Copy BSSID: {bssid}")
            copy_bssid.triggered.connect(lambda: QApplication.clipboard().setText(bssid))
        if essid:
            copy_essid = menu.addAction(f"📋 Copy ESSID: {essid}")
            copy_essid.triggered.connect(lambda: QApplication.clipboard().setText(essid))

        menu.addSeparator()

        if bssid:
            deauth_act = menu.addAction(f"💀 Deauth → {essid or bssid}")
            deauth_act.triggered.connect(lambda: (
                self.deauth_bssid.setCurrentText(bssid),
                self._do_deauth(),
            ))

            blitz_act = menu.addAction(f"🔥 Wi-Fi Blitz → {essid or bssid}")
            blitz_act.triggered.connect(self._do_wifi_blitz)

            menu.addSeparator()

            set_target = menu.addAction(f"🎯 Set as Target")
            set_target.triggered.connect(lambda: self._set_target_from_menu(bssid))

        menu.exec_(self.ap_table.mapToGlobal(pos))

    # ── actions ─────────────────────────────────────────────────

    def _run_system_check(self):
        def _check():
            return self.orch.system_check()
        w = WorkerThread(_check)
        w.finished.connect(self._show_system_status)
        w.error.connect(lambda e: self._term_print(f"[ERROR] {e}"))
        self._start_worker(w)

    def _show_system_status(self, status: dict):
        # clear grid
        for i in reversed(range(self.status_grid.count())):
            self.status_grid.itemAt(i).widget().deleteLater()

        installed = sum(1 for v in status.values() if v)
        total = len(status)

        # Summary header
        summary = QLabel(f"  {installed}/{total} tools installed")
        if installed == total:
            summary.setStyleSheet("color: #00ff88; font-size: 12px; font-weight: bold;")
        elif installed > total // 2:
            summary.setStyleSheet("color: #ffcc00; font-size: 12px; font-weight: bold;")
        else:
            summary.setStyleSheet("color: #ff4757; font-size: 12px; font-weight: bold;")
        self.status_grid.addWidget(summary, 0, 0, 1, 4)

        row = 1
        col = 0
        for tool, available in status.items():
            dot = "●" if available else "✕"
            color = "#00ff88" if available else "#ff4757"
            lbl = QLabel(f'<span style="color:{color}; font-size:13px;">{dot}</span>  {tool}')
            lbl.setStyleSheet("font-size: 11px; padding: 2px 4px;")
            self.status_grid.addWidget(lbl, row, col * 2, 1, 2)
            self.tool_labels[tool] = lbl
            col += 1
            if col >= 2:
                col = 0
                row += 1
        if col != 0:
            row += 1

        # Refresh button
        refresh_btn = QPushButton("↻ Re-check Tools")
        refresh_btn.setFixedWidth(140)
        refresh_btn.clicked.connect(self._run_system_check)
        self.status_grid.addWidget(refresh_btn, row, 0, 1, 4)

        self.status_grid.setRowStretch(row, 1)
        self._term_print("[SYS] System check complete.")

    def _run_manual_cmd(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        self._term_print(f"$ {cmd}")

        def _exec():
            return self.orch.layer.run(cmd, timeout=60)
        w = WorkerThread(_exec)
        w.finished.connect(lambda r: self._term_print(r.stdout + r.stderr if r else ""))
        w.error.connect(lambda e: self._term_print(f"[ERROR] {e}"))
        self._start_worker(w)

    def _do_quick_scan(self):
        target = self.recon_target.currentText().strip()
        if not target:
            return
        self._term_print(f"[RECON] Quick scan → {target}")
        self.recon_quick_btn.setEnabled(False)
        w = WorkerThread(self.orch.quick_recon, target)
        w.finished.connect(self._populate_recon)
        w.finished.connect(lambda _: self.recon_quick_btn.setEnabled(True))
        w.error.connect(lambda e: (self._term_print(f"[ERROR] {e}"),
                                    self.recon_quick_btn.setEnabled(True)))
        self._start_worker(w)

    def _do_full_scan(self):
        target = self.recon_target.currentText().strip()
        if not target:
            return
        self._term_print(f"[RECON] Full scan → {target}")
        self.recon_full_btn.setEnabled(False)
        w = WorkerThread(self.orch.full_scan, target)
        w.finished.connect(self._populate_recon)
        w.finished.connect(lambda _: self.recon_full_btn.setEnabled(True))
        w.error.connect(lambda e: (self._term_print(f"[ERROR] {e}"),
                                    self.recon_full_btn.setEnabled(True)))
        self._start_worker(w)

    def _populate_recon(self, result: dict):
        self.recon_table.setRowCount(0)
        if "error" in result:
            self._term_print(f"[ERROR] {result['error']}")
            return
        new_targets = False
        for host in result.get("hosts", []):
            addr = host["address"]
            if addr and addr not in self.known_targets:
                self.known_targets.add(addr)
                new_targets = True
            for port in host.get("ports", []):
                row = self.recon_table.rowCount()
                self.recon_table.insertRow(row)
                self.recon_table.setItem(row, 0, QTableWidgetItem(addr))
                self.recon_table.setItem(row, 1, QTableWidgetItem(str(port["port"])))
                self.recon_table.setItem(row, 2, QTableWidgetItem(port["state"]))
                self.recon_table.setItem(row, 3, QTableWidgetItem(port["service"]))
                self.recon_table.setItem(row, 4, QTableWidgetItem(port["version"]))
        self._term_print(f"[RECON] Found {self.recon_table.rowCount()} open ports.")
        if new_targets:
            self._update_all_target_comboboxes()

    def _refresh_interfaces(self):
        w = WorkerThread(self.orch.wifi_interfaces)
        w.finished.connect(self._update_iface_combo)
        self._start_worker(w)

    def _update_iface_combo(self, ifaces: list):
        self.wifi_iface.clear()
        for iface in ifaces:
            self.wifi_iface.addItem(f"{iface['interface']} ({iface['mode']})")

    def _toggle_monitor(self):
        iface_text = self.wifi_iface.currentText()
        if not iface_text:
            return
        iface = iface_text.split()[0]
        if "Monitor" in iface_text:
            w = WorkerThread(self.orch.stop_monitor, iface)
            w.finished.connect(lambda r: self._wifi_print(
                f"[MONITOR] Stopped: {r.get('stdout', '')}"))
        else:
            w = WorkerThread(self.orch.start_monitor, iface)
            w.finished.connect(lambda r: self._wifi_print(
                f"[MONITOR] Started: {r.get('stdout', '')}"))
        w.finished.connect(lambda _: self._refresh_interfaces())
        self._start_worker(w)

    def _do_deauth(self):
        iface_text = self.wifi_iface.currentText()
        bssid = self.deauth_bssid.currentText().strip()
        if not iface_text or not bssid:
            return
        iface = iface_text.split()[0]
        count = int(self.deauth_count.text() or "10")

        # Network self-protection check
        safe, reason = self.orch.net_guard.check_deauth_safe(bssid)
        if not safe:
            self._wifi_print(reason)
            QMessageBox.warning(self, "Self-Protection", reason)
            return

        self._wifi_print(f"[DEAUTH] → {bssid} x{count}")
        w = WorkerThread(self.orch.aircrack.deauth, iface, bssid, count=count)
        w.finished.connect(lambda r: self._wifi_print(r.stdout if r else "done"))
        self._start_worker(w)

    def _do_crack_wpa(self):
        cap = self._get_wordlist_path(self.cap_path)  # works for any QComboBox with data
        wl = self._get_wordlist_path(self.wl_path)
        if not cap:
            QMessageBox.warning(self, "No Capture", "Select a .cap file first.\nUse 'Detect' to find captures from AutoPwn runs.")
            return
        if not wl:
            QMessageBox.warning(self, "No Wordlist", "Select a wordlist first.")
            return
        self.crack_output.setPlainText(f"Cracking {cap.split('/')[-1]} with {wl.split('/')[-1]}…\n")
        w = WorkerThread(self.orch.crack_handshake, cap, wl)
        w.finished.connect(self._show_crack_result)
        self._start_worker(w)

    def _do_autopwn(self):
        iface_text = self.wifi_iface.currentText()
        if not iface_text:
            QMessageBox.warning(self, "No Interface", "Please select a Wi-Fi interface first.")
            return
        iface = iface_text.split()[0]
        
        # Use the Wi-Fi tab wordlist selector
        wordlist = self._get_wordlist_path(self.wifi_wl_combo)
        if not wordlist:
            # Fallback to orchestrator auto-detection
            wordlist = self.orch.find_wordlist("wifi")
        if not wordlist:
            QMessageBox.warning(self, "No Wordlist", "No wordlist selected and none auto-detected.\nSelect one from the Wordlist dropdown.")
            return
            
        self._term_print(f"[AUTOPWN] Triggered on interface {iface} with {wordlist.split('/')[-1]}")
        self.autopwn_btn.setEnabled(False)
        w = WorkerThread(self.orch.auto_wifi_pwn, iface, wordlist)
        w.finished.connect(lambda r: self._term_print(f"[AUTOPWN] Workflow complete: {json.dumps(r)}"))
        w.finished.connect(lambda _: self.autopwn_btn.setEnabled(True))
        w.error.connect(lambda e: (self._term_print(f"[ERROR] AutoPwn failed: {e}"), self.autopwn_btn.setEnabled(True)))
        self._start_worker(w)

    def _do_crack_hash(self):
        hf = self.hash_path.text().strip()
        wl = self._get_wordlist_path(self.hash_wl_path)
        if not hf or not wl:
            return
        mode = int(self.hash_mode.currentText().split(" - ")[0])
        self.crack_output.setPlainText(f"Cracking hash with {wl.split('/')[-1]}…\n")
        w = WorkerThread(self.orch.crack_hash, hf, wl, mode)
        w.finished.connect(self._show_crack_result)
        self._start_worker(w)

    def _show_crack_result(self, result: dict):
        if result.get("found"):
            self.crack_output.setPlainText(f"🔑 KEY FOUND: {result['key']}\n\n{result.get('output','')}")
        else:
            self.crack_output.setPlainText(f"No key found.\n\n{result.get('output','')}")

    def _browse(self, target_input: QLineEdit, pattern: str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "/home/malcolm", pattern)
        if path:
            target_input.setText(path)

    # ── AP scanner handlers ─────────────────────────────────────

    def _do_ap_scan(self):
        iface_text = self.wifi_iface.currentText()
        if not iface_text:
            QMessageBox.warning(self, "No Interface", "Select a Wi-Fi interface first.\nClick 'Refresh' to detect wireless adapters.")
            return
        iface = iface_text.split()[0]
        self._wifi_print("[AP SCAN] Scanning nearby networks (10s)...")
        self._wifi_print("[AP SCAN] Monitor mode will be auto-enabled if needed.")
        w = WorkerThread(self.orch.scan_nearby_aps, iface)
        w.finished.connect(self._populate_ap_table)
        w.error.connect(lambda e: self._wifi_print(f"[ERROR] AP scan failed: {e}"))
        self._start_worker(w)

    def _populate_ap_table(self, result: dict):
        aps = result.get("aps", [])
        self.ap_table.setRowCount(0)
        new_targets = False
        for ap in aps:
            row = self.ap_table.rowCount()
            bssid = ap.get("bssid", "")
            if bssid and bssid not in self.known_targets:
                self.known_targets.add(bssid)
                new_targets = True
            essid = ap.get("essid", "")
            if essid and essid not in self.known_targets:
                self.known_targets.add(essid)
                new_targets = True
            self.ap_table.insertRow(row)
            self.ap_table.setItem(row, 0, QTableWidgetItem(ap.get("bssid", "")))
            self.ap_table.setItem(row, 1, QTableWidgetItem(ap.get("essid", "")))
            self.ap_table.setItem(row, 2, QTableWidgetItem(str(ap.get("channel", ""))))
            self.ap_table.setItem(row, 3, QTableWidgetItem(ap.get("privacy", "")))
            # Signal strength with visual bar
            pwr = ap.get("power", -100)
            bars = "█" * max(0, min(5, (pwr + 100) // 15)) + "░" * max(0, 5 - max(0, (pwr + 100) // 15))
            pwr_item = QTableWidgetItem(f"{pwr}dBm {bars}")
            if pwr > -50:
                pwr_item.setForeground(QColor("#00ff88"))
            elif pwr > -70:
                pwr_item.setForeground(QColor("#ffcc00"))
            else:
                pwr_item.setForeground(QColor("#ff4757"))
            self.ap_table.setItem(row, 4, pwr_item)
        self._wifi_print(f"[AP SCAN] Found {len(aps)} access points")
        if new_targets:
            self._update_all_target_comboboxes()

    def _ap_table_select(self, item):
        """Double-click an AP row → auto-fill BSSID into deauth field and context."""
        row = item.row()
        bssid = self.ap_table.item(row, 0).text() if self.ap_table.item(row, 0) else ""
        essid = self.ap_table.item(row, 1).text() if self.ap_table.item(row, 1) else ""
        channel = self.ap_table.item(row, 2).text() if self.ap_table.item(row, 2) else ""
        if bssid:
            self.deauth_bssid.setCurrentText(bssid)
            # Also update agent context for evil twin etc.
            try:
                self.chat_panel.agent.context["target_bssid"] = bssid
                self.chat_panel.agent.context["target_ssid"] = essid
                self.chat_panel.agent.context["target_channel"] = channel
            except AttributeError:
                pass
            self._wifi_print(f"[TARGET] Selected: {bssid} ({essid}) ch{channel}")

    def _refresh_loot(self):
        loot = self.orch.get_loot_summary()
        if loot["cracked_count"] == 0:
            self.loot_label.setText("No keys cracked yet.")
            return
        lines = []
        for entry in loot["keys"]:
            lines.append(f"🔑 {entry['essid'] or entry['id']} → {entry['key']}  [{entry['method']}]")
        self.loot_label.setText("\n".join(lines))
        self.loot_label.setStyleSheet("color: #00ff88; font-size: 11px; font-family: 'JetBrains Mono';")

    # ── one-click hack handlers ─────────────────────────────────

    def _do_wifi_blitz(self):
        iface_text = self.wifi_iface.currentText()
        if not iface_text:
            QMessageBox.warning(self, "No Interface", "Select a Wi-Fi interface first.")
            return
        iface = iface_text.split()[0]
        wordlist = self._get_wordlist_path(self.wifi_wl_combo)
        if not wordlist:
            wordlist = self.orch.find_wordlist("wifi")
        if not wordlist:
            QMessageBox.warning(self, "No Wordlist", "Select a wordlist from the dropdown first.")
            return
        self._term_print(f"[ONE-CLICK] 🔥 Wi-Fi Blitz on {iface} with {wordlist.split('/')[-1]}")
        w = WorkerThread(self.orch.oneclick_wifi_blitz, iface, wordlist)
        w.finished.connect(lambda r: self._term_print(f"[ONE-CLICK] Wi-Fi Blitz finished: {len(r.get('cracked', []))} cracked"))
        w.error.connect(lambda e: self._term_print(f"[ERROR] Wi-Fi Blitz failed: {e}"))
        self._start_worker(w)

    def _do_network_dominate(self):
        from PyQt5.QtWidgets import QInputDialog
        targets = [""] + sorted(list(self.known_targets))
        target, ok = QInputDialog.getItem(self, "Network Dominate", "Target range (e.g. 192.168.1.0/24):", targets, 0, True)
        if not ok or not target:
            return
        self._term_print(f"[ONE-CLICK] 💀 Network Dominate → {target}")
        w = WorkerThread(self.orch.oneclick_network_dominate, target)
        w.finished.connect(lambda r: self._term_print(f"[ONE-CLICK] Network Dominate finished: {len(r.get('services',[]))} services found"))
        w.error.connect(lambda e: self._term_print(f"[ERROR] Network Dominate failed: {e}"))
        self._start_worker(w)

    def _do_web_pwn(self):
        from PyQt5.QtWidgets import QInputDialog
        targets = [""] + sorted(list(self.known_targets))
        url, ok = QInputDialog.getItem(self, "Web Pwn", "Target URL (e.g. http://target.com):", targets, 0, True)
        if not ok or not url:
            return
        self._term_print(f"[ONE-CLICK] 🌐 Web Pwn → {url}")
        w = WorkerThread(self.orch.oneclick_web_pwn, url)
        w.finished.connect(lambda r: self._term_print("[ONE-CLICK] Web Pwn finished"))
        w.error.connect(lambda e: self._term_print(f"[ERROR] Web Pwn failed: {e}"))
        self._start_worker(w)

    def _do_stealth_recon(self):
        from PyQt5.QtWidgets import QInputDialog
        targets = [""] + sorted(list(self.known_targets))
        target, ok = QInputDialog.getItem(self, "Stealth Recon", "Target domain/IP:", targets, 0, True)
        if not ok or not target:
            return
        self._term_print(f"[ONE-CLICK] 👁️ Stealth Recon → {target}")
        w = WorkerThread(self.orch.oneclick_stealth_recon, target)
        w.finished.connect(lambda r: self._term_print("[ONE-CLICK] Stealth Recon finished"))
        w.error.connect(lambda e: self._term_print(f"[ERROR] Stealth Recon failed: {e}"))
        self._start_worker(w)

    # ── kill JAMES handler ───────────────────────────────────────

    def _do_kill_james(self):
        """Emergency stop — confirm, then kill everything."""
        reply = QMessageBox.warning(
            self,
            "🛑 Kill JAMES",
            "This will:\n\n"
            "• Kill ALL running pentesting tools\n"
            "• Restore wireless interfaces to managed mode\n"
            "• Flush iptables rules\n"
            "• Restart NetworkManager (reconnect Wi-Fi)\n"
            "• Clean temp files\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.kill_btn.setEnabled(False)
        self.kill_btn.setText("⏳ ...")
        self._term_print("🛑 KILL JAMES — Shutting everything down...")
        self._wifi_print("🛑 KILL JAMES — Shutting everything down...")

        w = WorkerThread(self.orch.kill_james)
        w.finished.connect(self._on_kill_complete)
        w.error.connect(lambda e: (
            self._term_print(f"[ERROR] Kill failed: {e}"),
            self._restore_kill_btn(),
        ))
        self._start_worker(w)

    def _on_kill_complete(self, summary: dict):
        killed = len(summary.get("killed", []))
        restored = len(summary.get("interfaces_restored", []))
        self._term_print(f"🛑 Kill complete — {killed} processes killed, {restored} interfaces restored")
        self._wifi_print(f"🛑 Kill complete — interfaces restored. Wi-Fi should reconnect.")
        self._restore_kill_btn()
        # Refresh the interface list
        QTimer.singleShot(3000, self._refresh_interfaces)

    def _restore_kill_btn(self):
        self.kill_btn.setEnabled(True)
        self.kill_btn.setText("🛑 KILL")

    def _do_reboot_james(self):
        """Full reboot: kill tools, clear state, re-init, refresh everything."""
        reply = QMessageBox.question(
            self,
            "🔄 Reboot JAMES",
            "This will:\n\n"
            "• Kill ALL running tools\n"
            "• Restore wireless interfaces\n"
            "• Clear agent context & chat history\n"
            "• Re-initialize the orchestrator\n"
            "• Refresh all interfaces\n\n"
            "Saved targets and loot are preserved.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.reboot_btn.setEnabled(False)
        self.reboot_btn.setText("⏳ ...")
        self._term_print("🔄 REBOOT — Starting full restart...")

        def _do_reboot():
            try:
                self.orch.kill_james()
            except Exception:
                pass
            return True

        w = WorkerThread(_do_reboot)
        w.finished.connect(self._on_reboot_complete)
        w.error.connect(lambda e: (
            self._term_print(f"[ERROR] Reboot failed: {e}"),
            self._restore_reboot_btn(),
        ))
        self._start_worker(w)

    def _on_reboot_complete(self, _):
        """Post-reboot re-initialization."""
        # Clear agent state
        try:
            self.chat_panel.agent.context.clear()
            self.chat_panel.agent._save_context()
        except Exception:
            pass

        # Clear chat log and re-show welcome
        self.chat_panel.chat_log.clear()
        self.chat_panel._show_welcome()

        # Clear terminal
        self.terminal.clear()
        self._term_print("🔄 JAMES rebooted successfully.")
        self._term_print(f"[SYS] {len(self.known_targets)} saved targets preserved.")

        # Refresh interfaces
        QTimer.singleShot(1000, self._refresh_interfaces)

        # Refresh context strip
        self._refresh_context_strip()

        # Restore button
        self._restore_reboot_btn()

        # Toast
        show_toast(self, "JAMES rebooted — ready for action", "success", 3000)

    def _restore_reboot_btn(self):
        self.reboot_btn.setEnabled(True)
        self.reboot_btn.setText("🔄 REBOOT")

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Log", "/home/malcolm/Desktop/james_log.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump(self.orch.export_log(), f, indent=2)
            self._term_print(f"[LOG] Exported to {path}")

    def _generate_gui_report(self):
        """Generate professional HTML pentest report from GUI."""
        import subprocess
        from james.core.report import generate_html_report, save_report

        self._term_print("[REPORT] Generating HTML report...")
        try:
            log = self.orch.export_log()
            skills = self.orch.list_skills()
            tool_status = self.orch.system_check()
            loot = self.orch.get_loot_summary()

            ctx = {}
            try:
                ctx = self.chat_panel.agent.context
            except AttributeError:
                pass

            html = generate_html_report(
                task_log=log,
                context=ctx,
                loot_summary=loot,
                tool_status=tool_status,
                skills=skills,
                known_targets=self.known_targets,
            )

            report_path = save_report(html)
            self._term_print(f"[REPORT] Saved to {report_path}")

            # Try to open in browser
            try:
                subprocess.Popen(["xdg-open", str(report_path)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._term_print("[REPORT] Opened in browser.")
            except Exception:
                pass

            QMessageBox.information(self, "Report Generated",
                                    f"Report saved to:\n{report_path}")
        except Exception as e:
            self._term_print(f"[ERROR] Report generation failed: {e}")
            QMessageBox.warning(self, "Report Error", f"Failed: {e}")

    # ── task log callback ───────────────────────────────────────

    def _on_task_update(self, entry):
        """Called from orchestrator (possibly worker thread)."""
        self.append_output.emit(f"[{entry.status.upper()}] {entry.action} ({entry.tool})")
        self.refresh_log.emit()  # rebuild log table on task events only

    def _refresh_log_table(self):
        log = self.orch.export_log()
        self.log_table.setRowCount(0)
        for e in log:
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem(e["timestamp"]))
            self.log_table.setItem(row, 1, QTableWidgetItem(e["action"]))
            self.log_table.setItem(row, 2, QTableWidgetItem(e["tool"]))

            status_text = e["status"]
            status_item = QTableWidgetItem(status_text)
            if status_text.lower() in ("ok", "success", "done"):
                status_item.setForeground(QColor("#00ff88"))
            elif status_text.lower() in ("error", "failed", "timeout"):
                status_item.setForeground(QColor("#ff4757"))
            else:
                status_item.setForeground(QColor("#ffcc00"))
            self.log_table.setItem(row, 3, status_item)

            details = json.dumps(e.get("result", {}))[:120] if e.get("result") else ""
            self.log_table.setItem(row, 4, QTableWidgetItem(details))

        # Update counter
        try:
            self.log_count_label.setText(f"📋 {len(log)} tasks logged")
        except AttributeError:
            pass

    # ── helpers ─────────────────────────────────────────────────

    def _term_print(self, text: str):
        self.append_output.emit(text)
        # Trigger toast notifications for important events
        text_lower = text.lower() if text else ""
        if "[error]" in text_lower or "failed" in text_lower:
            show_toast(self, text[:80], "error", 4000)
            self._notify_tab(1)  # Dashboard
        elif "[autopwn]" in text_lower and "complete" in text_lower:
            show_toast(self, "AutoPwn workflow complete!", "success", 5000)
        elif "[one-click]" in text_lower and "finished" in text_lower:
            show_toast(self, text[:80], "success", 4000)
        elif "cracked" in text_lower and ("key" in text_lower or "password" in text_lower):
            show_toast(self, text[:80], "success", 6000)

    def _update_all_target_comboboxes(self):
        targets = sorted(list(self.known_targets))
        for cb in self.target_comboboxes:
            # We don't want to clear and lose the text if the user was typing
            current = cb.currentText()
            cb.clear()
            cb.addItems(targets)
            cb.setCurrentText(current)
        self._save_targets()

    # Terminal syntax highlighting patterns
    _TERM_HIGHLIGHT_RULES = [
        # IPs and CIDRs
        (re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)'), r'<span style="color:#00f0ff;">\1</span>'),
        # MAC addresses / BSSIDs
        (re.compile(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})'), r'<span style="color:#ff6b35;">\1</span>'),
        # [ERROR] tags
        (re.compile(r'(\[ERROR\])'), r'<span style="color:#ff4757;font-weight:bold;">\1</span>'),
        # [OK] / [+] tags
        (re.compile(r'(\[\+\]|\[OK\])'), r'<span style="color:#00ff88;font-weight:bold;">\1</span>'),
        # [SYS] / [INFO] tags
        (re.compile(r'(\[SYS\]|\[INFO\])'), r'<span style="color:#5a9abf;">\1</span>'),
        # [AUTOPWN] / [ONE-CLICK] tags
        (re.compile(r'(\[AUTOPWN\]|\[ONE-CLICK\]|\[TEST\])'), r'<span style="color:#ff6b35;font-weight:bold;">\1</span>'),
        # Port numbers (e.g., 22/tcp, 80/tcp)
        (re.compile(r'(\d{1,5}/(?:tcp|udp))'), r'<span style="color:#ff6b35;">\1</span>'),
    ]

    def _do_append(self, text: str):
        # Apply syntax highlighting via HTML
        escaped = (text
                   .replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))

        highlighted = escaped
        for pattern, replacement in self._TERM_HIGHLIGHT_RULES:
            highlighted = pattern.sub(replacement, highlighted)

        # If we actually highlighted something, use HTML insert
        if highlighted != escaped:
            self.terminal.appendHtml(
                f'<pre style="margin:0; padding:0; color:#c8d6e5; '
                f'font-family:JetBrains Mono,monospace; font-size:11px;">{highlighted}</pre>'
            )
        else:
            self.terminal.appendPlainText(text)

        # Cap terminal at MAX_TERMINAL_LINES to prevent unbounded memory growth
        doc = self.terminal.document()
        if doc.blockCount() > self.MAX_TERMINAL_LINES:
            cursor = QTextCursor(doc.begin())
            cursor.movePosition(
                QTextCursor.Down, QTextCursor.KeepAnchor,
                doc.blockCount() - self.MAX_TERMINAL_LINES,
            )
            cursor.removeSelectedText()

        # Auto-scroll (respects toggle)
        if self._term_auto_scroll:
            self.terminal.moveCursor(QTextCursor.End)

        # Update line count
        try:
            self._term_line_label.setText(f"{doc.blockCount()} lines")
        except AttributeError:
            pass

        self.status.showMessage(text[:120], 3000)

    def _wifi_print(self, text):
        self.wifi_output.appendPlainText(str(text))

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _start_worker(self, worker: WorkerThread):
        self._workers.append(worker)
        self._start_activity("SCANNING")
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.finished.connect(self._stop_activity)
        worker.finished.connect(worker.deleteLater)  # prevent thread leak
        worker.error.connect(self._stop_activity)
        worker.start()

    # ── target persistence ───────────────────────────────────────

    def _load_targets(self):
        """Load known targets from disk."""
        try:
            if self._targets_file.exists():
                data = json.loads(self._targets_file.read_text())
                if isinstance(data, list):
                    self.known_targets = set(data)
                    if self.known_targets:
                        self._term_print(f"[SYS] Loaded {len(self.known_targets)} saved targets")
        except Exception:
            pass  # file corrupt / missing — start fresh

    def _save_targets(self):
        """Persist known targets to disk."""
        try:
            self._targets_file.parent.mkdir(parents=True, exist_ok=True)
            self._targets_file.write_text(json.dumps(sorted(self.known_targets)))
        except Exception:
            pass

    # ── graceful shutdown ───────────────────────────────────────

    def closeEvent(self, event):
        """Ask user whether to clean up before closing."""
        self._save_targets()
        reply = QMessageBox.question(
            self, "Exit JAMES",
            "Run kill_james (restore interfaces, kill tools) before closing?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Cancel:
            event.ignore()
            return
        if reply == QMessageBox.Yes:
            self._term_print("Running kill_james before exit...")
            try:
                self.orch.kill_james()
            except Exception as e:
                self._term_print(f"Cleanup error: {e}")
        # Stop timers
        self._ctx_timer.stop()
        self._clock_timer.stop()
        event.accept()
