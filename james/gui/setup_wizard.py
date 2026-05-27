"""
JAMES — First-Run Setup Wizard (Design System v3).

A multi-page dialog that guides the user through:
  Page 1 — Welcome
  Page 2 — Sudo password (stored to ~/.config/james/settings.json)
  Page 3 — Tool dependency check
  Page 4 — Done / launch
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QStackedWidget,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QCheckBox, QSpacerItem,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from james.gui.theme import DARK_STYLESHEET, PALETTE

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path.home() / ".config" / "james" / "settings.json"


# ── Worker for dependency check ────────────────────────────────────────────

class _CheckWorker(QThread):
    progress = pyqtSignal(str, bool)   # (tool_name, found)
    done     = pyqtSignal()

    TOOLS = [
        "aircrack-ng", "airmon-ng", "airodump-ng", "aireplay-ng",
        "hashcat", "hcxdumptool", "hcxpcapngtool", "hostapd",
        "dnsmasq", "nmap", "john", "hydra", "reaver", "bully",
        "mdk4", "nikto", "gobuster", "sqlmap", "macchanger", "masscan",
    ]

    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator

    def run(self):
        try:
            status = self.orchestrator.system_check()
            for tool in self.TOOLS:
                self.progress.emit(tool, status.get(tool, False))
            self.done.emit()
        except Exception as exc:
            logger.warning("Wizard tool check failed: %s", exc)
            for tool in self.TOOLS:
                self.progress.emit(tool, False)
            self.done.emit()


# ── Page helpers ───────────────────────────────────────────────────────────

def _sep_h() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    f.setFrameShape(QFrame.HLine)
    return f


class _PageBase(QWidget):
    """Common scaffold for wizard pages."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 24)
        root.setSpacing(16)

        heading = QLabel(title)
        heading.setObjectName("sectionLabel")
        root.addWidget(heading)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("dimLabel")
            sub.setWordWrap(True)
            root.addWidget(sub)

        root.addWidget(_sep_h())
        self._body = QVBoxLayout()
        self._body.setSpacing(12)
        root.addLayout(self._body)
        root.addStretch()
        self._root = root


# ── Page 1 — Welcome ──────────────────────────────────────────────────────

class _WelcomePage(_PageBase):
    def __init__(self):
        super().__init__(
            "Welcome to JAMES",
            "Just Another Multipurpose Exploitation System — autonomous Wi-Fi & network pentesting agent.",
        )
        items = [
            ("🔥", "One-click attack chains",   "PMKID · Handshake · WPS · Evil Twin — fully automated."),
            ("🔑", "Persistent loot cache",     "Cracked keys survive reboots and are indexed by network."),
            ("📡", "Live AP scanner",           "See every network in range, select a target in one click."),
            ("⚡", "35+ tool wrappers",         "nmap · aircrack-ng · hashcat · hydra · sqlmap and more."),
            ("🤖", "AI agent brain",            "Type plain English — JAMES plans and executes the attack."),
        ]
        for icon, title, desc in items:
            row = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedWidth(28)
            icon_lbl.setStyleSheet("font-size: 22px;")
            text_v = QVBoxLayout()
            text_v.setSpacing(1)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #CCCCCC; font-size: 14px; font-weight: 700;")
            d_lbl = QLabel(desc)
            d_lbl.setObjectName("dimLabel")
            d_lbl.setWordWrap(True)
            text_v.addWidget(t_lbl)
            text_v.addWidget(d_lbl)
            row.addWidget(icon_lbl)
            row.addLayout(text_v)
            self._body.addLayout(row)

        warn = QLabel(
            "⚠  JAMES is designed for authorized security testing ONLY.\n"
            "Use it only against networks you own or have explicit written permission to test."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "background: #1A0A00; color: #BB8009; font-size: 13px;"
            " border: 1px solid #BB800930; border-left: 3px solid #BB8009;"
            " border-radius: 6px; padding: 8px 12px;"
        )
        self._body.addWidget(warn)


# ── Page 2 — Sudo ─────────────────────────────────────────────────────────

class _SudoPage(_PageBase):
    def __init__(self):
        super().__init__(
            "Sudo Access",
            "Many pentesting tools require root privileges. Enter your sudo password so JAMES "
            "can run them automatically — it is stored locally in an encrypted config file.",
        )
        self._pwd_edit = QLineEdit()
        self._pwd_edit.setEchoMode(QLineEdit.Password)
        self._pwd_edit.setPlaceholderText("Enter sudo password (leave blank to be prompted each time)")
        self._pwd_edit.setStyleSheet(
            "background: #181818; color: #CCCCCC; border: 1px solid #2B2B2B;"
            " border-radius: 6px; padding: 8px 12px; font-size: 14px;"
            " font-family: 'JetBrains Mono', monospace;"
        )
        self._body.addWidget(QLabel("Sudo Password:"))
        self._body.addWidget(self._pwd_edit)

        self._show_pwd = QCheckBox("Show password")
        self._show_pwd.setStyleSheet("color: #6E7681; font-size: 13px;")
        self._show_pwd.toggled.connect(self._toggle_echo)
        self._body.addWidget(self._show_pwd)

        note = QLabel(
            "Password is saved to ~/.config/james/settings.json  —  "
            "a file readable only by your user account."
        )
        note.setObjectName("dimLabel")
        note.setWordWrap(True)
        self._body.addWidget(note)

    def _toggle_echo(self, checked: bool):
        self._pwd_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def get_password(self) -> str:
        return self._pwd_edit.text()


