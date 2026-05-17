from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QPlainTextEdit
)

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread

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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # ── Diagnostics ──
        diag_group = QGroupBox("System Diagnostics")
        diag_layout = QVBoxLayout(diag_group)
        
        row = QHBoxLayout()
        self.btn_check_deps = QPushButton("🔍 Check Dependencies")
        self.btn_view_logs = QPushButton("📄 View System Logs (dmesg)")
        row.addWidget(self.btn_check_deps)
        row.addWidget(self.btn_view_logs)
        diag_layout.addLayout(row)
        
        self.txt_output = QPlainTextEdit()
        self.txt_output.setReadOnly(True)
        diag_layout.addWidget(self.txt_output)
        
        layout.addWidget(diag_group)
        
        # ── Emergency ──
        emerg_group = QGroupBox("Emergency Actions")
        emerg_layout = QVBoxLayout(emerg_group)
        
        self.btn_kill_all = QPushButton("🛑 KILL ALL PENTESTING PROCESSES")
        self.btn_kill_all.setObjectName("dangerBtn")
        emerg_layout.addWidget(self.btn_kill_all)
        
        layout.addWidget(emerg_group)

    def _connect_signals(self):
        self.btn_check_deps.clicked.connect(self.check_deps)
        self.btn_view_logs.clicked.connect(self.view_logs)
        self.btn_kill_all.clicked.connect(self.kill_processes)

    def check_deps(self):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText("Checking dependencies...\n")
        
        def _do_check():
            deps = ["aircrack-ng", "hashcat", "hcxpcapngtool", "hostapd", "dnsmasq", "macchanger"]
            res = ""
            for d in deps:
                p = self.orchestrator.layer.run(f"which {d}")
                status = "INSTALLED" if p.returncode == 0 else "MISSING"
                res += f"{d}: {status}\n"
            return res
            
        self.worker = WorkerThread(_do_check)
        self.worker.finished.connect(self._on_check_done)
        self.worker.start()

    def _on_check_done(self, res):
        self.main_window._set_idle(True)
        self.txt_output.appendPlainText(str(res))

    def view_logs(self):
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.layer.run, "dmesg | tail -n 50")
        self.worker.finished.connect(self._on_logs_done)
        self.worker.start()
        
    def _on_logs_done(self, res):
        self.main_window._set_idle(True)
        if not isinstance(res, Exception):
            self.txt_output.setPlainText(res.stdout)

    def kill_processes(self):
        self.main_window._set_idle(False)
        self.txt_output.setPlainText("Killing processes...\n")
        self.worker = WorkerThread(self.orchestrator.layer.run, "killall airodump-ng aireplay-ng aircrack-ng hashcat hostapd dnsmasq 2>/dev/null", sudo=True)
        self.worker.finished.connect(lambda r: self._on_check_done("Processes killed."))
        self.worker.start()
