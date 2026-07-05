"""JAMES — Troubleshoot Tab (Layout v2)."""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QPlainTextEdit,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QShortcut,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QKeySequence

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread
from james.gui.theme import LOG_STYLE

DEPS = [
    "aircrack-ng",
    "hashcat",
    "hcxdumptool",
    "hcxpcapngtool",
    "hostapd",
    "dnsmasq",
    "macchanger",
    "nmap",
    "hydra",
    "nikto",
    "gobuster",
    "reaver",
    "bully",
    "mdk4",
    "sqlmap",
    "sslscan",
    "ettercap",
    "masscan",
    "john",
]


class TroubleshootTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self.worker = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        hdr = QLabel("🔧  System Diagnostics")
        hdr.setObjectName("sectionLabel")
        layout.addWidget(hdr)

        # ── Dependency checker ──
        dep_group = QGroupBox("Dependency Status")
        dep_layout = QVBoxLayout(dep_group)
        dep_layout.setSpacing(8)

        btn_row = QHBoxLayout()
        self.btn_check_deps = QPushButton("🔍  Check All Dependencies")
        self.btn_check_deps.setObjectName("primaryBtn")
        self.btn_check_deps.setMinimumHeight(38)
        self.btn_check_deps.setToolTip("Check all dependencies (Ctrl+R)")

        self.btn_install_deps = QPushButton("⚡  Auto-Install Missing")
        self.btn_install_deps.setObjectName("successBtn")
        self.btn_install_deps.setMinimumHeight(38)
        self.btn_install_deps.setToolTip("Auto-install missing dependencies (Ctrl+I)")

        btn_row.addWidget(self.btn_check_deps)
        btn_row.addWidget(self.btn_install_deps)
        dep_layout.addLayout(btn_row)

        self.dep_table = QTableWidget(0, 3)
        self.dep_table.setHorizontalHeaderLabels(["Tool", "Status", "Path"])
        self.dep_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.dep_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.dep_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.dep_table.setMaximumHeight(220)
        self.dep_table.verticalHeader().setVisible(False)
        self.dep_table.setEditTriggers(QTableWidget.NoEditTriggers)
        dep_layout.addWidget(self.dep_table)
        layout.addWidget(dep_group)

        # ── System info / log viewer ──
        diag_group = QGroupBox("System Information")
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setSpacing(8)

        diag_btns = QHBoxLayout()
        self.btn_view_logs = QPushButton("📄  dmesg (kernel log)")
        self.btn_view_logs.setMinimumHeight(36)
        self.btn_iw_list = QPushButton("📡  iw list (Wi-Fi caps)")
        self.btn_iw_list.setMinimumHeight(36)
        self.btn_ip_link = QPushButton("🔌  ip link (interfaces)")
        self.btn_ip_link.setMinimumHeight(36)
        diag_btns.addWidget(self.btn_view_logs)
        diag_btns.addWidget(self.btn_iw_list)
        diag_btns.addWidget(self.btn_ip_link)
        diag_layout.addLayout(diag_btns)

        self.txt_output = QPlainTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setStyleSheet(LOG_STYLE)
        self.txt_output.setFont(QFont("JetBrains Mono", 13))
        self.txt_output.setMinimumHeight(160)
        diag_layout.addWidget(self.txt_output)
        layout.addWidget(diag_group)

        # ── Emergency ──
        emerg_group = QGroupBox("Emergency Actions")
        emerg_layout = QHBoxLayout(emerg_group)
        emerg_layout.setSpacing(8)

        self.btn_kill_all = QPushButton("🛑  Kill All Pentesting Processes")
        self.btn_kill_all.setObjectName("dangerBtn")
        self.btn_kill_all.setMinimumHeight(42)

        self.btn_restore_nm = QPushButton("🔄  Full Network Restore")
        self.btn_restore_nm.setObjectName("warnBtn")
        self.btn_restore_nm.setMinimumHeight(42)

        emerg_layout.addWidget(self.btn_kill_all, stretch=2)
        emerg_layout.addWidget(self.btn_restore_nm, stretch=1)
        layout.addWidget(emerg_group)

    def _connect_signals(self):
        self.btn_check_deps.clicked.connect(self.check_deps)
        self.btn_install_deps.clicked.connect(self.install_deps)

        sc_r = QShortcut(QKeySequence("Ctrl+R"), self)
        sc_r.setContext(Qt.WidgetWithChildrenShortcut)
        sc_r.activated.connect(self.check_deps)

        sc_i = QShortcut(QKeySequence("Ctrl+I"), self)
        sc_i.setContext(Qt.WidgetWithChildrenShortcut)
        sc_i.activated.connect(self.install_deps)

        self.btn_view_logs.clicked.connect(
            lambda: self._run_cmd("dmesg | tail -n 60")
        )
        self.btn_iw_list.clicked.connect(lambda: self._run_cmd("iw list"))
        self.btn_ip_link.clicked.connect(lambda: self._run_cmd("ip link show"))
        self.btn_kill_all.clicked.connect(self.kill_processes)
        self.btn_restore_nm.clicked.connect(self.restore_network)

    # ── Actions ───────────────────────────────────────────────────────

    def check_deps(self):
        self.main_window._set_idle(False)
        self.dep_table.setRowCount(0)

        def _do():
            results = []
            for dep in DEPS:
                r = self.orchestrator.layer.run(f"which {dep}", timeout=5)
                path = r.stdout.strip() if r.returncode == 0 else ""
                results.append((dep, r.returncode == 0, path))
            return results

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(self._on_deps_done)
        self.worker.start()

    def _on_deps_done(self, results):
        self.main_window._set_idle(True)
        if isinstance(results, Exception):
            show_toast(self.main_window, f"Check failed: {results}", "error")
            return

        self.dep_table.setRowCount(0)
        missing = 0
        for name, installed, path in results:
            row = self.dep_table.rowCount()
            self.dep_table.insertRow(row)

            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor("#c8d6e5"))

            if installed:
                status_item = QTableWidgetItem("✅  INSTALLED")
                status_item.setForeground(QColor("#00ff88"))
                path_item = QTableWidgetItem(path)
                path_item.setForeground(QColor("#4a6a8a"))
            else:
                status_item = QTableWidgetItem("❌  MISSING")
                status_item.setForeground(QColor("#ff4757"))
                path_item = QTableWidgetItem("—")
                path_item.setForeground(QColor("#3a5a7a"))
                missing += 1

            self.dep_table.setItem(row, 0, name_item)
            self.dep_table.setItem(row, 1, status_item)
            self.dep_table.setItem(row, 2, path_item)

        show_toast(
            self.main_window,
            f"{len(results) - missing}/{len(results)} dependencies installed",
            "success" if missing == 0 else "error",
        )

    def install_deps(self):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText("⚡ Installing missing dependencies…\n")
        self.worker = WorkerThread(self.orchestrator.auto_install_deps)
        self.worker.finished.connect(
            lambda r: (
                self.main_window._set_idle(True),
                self.txt_output.appendPlainText(str(r)),
                show_toast(self.main_window, "Install complete", "success"),
            )
        )
        self.worker.start()

    def _run_cmd(self, cmd: str):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText(f"$ {cmd}\n")
        self.worker = WorkerThread(
            self.orchestrator.layer.run, cmd, timeout=15
        )
        self.worker.finished.connect(self._on_cmd_done)
        self.worker.start()

    def _on_cmd_done(self, result):
        self.main_window._set_idle(True)
        if isinstance(result, Exception):
            self.txt_output.appendPlainText(f"Error: {result}")
        else:
            output = (result.stdout + result.stderr).strip()
            self.txt_output.appendPlainText(output or "(no output)")

    def kill_processes(self):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText("🛑 Killing all pentesting processes…\n")
        self.worker = WorkerThread(
            self.orchestrator.layer.run,
            "killall airodump-ng aireplay-ng aircrack-ng hashcat hostapd "
            "dnsmasq hcxdumptool reaver bully mdk4 john hydra nmap 2>/dev/null; echo Done",
            sudo=True,
        )
        self.worker.finished.connect(
            lambda r: (
                self.main_window._set_idle(True),
                self.txt_output.appendPlainText("Done."),
                show_toast(self.main_window, "Processes killed", "success"),
            )
        )
        self.worker.start()

    def restore_network(self):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText("🔄 Restoring network…\n")
        self.worker = WorkerThread(self.orchestrator.kill_james)
        self.worker.finished.connect(
            lambda r: (
                self.main_window._set_idle(True),
                self.txt_output.appendPlainText(str(r)),
                show_toast(self.main_window, "Network restored", "success"),
            )
        )
        self.worker.start()