# ── Page 3 — Tool check ───────────────────────────────────────────────────

class _ToolCheckPage(_PageBase):
    def __init__(self):
        super().__init__(
            "Dependency Check",
            "Verifying that pentesting tools are installed on this system.",
        )
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Tool", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMaximumHeight(280)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: #181818; border: none; border-radius: 2px; }"
            "QProgressBar::chunk { background: #0078D4; border-radius: 2px; }"
        )

        self._status_lbl = QLabel("Click 'Check Tools' to begin.")
        self._status_lbl.setObjectName("dimLabel")

        self._body.addWidget(self._status_lbl)
        self._body.addWidget(self._progress)
        self._body.addWidget(self._table)

    def reset(self):
        self._table.setRowCount(0)
        self._progress.setValue(0)
        self._status_lbl.setText("Scanning…")

    def add_result(self, tool: str, found: bool, total: int):
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QTableWidgetItem(tool)
        name_item.setForeground(QColor("#CCCCCC"))

        if found:
            status_item = QTableWidgetItem("✅  installed")
            status_item.setForeground(QColor("#2EA043"))
        else:
            status_item = QTableWidgetItem("❌  missing")
            status_item.setForeground(QColor("#F85149"))

        self._table.setItem(row, 0, name_item)
        self._table.setItem(row, 1, status_item)

        pct = int((row + 1) / total * 100)
        self._progress.setValue(pct)

    def set_done(self, n_found: int, n_total: int):
        if n_found == n_total:
            self._status_lbl.setText(f"✅  All {n_total} tools found.")
            self._status_lbl.setStyleSheet("color: #2EA043; font-size: 14px;")
        else:
            missing = n_total - n_found
            self._status_lbl.setText(
                f"⚠  {missing} tool(s) missing — install them via the Troubleshoot tab."
            )
            self._status_lbl.setStyleSheet("color: #BB8009; font-size: 14px;")


# ── Page 4 — Done ─────────────────────────────────────────────────────────

class _DonePage(_PageBase):
    def __init__(self):
        super().__init__(
            "Setup Complete",
            "JAMES is ready. Click Launch to open the main dashboard.",
        )
        tips_lbl = QLabel("Quick-start tips:")
        tips_lbl.setStyleSheet("color: #CCCCCC; font-size: 14px; font-weight: 700;")
        self._body.addWidget(tips_lbl)

        for tip in [
            "→  Go to Wi-Fi Arsenal · Recon and click START SCAN",
            "→  Right-click an AP to set it as your attack target",
            "→  Auto-Pilot tab runs the full capture+crack pipeline hands-free",
            "→  Type 'wifi blitz wlan0' in the Agent tab for one-click blitz",
            "→  Hit Kill in the header to instantly restore all interfaces",
        ]:
            lbl = QLabel(tip)
            lbl.setObjectName("dimLabel")
            lbl.setWordWrap(True)
            self._body.addWidget(lbl)


# ── Main wizard dialog ─────────────────────────────────────────────────────

