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
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QGroupBox,
    QGridLayout, QComboBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QStatusBar, QFrame, QScrollArea,
    QToolButton, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor

from james.core.orchestrator import Orchestrator
from james.gui.chat_panel import ChatPanel

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

        self.setWindowTitle("JAMES — Linux Pentesting Agent")
        self.setMinimumSize(1100, 720)

        self._build_ui()
        self.append_output.connect(self._do_append)
        self.refresh_log.connect(self._refresh_log_table)
        
        self.orch.on_print = self._term_print

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

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("JAMES ready.")

        # Refresh context badges every 5 seconds (context rarely changes faster)
        self._ctx_timer = QTimer(self)
        self._ctx_timer.timeout.connect(self._refresh_context_strip)
        self._ctx_timer.start(5000)

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
        """Inject a quick-action command into the chat panel."""
        # If cmd has a placeholder like {target}, use context or ask
        if "{target}" in cmd:
            target = self.orch  # just use chat for now
            self.chat_panel.input_field.setText("scan ")
            self.chat_panel.input_field.setFocus()
            self.tabs.setCurrentIndex(0)
            return
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
        ver = QLabel("v0.4.0")
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
        lay.setContentsMargins(12, 12, 12, 12)

        # left: system status
        status_group = QGroupBox("System Status")
        self.status_grid = QGridLayout(status_group)
        self.tool_labels: dict[str, QLabel] = {}
        lay.addWidget(status_group, 1)

        # right: terminal
        term_group = QGroupBox("Terminal Output")
        term_lay = QVBoxLayout(term_group)
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(5000)
        self.terminal.setFont(QFont("JetBrains Mono", 11))
        term_lay.addWidget(self.terminal)

        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter command…")
        self.cmd_input.returnPressed.connect(self._run_manual_cmd)
        cmd_row.addWidget(self.cmd_input)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self._run_manual_cmd)
        cmd_row.addWidget(run_btn)
        term_lay.addLayout(cmd_row)

        lay.addWidget(term_group, 2)
        return w

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

        # Extract variables
        vars_needed = set()
        for step in skill_data.get("steps", []):
            for _, v in step.get("params", {}).items():
                if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                    vars_needed.add(v[2:-2].strip())

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

        self.recon_quick_btn = QPushButton("Quick Scan")
        self.recon_quick_btn.clicked.connect(self._do_quick_scan)
        row.addWidget(self.recon_quick_btn)

        self.recon_full_btn = QPushButton("Full Scan")
        self.recon_full_btn.clicked.connect(self._do_full_scan)
        row.addWidget(self.recon_full_btn)
        lay.addLayout(row)

        # results table
        self.recon_table = QTableWidget(0, 5)
        self.recon_table.setHorizontalHeaderLabels(["Host", "Port", "State", "Service", "Version"])
        self.recon_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.recon_table)

        return w

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

        iface_row.addStretch()
        lay.addLayout(iface_row)

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
        self.ap_table.setStyleSheet("QTableWidget { background: #060a12; gridline-color: #141e30; }")
        self.ap_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ap_table.itemDoubleClicked.connect(self._ap_table_select)
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
        wpa_group = QGroupBox("WPA Handshake Crack (aircrack-ng)")
        glay = QGridLayout(wpa_group)

        glay.addWidget(QLabel("Capture (.cap):"), 0, 0)
        self.cap_path = QLineEdit()
        glay.addWidget(self.cap_path, 0, 1)
        cap_browse = QPushButton("Browse")
        cap_browse.clicked.connect(lambda: self._browse(self.cap_path, "*.cap"))
        glay.addWidget(cap_browse, 0, 2)

        glay.addWidget(QLabel("Wordlist:"), 1, 0)
        self.wl_path = QLineEdit("/home/malcolm/Desktop/rockyou.txt")
        glay.addWidget(self.wl_path, 1, 1)
        wl_browse = QPushButton("Browse")
        wl_browse.clicked.connect(lambda: self._browse(self.wl_path, "*"))
        glay.addWidget(wl_browse, 1, 2)

        crack_btn = QPushButton("⚡ Crack")
        crack_btn.clicked.connect(self._do_crack_wpa)
        glay.addWidget(crack_btn, 2, 1)
        lay.addWidget(wpa_group)

        # Hash cracking
        hash_group = QGroupBox("Hash Crack (hashcat)")
        hlay = QGridLayout(hash_group)
        hlay.addWidget(QLabel("Hash File:"), 0, 0)
        self.hash_path = QLineEdit()
        hlay.addWidget(self.hash_path, 0, 1)
        h_browse = QPushButton("Browse")
        h_browse.clicked.connect(lambda: self._browse(self.hash_path, "*"))
        hlay.addWidget(h_browse, 0, 2)

        hlay.addWidget(QLabel("Mode:"), 1, 0)
        self.hash_mode = QComboBox()
        self.hash_mode.addItems(["0 - MD5", "100 - SHA1", "1400 - SHA256",
                                  "1800 - sha512crypt", "2500 - WPA/WPA2",
                                  "3200 - bcrypt"])
        hlay.addWidget(self.hash_mode, 1, 1)

        hcrack_btn = QPushButton("⚡ Crack Hash")
        hcrack_btn.clicked.connect(self._do_crack_hash)
        hlay.addWidget(hcrack_btn, 2, 1)
        lay.addWidget(hash_group)

        # result output
        self.crack_output = QPlainTextEdit()
        self.crack_output.setReadOnly(True)
        lay.addWidget(self.crack_output)

        return w

    # ── Log tab ─────────────────────────────────────────────────

    def _make_log_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        self.log_table = QTableWidget(0, 5)
        self.log_table.setHorizontalHeaderLabels(["Time", "Action", "Tool", "Status", "Details"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.log_table)

        export_btn = QPushButton("Export Log (JSON)")
        export_btn.clicked.connect(self._export_log)
        lay.addWidget(export_btn)
        return w

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

        row = 0
        for tool, available in status.items():
            name_lbl = QLabel(f"  {tool}")
            name_lbl.setStyleSheet("font-size: 14px;")
            status_lbl = QLabel("● INSTALLED" if available else "✕ MISSING")
            status_lbl.setObjectName("statusOk" if available else "statusBad")
            self.status_grid.addWidget(name_lbl, row, 0)
            self.status_grid.addWidget(status_lbl, row, 1)
            self.tool_labels[tool] = status_lbl
            row += 1

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
        self._wifi_print(f"[DEAUTH] → {bssid} x{count}")
        w = WorkerThread(self.orch.aircrack.deauth, iface, bssid, count=count)
        w.finished.connect(lambda r: self._wifi_print(r.stdout if r else "done"))
        self._start_worker(w)

    def _do_crack_wpa(self):
        cap = self.cap_path.text().strip()
        wl = self.wl_path.text().strip()
        if not cap or not wl:
            return
        self.crack_output.setPlainText("Cracking in progress…\n")
        w = WorkerThread(self.orch.crack_handshake, cap, wl)
        w.finished.connect(self._show_crack_result)
        self._start_worker(w)

    def _do_autopwn(self):
        iface_text = self.wifi_iface.currentText()
        if not iface_text:
            QMessageBox.warning(self, "No Interface", "Please select a Wi-Fi interface first.")
            return
        iface = iface_text.split()[0]
        
        # We need a wordlist
        wordlist, _ = QFileDialog.getOpenFileName(self, "Select Wordlist for AutoPwn", "/home/malcolm/Desktop", "*")
        if not wordlist:
            return
            
        self._term_print(f"[AUTOPWN] Triggered on interface {iface} with wordlist {wordlist}")
        self.autopwn_btn.setEnabled(False)
        w = WorkerThread(self.orch.auto_wifi_pwn, iface, wordlist)
        w.finished.connect(lambda r: self._term_print(f"[AUTOPWN] Workflow complete: {json.dumps(r)}"))
        w.finished.connect(lambda _: self.autopwn_btn.setEnabled(True))
        w.error.connect(lambda e: (self._term_print(f"[ERROR] AutoPwn failed: {e}"), self.autopwn_btn.setEnabled(True)))
        self._start_worker(w)

    def _do_crack_hash(self):
        hf = self.hash_path.text().strip()
        wl = self.wl_path.text().strip()
        if not hf or not wl:
            return
        mode = int(self.hash_mode.currentText().split(" - ")[0])
        self.crack_output.setPlainText("Cracking hash…\n")
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
        wordlist, _ = QFileDialog.getOpenFileName(self, "Select Wordlist", "/home/malcolm/Desktop", "*")
        if not wordlist:
            return
        self._term_print(f"[ONE-CLICK] 🔥 Wi-Fi Blitz on {iface}")
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

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Log", "/home/malcolm/Desktop/james_log.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump(self.orch.export_log(), f, indent=2)
            self._term_print(f"[LOG] Exported to {path}")

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
            self.log_table.setItem(row, 3, QTableWidgetItem(e["status"]))
            details = json.dumps(e.get("result", {}))[:120] if e.get("result") else ""
            self.log_table.setItem(row, 4, QTableWidgetItem(details))

    # ── helpers ─────────────────────────────────────────────────

    def _term_print(self, text: str):
        self.append_output.emit(text)

    def _update_all_target_comboboxes(self):
        targets = sorted(list(self.known_targets))
        for cb in self.target_comboboxes:
            # We don't want to clear and lose the text if the user was typing
            current = cb.currentText()
            cb.clear()
            cb.addItems(targets)
            cb.setCurrentText(current)

    def _do_append(self, text: str):
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
        self.terminal.moveCursor(QTextCursor.End)
        self.status.showMessage(text[:120])

    def _wifi_print(self, text):
        self.wifi_output.appendPlainText(str(text))

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _start_worker(self, worker: WorkerThread):
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.finished.connect(worker.deleteLater)  # prevent thread leak
        worker.start()

    # ── graceful shutdown ───────────────────────────────────────

    def closeEvent(self, event):
        """Ask user whether to clean up before closing."""
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
