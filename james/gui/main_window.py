"""
JAMES Dashboard — main PyQt5 window.

Panels:
  • System Status  — tool availability, interfaces
  • Terminal        — embedded command output with input
  • Task Launcher   — run scans / attacks from the GUI
  • Task Log        — history of orchestrator actions
"""

import json
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QGroupBox,
    QGridLayout, QComboBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QStatusBar, QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor

from james.core.orchestrator import Orchestrator
from james.gui.chat_panel import ChatPanel


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

    append_output = pyqtSignal(str)  # thread-safe terminal append

    def __init__(self):
        super().__init__()
        self.orch = Orchestrator()
        self.orch.on_task_update = self._on_task_update
        self._workers: list[WorkerThread] = []

        self.setWindowTitle("JAMES — Linux Pentesting Agent")
        self.setMinimumSize(1100, 720)

        self._build_ui()
        self.append_output.connect(self._do_append)
        
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

        # tab widget
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # AI Agent chat — the primary interface
        self.chat_panel = ChatPanel(self.orch)
        self.tabs.addTab(self.chat_panel, "🤖 Agent")

        self.tabs.addTab(self._make_dashboard_tab(), "⚡ Dashboard")
        self.tabs.addTab(self._make_oneclick_tab(), "🧪 One-Click Tests")
        self.tabs.addTab(self._make_recon_tab(), "🔍 Recon")
        self.tabs.addTab(self._make_wifi_tab(), "📡 Wi-Fi")
        self.tabs.addTab(self._make_cracking_tab(), "🔓 Cracking")
        self.tabs.addTab(self._make_log_tab(), "📋 Log")

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("JAMES ready.")

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
        ver = QLabel("v0.3.0")
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

    # ── One-Click Tests tab ─────────────────────────────────────

    def _make_oneclick_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(16)
        
        skills = self.orch.list_skills()
        if not skills:
            lay.addWidget(QLabel("No skills found in james/skills/ directory."))
        else:
            for skill_name in skills:
                skill_data = self.orch.load_skill(skill_name)
                if "error" in skill_data:
                    continue
                    
                group = QGroupBox(f"{skill_data.get('name', skill_name).replace('_', ' ').title()}")
                glay = QVBoxLayout(group)
                
                desc = QLabel(skill_data.get("description", ""))
                desc.setWordWrap(True)
                desc.setStyleSheet("color: #a0b0c0; font-style: italic;")
                glay.addWidget(desc)
                
                # Extract variables
                vars_needed = set()
                for step in skill_data.get("steps", []):
                    for _, v in step.get("params", {}).items():
                        if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                            vars_needed.add(v[2:-2].strip())
                
                input_fields = {}
                if vars_needed:
                    form_lay = QGridLayout()
                    for idx, var in enumerate(sorted(vars_needed)):
                        form_lay.addWidget(QLabel(f"{var}:"), idx, 0)
                        inp = QLineEdit()
                        inp.setPlaceholderText(f"Enter {var}...")
                        form_lay.addWidget(inp, idx, 1)
                        input_fields[var] = inp
                    glay.addLayout(form_lay)
                
                btn = QPushButton("▶ Run Test")
                btn.setStyleSheet("background-color: #2a4a3a; color: #00ff00; font-weight: bold;")
                
                # Use default args lambda binding trick
                btn.clicked.connect(lambda checked=False, s=skill_data, fields=input_fields: self._run_oneclick_test(s, fields))
                glay.addWidget(btn)
                
                lay.addWidget(group)
        
        lay.addStretch()
        scroll.setWidget(container)
        
        main_lay = QVBoxLayout(w)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(scroll)
        return w

    def _run_oneclick_test(self, skill_data, fields):
        context = {}
        for var_name, line_edit in fields.items():
            val = line_edit.text().strip()
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
        self.recon_target = QLineEdit()
        self.recon_target.setPlaceholderText("e.g. 192.168.1.0/24 or scanme.nmap.org")
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

        # deauth controls
        deauth_group = QGroupBox("Deauthentication")
        dlay = QHBoxLayout(deauth_group)
        dlay.addWidget(QLabel("BSSID:"))
        self.deauth_bssid = QLineEdit()
        self.deauth_bssid.setPlaceholderText("AA:BB:CC:DD:EE:FF")
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
        target = self.recon_target.text().strip()
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
        target = self.recon_target.text().strip()
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
        for host in result.get("hosts", []):
            addr = host["address"]
            for port in host.get("ports", []):
                row = self.recon_table.rowCount()
                self.recon_table.insertRow(row)
                self.recon_table.setItem(row, 0, QTableWidgetItem(addr))
                self.recon_table.setItem(row, 1, QTableWidgetItem(str(port["port"])))
                self.recon_table.setItem(row, 2, QTableWidgetItem(port["state"]))
                self.recon_table.setItem(row, 3, QTableWidgetItem(port["service"]))
                self.recon_table.setItem(row, 4, QTableWidgetItem(port["version"]))
        self._term_print(f"[RECON] Found {self.recon_table.rowCount()} open ports.")

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
        bssid = self.deauth_bssid.text().strip()
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

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Log", "/home/malcolm/Desktop/james_log.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump(self.orch.export_log(), f, indent=2)
            self._term_print(f"[LOG] Exported to {path}")

    # ── task log callback ───────────────────────────────────────

    def _on_task_update(self, entry):
        """Called from orchestrator (possibly worker thread)."""
        # safe to emit signal
        self.append_output.emit(f"[{entry.status.upper()}] {entry.action} ({entry.tool})")

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

    def _do_append(self, text: str):
        self.terminal.appendPlainText(text)
        self.terminal.moveCursor(QTextCursor.End)
        self.status.showMessage(text[:120])
        # also refresh log table
        self._refresh_log_table()

    def _wifi_print(self, text):
        self.wifi_output.appendPlainText(str(text))

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _start_worker(self, worker: WorkerThread):
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.start()
