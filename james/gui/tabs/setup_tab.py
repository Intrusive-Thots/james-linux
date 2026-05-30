"""JAMES — Setup Tab (Layout v2)."""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QLineEdit,
    QFormLayout,
    QFrame,
    QSizePolicy,
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
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # ── Section header ──
        hdr = QLabel("⚙️  System Configuration")
        hdr.setObjectName("sectionLabel")
        layout.addWidget(hdr)

        # ── Internet Connection Sharing ──
        bridge_group = QGroupBox("Internet Connection Sharing (ICS)")
        bridge_layout = QVBoxLayout(bridge_group)
        bridge_layout.setSpacing(12)

        desc = QLabel(
            "Bridge a local Ethernet interface with your active internet connection — "
            "useful for sharing connectivity with downstream hardware (e.g. Wi-Fi Pineapple)."
        )
        desc.setWordWrap(True)
        desc.setObjectName("dimLabel")
        bridge_layout.addWidget(desc)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setSpacing(8)
        self.txt_lan_iface = QLineEdit("enp45s0")
        self.txt_lan_iface.setPlaceholderText("e.g. eth0, enp3s0")
        self.txt_wan_iface = QLineEdit("wlo1")
        self.txt_wan_iface.setPlaceholderText("e.g. wlan0, wlo1")
        form.addRow("Local Interface (LAN):", self.txt_lan_iface)
        form.addRow("Internet Interface (WAN):", self.txt_wan_iface)
        bridge_layout.addLayout(form)

        self.btn_bridge = QPushButton("🔗  Enable ICS  (Bridge Networks)")
        self.btn_bridge.setObjectName("primaryBtn")
        self.btn_bridge.setMinimumHeight(40)
        bridge_layout.addWidget(self.btn_bridge)
        layout.addWidget(bridge_group)

        # ── Interface Management ──
        iface_group = QGroupBox("Interface & Firewall Management")
        iface_layout = QVBoxLayout(iface_group)
        iface_layout.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_restart_nm = QPushButton("🔄  Restart NetworkManager")
        self.btn_restart_nm.setMinimumHeight(38)
        self.btn_flush_iptables = QPushButton("🧹  Flush iptables")
        self.btn_flush_iptables.setObjectName("warnBtn")
        self.btn_flush_iptables.setMinimumHeight(38)
        row.addWidget(self.btn_restart_nm)
        row.addWidget(self.btn_flush_iptables)
        iface_layout.addLayout(row)
        layout.addWidget(iface_group)

        layout.addStretch()

    def _connect_signals(self):
        self.btn_bridge.clicked.connect(self.setup_ics)
        self.btn_restart_nm.clicked.connect(self.restart_nm)
        self.btn_flush_iptables.clicked.connect(self.flush_iptables)

    def setup_ics(self):
        lan = self.txt_lan_iface.text().strip()
        wan = self.txt_wan_iface.text().strip()
        if not lan or not wan:
            show_toast(
                self.main_window, "Enter both LAN and WAN interfaces", "error"
            )
            return
        self.main_window._set_idle(False)
        self.main_window._append_log(f"🔗 Setting up ICS: {lan} → {wan}")

        def _do():
            self.orchestrator.layer.run(
                f"nmcli connection add type ethernet ifname {lan} "
                f"ipv4.method shared con-name Shared-Ethernet",
                sudo=True,
            )
            self.orchestrator.layer.run(
                "nmcli connection up Shared-Ethernet", sudo=True
            )
            return {"success": True}

        self.worker = WorkerThread(_do)
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()

    def restart_nm(self):
        self.main_window._set_idle(False)
        self.main_window._append_log("🔄 Restarting NetworkManager…")
        self.worker = WorkerThread(
            self.orchestrator.layer.run,
            "systemctl restart NetworkManager",
            sudo=True,
        )
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()

    def flush_iptables(self):
        self.main_window._set_idle(False)
        self.main_window._append_log("🧹 Flushing iptables…")
        self.worker = WorkerThread(
            self.orchestrator.layer.run,
            "iptables --flush && iptables -t nat --flush",
            sudo=True,
        )
        self.worker.finished.connect(self._on_setup_done)
        self.worker.start()

    def _on_setup_done(self, res):
        self.main_window._set_idle(True)
        if isinstance(res, Exception):
            show_toast(self.main_window, f"Error: {res}", "error")
        else:
            show_toast(self.main_window, "Operation completed", "success")
