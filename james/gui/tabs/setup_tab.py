from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, 
    QLineEdit, QFormLayout
)
from PyQt5.QtCore import Qt

from james.gui.toast import show_toast
from james.gui.utils.worker import WorkerThread

class SetupTab(QWidget):
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

        # ── Internet Connection Sharing ──
        bridge_group = QGroupBox("Internet Connection Sharing (ICS)")
        bridge_layout = QVBoxLayout(bridge_group)
        
        desc = QLabel("Bridge a local ethernet connection with the active internet connection to provide internet access to downstream devices (like a hardware Pineapple).")
        desc.setWordWrap(True)
        bridge_layout.addWidget(desc)
        
        form = QFormLayout()
        self.txt_lan_iface = QLineEdit("enp45s0")
        self.txt_wan_iface = QLineEdit("wlo1")
        form.addRow("Local Interface (LAN):", self.txt_lan_iface)
        form.addRow("Internet Interface (WAN):", self.txt_wan_iface)
        bridge_layout.addLayout(form)
        
        self.btn_bridge = QPushButton("🔗 ENABLE ICS (BRIDGE NETWORKS)")
        bridge_layout.addWidget(self.btn_bridge)
        layout.addWidget(bridge_group)

        # ── Interface Management ──
        iface_group = QGroupBox("Interface Management")
        iface_layout = QVBoxLayout(iface_group)
        
        self.btn_restart_nm = QPushButton("🔄 Restart NetworkManager")
        self.btn_flush_iptables = QPushButton("🧹 Flush iptables (Firewall)")
        iface_layout.addWidget(self.btn_restart_nm)
        iface_layout.addWidget(self.btn_flush_iptables)
        
        layout.addWidget(iface_group)
        layout.addStretch()

    def _connect_signals(self):
        self.btn_bridge.clicked.connect(self.setup_ics)
        self.btn_restart_nm.clicked.connect(self.restart_nm)
        self.btn_flush_iptables.clicked.connect(self.flush_iptables)

    def setup_ics(self):
        lan = self.txt_lan_iface.text()
        wan = self.txt_wan_iface.text()
        
        self.main_window._set_idle(False)
        self.main_window._append_log(f"Setting up ICS: {lan} -> {wan}")
        
        def _do_bridge():
            self.orchestrator.layer.run(f"nmcli connection add type ethernet ifname {lan} ipv4.method shared con-name Shared-Ethernet", sudo=True)
            self.orchestrator.layer.run(f"nmcli connection up Shared-Ethernet", sudo=True)
            return {"success": True}
            
        self.worker = WorkerThread(_do_bridge)
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()

    def restart_nm(self):
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.layer.run, "systemctl restart NetworkManager", sudo=True)
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()
        
    def flush_iptables(self):
        self.main_window._set_idle(False)
        self.worker = WorkerThread(self.orchestrator.layer.run, "iptables --flush && iptables -t nat --flush", sudo=True)
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()

    def _on_setup_done(self, res):
        self.main_window._set_idle(True)
        show_toast(self.main_window, "Setup", "Operation completed")
