"""
JAMES — First-Launch Setup Wizard.

Shown on first run when GEMINI_API_KEY is not set.
Captures: API key, default wordlist, default Wi-Fi interface.
Saves settings to ~/.config/james/settings.json and can export to shell rc.
"""

import json
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QCheckBox,
    QFrame, QStackedWidget, QWidget, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

SETTINGS_FILE = Path.home() / ".config" / "james" / "settings.json"


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {}


def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def should_show_wizard() -> bool:
    """Return True if the wizard should be shown (no API key configured)."""
    if os.environ.get("GEMINI_API_KEY"):
        return False
    settings = load_settings()
    if settings.get("gemini_api_key"):
        return False
    if settings.get("wizard_skipped"):
        return False
    return True


def apply_settings_to_env(settings: dict):
    """Apply saved settings as environment variables for this process."""
    if settings.get("gemini_api_key"):
        os.environ["GEMINI_API_KEY"] = settings["gemini_api_key"]
    if settings.get("wordlist"):
        os.environ["JAMES_WORDLIST"] = settings["wordlist"]
    if settings.get("interface"):
        os.environ["JAMES_INTERFACE"] = settings["interface"]


# ── wizard dialog ────────────────────────────────────────────────

class SetupWizard(QDialog):
    """Multi-step onboarding wizard for first launch."""

    def __init__(self, parent=None, wifi_interfaces: list = None):
        super().__init__(parent)
        self.wifi_interfaces = wifi_interfaces or []
        self._settings = load_settings()

        self.setWindowTitle("JAMES — First Launch Setup")
        self.setFixedSize(560, 440)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #080c14;
                border: 1px solid #1a3050;
                border-radius: 12px;
            }
            QLabel {
                color: #c8d6e5;
                background: transparent;
            }
            QLineEdit {
                background-color: #0b1120;
                color: #00ff88;
                border: 1px solid #1a3050;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'JetBrains Mono', monospace;
            }
            QLineEdit:focus { border-color: #00f0ff60; }
            QPushButton {
                background-color: #101a2c;
                color: #00f0ff;
                border: 1px solid #1a3050;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #142540; border-color: #00f0ff80; }
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff20, stop:1 #00ff8820);
                border: 1px solid #00f0ff50;
                color: #00f0ff;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff35, stop:1 #00ff8835);
                border-color: #00f0ff;
            }
            QComboBox {
                background-color: #101a2c;
                color: #c8d6e5;
                border: 1px solid #1a3050;
                border-radius: 6px;
                padding: 7px 10px;
            }
            QComboBox:hover { border-color: #00f0ff60; }
            QComboBox QAbstractItemView {
                background-color: #0b1120;
                color: #c8d6e5;
                selection-background-color: #00f0ff22;
                selection-color: #00f0ff;
                border: 1px solid #1a3050;
            }
            QCheckBox { color: #6a8aaa; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #1a3050; border-radius: 4px;
                background: #0b1120;
            }
            QCheckBox::indicator:checked {
                background: #00f0ff30; border-color: #00f0ff;
            }
        """)

        self._build_ui()
        self._go_to_page(0)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── header ───────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(72)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0b1120, stop:1 #0d1830);
                border-bottom: 1px solid #1a2940;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)

        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 32px; color: #00f0ff; background: transparent;")
        h_lay.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title = QLabel("JAMES Setup")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f0ff; letter-spacing: 2px;")
        subtitle = QLabel("Configure your pentesting environment")
        subtitle.setStyleSheet("color: #3a5a7a; font-size: 11px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        h_lay.addLayout(title_col)
        h_lay.addStretch()

        # Step indicators
        self.step_labels: list[QLabel] = []
        for i in range(3):
            dot = QLabel(f"{'●' if i == 0 else '○'}")
            dot.setStyleSheet("color: #2a4a5a; font-size: 16px; background: transparent;")
            self.step_labels.append(dot)
            h_lay.addWidget(dot)

        outer.addWidget(header)

        # ── pages ────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.addWidget(self._make_page_api())
        self.stack.addWidget(self._make_page_wordlist())
        self.stack.addWidget(self._make_page_interface())
        outer.addWidget(self.stack, 1)

        # ── footer ───────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background: #0b1120; border-top: 1px solid #141e30;")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 0, 24, 0)

        skip_btn = QPushButton("Skip All")
        skip_btn.setStyleSheet("color: #3a5a7a; border-color: #141e30;")
        skip_btn.clicked.connect(self._skip_all)
        f_lay.addWidget(skip_btn)
        f_lay.addStretch()

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setVisible(False)
        f_lay.addWidget(self.back_btn)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("primaryBtn")
        self.next_btn.clicked.connect(self._go_next)
        f_lay.addWidget(self.next_btn)

        outer.addWidget(footer)

    # ── pages ────────────────────────────────────────────────────

    def _make_page_api(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 24, 32, 16)
        lay.setSpacing(12)

        title = QLabel("Gemini AI Key (Optional)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f0ff;")
        lay.addWidget(title)

        desc = QLabel(
            "JAMES uses Google Gemini for natural language understanding.\n"
            "Without a key, rule-based command matching is used (still powerful).\n\n"
            "Get a free key at: aistudio.google.com/app/apikey"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6a8aaa; font-size: 12px; line-height: 1.6;")
        lay.addWidget(desc)

        lay.addSpacing(8)

        key_label = QLabel("API Key:")
        key_label.setStyleSheet("color: #8899aa; font-size: 12px;")
        lay.addWidget(key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("AIza… (leave blank to skip)")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        existing = self._settings.get("gemini_api_key", "")
        if existing:
            self.api_key_input.setText(existing)
        lay.addWidget(self.api_key_input)

        self.show_key_cb = QCheckBox("Show key")
        self.show_key_cb.toggled.connect(
            lambda c: self.api_key_input.setEchoMode(
                QLineEdit.Normal if c else QLineEdit.Password
            )
        )
        lay.addWidget(self.show_key_cb)

        lay.addStretch()
        return w

    def _make_page_wordlist(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 24, 32, 16)
        lay.setSpacing(12)

        title = QLabel("Default Wordlist")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f0ff;")
        lay.addWidget(title)

        desc = QLabel(
            "The wordlist used for WPA cracking and brute-force attacks.\n"
            "rockyou.txt is a good default if you have it installed.\n"
            "Common paths: /usr/share/wordlists/rockyou.txt"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6a8aaa; font-size: 12px; line-height: 1.6;")
        lay.addWidget(desc)

        lay.addSpacing(8)

        wl_label = QLabel("Wordlist Path:")
        wl_label.setStyleSheet("color: #8899aa; font-size: 12px;")
        lay.addWidget(wl_label)

        row = QHBoxLayout()
        self.wordlist_input = QLineEdit()
        default_wl = self._settings.get("wordlist", "/home/malcolm/Desktop/rockyou.txt")
        # Check common paths
        for path in ["/usr/share/wordlists/rockyou.txt", "/home/malcolm/Desktop/rockyou.txt"]:
            if os.path.exists(path):
                default_wl = path
                break
        self.wordlist_input.setText(default_wl)
        self.wordlist_input.setPlaceholderText("/path/to/wordlist.txt")
        row.addWidget(self.wordlist_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_wordlist)
        row.addWidget(browse_btn)
        lay.addLayout(row)

        lay.addStretch()
        return w

    def _make_page_interface(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 24, 32, 16)
        lay.setSpacing(12)

        title = QLabel("Default Wi-Fi Interface")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f0ff;")
        lay.addWidget(title)

        desc = QLabel(
            "Choose your primary wireless adapter for Wi-Fi auditing.\n"
            "You can always change this later via: set interface <name>"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6a8aaa; font-size: 12px; line-height: 1.6;")
        lay.addWidget(desc)

        lay.addSpacing(8)

        iface_label = QLabel("Interface:")
        iface_label.setStyleSheet("color: #8899aa; font-size: 12px;")
        lay.addWidget(iface_label)

        self.iface_combo = QComboBox()
        self.iface_combo.addItem("(none / detect automatically)")
        for iface in self.wifi_interfaces:
            name = iface.get("interface", str(iface))
            mode = iface.get("mode", "")
            self.iface_combo.addItem(f"{name}  [{mode}]", userData=name)
        saved = self._settings.get("interface", "")
        if saved:
            for i in range(self.iface_combo.count()):
                if self.iface_combo.itemData(i) == saved:
                    self.iface_combo.setCurrentIndex(i)
                    break
        lay.addWidget(self.iface_combo)

        lay.addSpacing(16)

        summary_lbl = QLabel(
            "✅  You're all set! Click Finish to save and launch JAMES."
        )
        summary_lbl.setStyleSheet("color: #00ff88; font-size: 12px; font-style: italic;")
        summary_lbl.setWordWrap(True)
        lay.addWidget(summary_lbl)

        lay.addStretch()
        return w

    # ── navigation ───────────────────────────────────────────────

    def _go_to_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, dot in enumerate(self.step_labels):
            dot.setText("●" if i == idx else ("✓" if i < idx else "○"))
            dot.setStyleSheet(
                f"color: {'#00f0ff' if i == idx else ('#00ff88' if i < idx else '#2a4a5a')}; "
                "font-size: 16px; background: transparent;"
            )
        self.back_btn.setVisible(idx > 0)
        is_last = idx == self.stack.count() - 1
        self.next_btn.setText("Finish ✓" if is_last else "Next →")

    def _go_next(self):
        current = self.stack.currentIndex()
        if current == self.stack.count() - 1:
            self._save_and_close()
        else:
            self._go_to_page(current + 1)

    def _go_back(self):
        current = self.stack.currentIndex()
        if current > 0:
            self._go_to_page(current - 1)

    def _skip_all(self):
        settings = load_settings()
        settings["wizard_skipped"] = True
        save_settings(settings)
        self.reject()

    # ── actions ─────────────────────────────────────────────────

    def _browse_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Wordlist", "/home/malcolm", "*")
        if path:
            self.wordlist_input.setText(path)

    def _save_and_close(self):
        settings = load_settings()

        api_key = self.api_key_input.text().strip()
        if api_key:
            settings["gemini_api_key"] = api_key

        wordlist = self.wordlist_input.text().strip()
        if wordlist:
            settings["wordlist"] = wordlist

        iface_data = self.iface_combo.currentData()
        if iface_data:
            settings["interface"] = iface_data

        settings["wizard_skipped"] = False
        settings["setup_complete"] = True
        save_settings(settings)
        apply_settings_to_env(settings)
        self.accept()