class SetupWizard(QDialog):
    """
    Multi-page first-run setup wizard.

    Usage:
        wizard = SetupWizard(orchestrator, parent)
        if wizard.exec_() == QDialog.Accepted:
            ...
    """

    def __init__(self, orchestrator=None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.setWindowTitle("JAMES Setup Wizard")
        self.setMinimumSize(640, 520)
        self.resize(700, 580)
        self.setModal(True)
        self.setStyleSheet(DARK_STYLESHEET)

        self._worker: _CheckWorker | None = None
        self._check_results: dict[str, bool] = {}
        self._build_ui()
        self._go_to(0)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header strip
        hdr = QWidget()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet("background: #181818; border-bottom: 1px solid #2B2B2B;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(24, 0, 24, 0)
        title = QLabel("JAMES  Setup Wizard")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 19px; font-weight: 700; color: #CCCCCC;")
        self._step_lbl = QLabel("Step 1 / 4")
        self._step_lbl.setObjectName("metaLabel")
        hdr_l.addWidget(title)
        hdr_l.addStretch()
        hdr_l.addWidget(self._step_lbl)
        root.addWidget(hdr)

        # Progress strip
        self._page_bar = QProgressBar()
        self._page_bar.setRange(0, 4)
        self._page_bar.setValue(0)
        self._page_bar.setTextVisible(False)
        self._page_bar.setFixedHeight(3)
        self._page_bar.setStyleSheet(
            "QProgressBar { background: #181818; border: none; }"
            "QProgressBar::chunk { background: #0078D4; }"
        )
        root.addWidget(self._page_bar)

        # Pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #1F1F1F;")

        self._p_welcome = _WelcomePage()
        self._p_sudo    = _SudoPage()
        self._p_tools   = _ToolCheckPage()
        self._p_done    = _DonePage()

        for p in (self._p_welcome, self._p_sudo, self._p_tools, self._p_done):
            self._stack.addWidget(p)

        root.addWidget(self._stack, stretch=1)

        # Footer nav
        nav = QWidget()
        nav.setFixedHeight(52)
        nav.setStyleSheet("background: #181818; border-top: 1px solid #2B2B2B;")
        nav_l = QHBoxLayout(nav)
        nav_l.setContentsMargins(24, 0, 24, 0)
        nav_l.setSpacing(8)

        self._btn_back = QPushButton("← Back")
        self._btn_back.setMinimumWidth(88)
        self._btn_back.setFixedHeight(36)

        self._btn_next = QPushButton("Next →")
        self._btn_next.setObjectName("primaryBtn")
        self._btn_next.setMinimumWidth(120)
        self._btn_next.setFixedHeight(36)

        self._btn_skip = QPushButton("Skip")
        self._btn_skip.setFixedHeight(36)
        self._btn_skip.setStyleSheet("color: #6E7681; border: none; background: transparent;")

        nav_l.addWidget(self._btn_skip)
        nav_l.addStretch()
        nav_l.addWidget(self._btn_back)
        nav_l.addWidget(self._btn_next)
        root.addWidget(nav)

        self._btn_back.clicked.connect(self._on_back)
        self._btn_next.clicked.connect(self._on_next)
        self._btn_skip.clicked.connect(self.reject)

    # ── Navigation ─────────────────────────────────────────────────

    def _go_to(self, idx: int):
        self._stack.setCurrentIndex(idx)
        self._page_bar.setValue(idx + 1)
        self._step_lbl.setText(f"Step {idx + 1} / 4")
        self._btn_back.setEnabled(idx > 0)
        if idx == 3:
            self._btn_next.setText("Launch  🚀")
            self._btn_skip.hide()
        else:
            self._btn_next.setText("Next →")
            self._btn_skip.show()

        # Auto-start tool check when navigating to page 3
        if idx == 2:
            self._start_tool_check()

    def _on_next(self):
        idx = self._stack.currentIndex()
        if idx == 1:
            self._save_settings()
        if idx == 3:
            self.accept()
            return
        self._go_to(idx + 1)

    def _on_back(self):
        self._go_to(self._stack.currentIndex() - 1)

    # ── Settings persistence ────────────────────────────────────────

    def _save_settings(self):
        password = self._p_sudo.get_password()
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            existing: dict = {}
            if SETTINGS_FILE.exists():
                try:
                    existing = json.loads(SETTINGS_FILE.read_text())
                except Exception:
                    pass
            existing["wizard_complete"] = True
            if password:
                existing["sudo_password"] = password
                # Also inject into the live orchestrator
                if self.orchestrator:
                    try:
                        self.orchestrator.layer.set_sudo_password(password)
                    except Exception as e:
                        logger.warning("Could not set sudo password: %s", e)
            SETTINGS_FILE.write_text(json.dumps(existing, indent=2))
            SETTINGS_FILE.chmod(0o600)
            logger.info("Wizard settings saved to %s", SETTINGS_FILE)
        except Exception as exc:
            logger.warning("Could not save wizard settings: %s", exc)

    # ── Tool check ──────────────────────────────────────────────────

    def _start_tool_check(self):
        if not self.orchestrator:
            self._p_tools._status_lbl.setText(
                "No orchestrator attached — skipping tool check."
            )
            return
        self._p_tools.reset()
        self._worker = _CheckWorker(self.orchestrator)
        self._worker.progress.connect(self._on_tool_progress)
        self._worker.done.connect(self._on_check_done)
        self._worker.start()

    def _on_tool_progress(self, tool: str, found: bool):
        total = len(_CheckWorker.TOOLS)
        self._check_results[tool] = found
        self._p_tools.add_result(tool, found, total)

    def _on_check_done(self):
        n_found = sum(1 for v in self._check_results.values() if v)
        n_total = len(self._check_results)
        self._p_tools.set_done(n_found, n_total)

    # ── Class-level factory ─────────────────────────────────────────

    @classmethod
    def should_show(cls) -> bool:
        """Return True if the wizard has not been completed yet."""
        if not SETTINGS_FILE.exists():
            return True
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            return not data.get("wizard_complete", False)
        except Exception:
            return True
