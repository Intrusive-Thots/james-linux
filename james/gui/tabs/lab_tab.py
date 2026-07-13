"""JAMES — Lab Tab (Experimental WPA3 Features)."""

from PyQt5.QtWidgets import (
    QShortcut,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QComboBox,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
import logging

logger = logging.getLogger(__name__)

class LabTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Header
        hdr = QLabel("🔬  Experimental Wireless Lab")
        hdr.setObjectName("sectionLabel")
        layout.addWidget(hdr)

        # Warning Alert/Callout
        warning_box = QFrame()
        warning_box.setObjectName("warningBox")
        warning_box.setStyleSheet(
            "QFrame { background: #2b1f1d; border: 1px solid #d9534f; border-radius: 6px; padding: 12px; }"
        )
        warning_layout = QVBoxLayout(warning_box)
        warning_title = QLabel("⚠️ EXPERIMENTAL FEATURES")
        warning_title.setStyleSheet("font-weight: bold; color: #d9534f; font-size: 13px;")
        warning_desc = QLabel(
            "These modules test cutting-edge wireless methodologies. They may be unstable, "
            "require specific firmware/SDR support, or not work in your current deployment environment."
        )
        warning_desc.setWordWrap(True)
        warning_desc.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_desc)
        layout.addWidget(warning_box)

        # WPA3 SAE Fuzzer
        fuzz_group = QGroupBox("WPA3 SAE Fuzzing Simulation")
        fuzz_layout = QVBoxLayout(fuzz_group)
        fuzz_layout.setSpacing(12)

        fuzz_desc = QLabel(
            "Emulate a WPA3 Access Point and transmit fuzzed/malformed SAE / EAPOL frames to test "
            "the robustness of client-side authentication state machines."
        )
        fuzz_desc.setWordWrap(True)
        fuzz_desc.setObjectName("dimLabel")
        fuzz_layout.addWidget(fuzz_desc)

        fuzz_controls = QHBoxLayout()
        fuzz_controls.setSpacing(8)
        self.cmb_fuzz_iface = QComboBox()
        self.cmb_fuzz_iface.setPlaceholderText("Select Interface")
        self.btn_run_fuzz = QPushButton("⚡ Start SAE Fuzzing")
        self.btn_run_fuzz.setObjectName("warnBtn")
        self.btn_run_fuzz.setToolTip("Start SAE Fuzzing on the selected interface (Ctrl+F)")
        self.btn_run_fuzz.setMinimumHeight(38)
        fuzz_controls.addWidget(self.cmb_fuzz_iface, stretch=1)
        fuzz_controls.addWidget(self.btn_run_fuzz, stretch=1)
        fuzz_layout.addLayout(fuzz_controls)
        layout.addWidget(fuzz_group)

        # Transition Mode Downgrade
        down_group = QGroupBox("WPA3 Transition-Mode Downgrade")
        down_layout = QVBoxLayout(down_group)
        down_layout.setSpacing(12)

        down_desc = QLabel(
            "Simulate downgrade request frames against dual WPA2/WPA3 (Transition Mode) networks. "
            "Attempts to force target clients to fall back to vulnerable legacy WPA2 mechanisms."
        )
        down_desc.setWordWrap(True)
        down_desc.setObjectName("dimLabel")
        down_layout.addWidget(down_desc)

        down_controls = QHBoxLayout()
        down_controls.setSpacing(8)
        self.cmb_down_iface = QComboBox()
        self.cmb_down_iface.setPlaceholderText("Select Interface")
        self.btn_run_down = QPushButton("🐉 Trigger Downgrade")
        self.btn_run_down.setObjectName("primaryBtn")
        self.btn_run_down.setToolTip("Trigger Downgrade on the selected interface (Ctrl+D)")
        self.btn_run_down.setMinimumHeight(38)
        down_controls.addWidget(self.cmb_down_iface, stretch=1)
        down_controls.addWidget(self.btn_run_down, stretch=1)
        down_layout.addLayout(down_controls)
        layout.addWidget(down_group)

        layout.addStretch()

        # Connect placeholders
        self.btn_run_fuzz.clicked.connect(self._on_fuzz_clicked)
        self.btn_run_down.clicked.connect(self._on_down_clicked)

        # Populate interface combo boxes
        self._refresh_interfaces()
        self._build_shortcuts()

    def _build_shortcuts(self):
        sc_f = QShortcut(QKeySequence("Ctrl+F"), self)
        sc_f.setContext(Qt.WidgetWithChildrenShortcut)
        sc_f.activated.connect(self._on_fuzz_clicked)

        sc_d = QShortcut(QKeySequence("Ctrl+D"), self)
        sc_d.setContext(Qt.WidgetWithChildrenShortcut)
        sc_d.activated.connect(self._on_down_clicked)

    def _refresh_interfaces(self):
        try:
            ifaces = self.orchestrator.layer.list_interfaces()
            for cb in (self.cmb_fuzz_iface, self.cmb_down_iface):
                cb.clear()
                cb.addItems(ifaces)
        except Exception as e:
            logger.warning("Failed to refresh interfaces in Lab tab: %s", e)

    def _on_fuzz_clicked(self):
        iface = self.cmb_fuzz_iface.currentText()
        if not iface:
            from james.gui.toast import show_toast
            show_toast(self.main_window, "Please select an interface first.", "WARN")
            return
        logger.info("Experimental WPA3 Fuzzer started on interface %s", iface)
        from james.gui.toast import show_toast
        show_toast(self.main_window, f"Started SAE fuzzing on {iface}", "INFO")

    def _on_down_clicked(self):
        iface = self.cmb_down_iface.currentText()
        if not iface:
            from james.gui.toast import show_toast
            show_toast(self.main_window, "Please select an interface first.", "WARN")
            return
        logger.info("Experimental WPA3 Downgrade started on interface %s", iface)
        from james.gui.toast import show_toast
        show_toast(self.main_window, f"Triggered transition downgrade on {iface}", "INFO")
