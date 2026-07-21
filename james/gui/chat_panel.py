"""
JAMES — Agent Chat Panel (Design System v3)

A conversational interface that sends plain-English commands to the
orchestrator and renders structured responses as styled chat bubbles.

Layout
──────
  ┌─────────────────────────────────────────┐
  │  History                                │
  │  (scrollable bubble view)               │
  ├─────────────────────────────────────────┤
  │  Suggestion chips (quick actions)       │
  ├─────────────────────────────────────────┤
  │  [input field]          [Send]          │
  └─────────────────────────────────────────┘
"""

import json
import logging
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QSizePolicy,
    QPlainTextEdit,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QKeyEvent

logger = logging.getLogger(__name__)

# ── Quick-action chip definitions ──────────────────────────────────────────
CHIPS = [
    ("Scan APs", "scan aps"),
    ("Show Loot", "show loot"),
    ("Status", "status"),
    ("Wi-Fi Blitz", "wifi blitz"),
    ("List Skills", "list skills"),
    ("Network Recon", "network dominate"),
    ("Kill JAMES", "kill james"),
]


# ── Worker ─────────────────────────────────────────────────────────────────


class AgentWorker(QThread):
    """Run orchestrator.handle_command in a background thread."""

    result_signal = pyqtSignal(str)  # agent reply text
    error_signal = pyqtSignal(str)  # error description

    def __init__(self, orchestrator, command: str):
        super().__init__()
        self.orchestrator = orchestrator
        self.command = command

    def run(self):
        try:
            # Try the agent first; fall back to raw orchestrator text
            if hasattr(self.orchestrator, "agent") and self.orchestrator.agent:
                result = self.orchestrator.agent.process(self.command)
                # agent.process returns a string directly
                if isinstance(result, str):
                    self.result_signal.emit(result)
                    return
                result = {"output": str(result)}
            elif hasattr(self.orchestrator, "handle_command"):
                result = self.orchestrator.handle_command(self.command)
            else:
                result = {
                    "output": f"[JAMES] Received: {self.command!r}\n"
                    "(Agent brain not loaded — orchestrator.handle_command not found)"
                }
            # Normalise to a plain string
            if isinstance(result, dict):
                text = (
                    result.get("output")
                    or result.get("message")
                    or json.dumps(result, indent=2)
                )
            else:
                text = str(result)
            self.result_signal.emit(text)
        except Exception as exc:
            self.error_signal.emit(str(exc))


# ── Bubble widget ──────────────────────────────────────────────────────────


class _Bubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._build(text)

    def _build(self, text: str):
        self.setFrameShape(QFrame.NoFrame)

        # Add fade-in animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade_anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_anim.setDuration(250)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)

        inner = QFrame()
        inner.setFrameShape(QFrame.NoFrame)
        inner.setMaximumWidth(680)

        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(4)

        # Header row (sender + copy button)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        ts = datetime.now().strftime("%H:%M")
        sender = "You" if self._is_user else "JAMES"
        sender_lbl = QLabel(f"{sender}  ·  {ts}")
        sender_lbl.setStyleSheet(
            f"color: {'#0078D4' if self._is_user else '#6E7681'};"
            f" font-size: 12px; font-weight: 700; letter-spacing: 0.5px;"
        )
        header_layout.addWidget(sender_lbl)
        header_layout.addStretch()

        # Tiny copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setToolTip("Copy message text to clipboard")
        copy_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent; color: #6E7681;"
            "  border: none; font-size: 11px; font-weight: 600; padding: 2px 6px;"
            "  min-height: 0px;"
            "}"
            "QPushButton:hover {"
            "  color: #4daafc;"
            "}"
        )
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(text, copy_btn))
        header_layout.addWidget(copy_btn)

        v.addLayout(header_layout)

        # Message content
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        if self._is_user:
            # User bubble - deep navy/slate blue tint
            inner.setStyleSheet(
                "background: #16233b; border: 1px solid #0078D4;"
                " border-radius: 10px 10px 2px 10px;"
            )
            body.setStyleSheet(
                "color: #e6f2ff; font-size: 14px;"
                " font-family: 'JetBrains Mono', monospace;"
            )
        else:
            # JAMES bubble - deep dark forest green tint
            inner.setStyleSheet(
                "background: #17261d; border: 1px solid #2EA043;"
                " border-radius: 10px 10px 10px 2px;"
            )
            body.setStyleSheet(
                "color: #CCCCCC; font-size: 14px; line-height: 1.4;"
                " font-family: 'JetBrains Mono', monospace;"
            )

        v.addWidget(body)
        inner.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        if self._is_user:
            outer.addStretch()
            outer.addWidget(inner)
        else:
            outer.addWidget(inner)
            outer.addStretch()

    def _copy_to_clipboard(self, text: str, button: QPushButton):
        from PyQt5.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        button.setText("Copied!")
        button.setStyleSheet(
            "QPushButton {"
            "  background: transparent; color: #2EA043;"
            "  border: none; font-size: 11px; font-weight: 600; padding: 2px 6px;"
            "  min-height: 0px;"
            "}"
        )
        QTimer.singleShot(2000, lambda: self._reset_copy_button(button))

    def _reset_copy_button(self, button: QPushButton):
        try:
            button.setText("Copy")
            button.setStyleSheet(
                "QPushButton {"
                "  background: transparent; color: #6E7681;"
                "  border: none; font-size: 11px; font-weight: 600; padding: 2px 6px;"
                "  min-height: 0px;"
                "}"
                "QPushButton:hover {"
                "  color: #4daafc;"
                "}"
            )
        except Exception:
            pass


# ── Loot banner ────────────────────────────────────────────────────────────


class _LootBanner(QFrame):
    """Highlighted block shown when cracked keys are in loot."""

    def __init__(self, loot_entries: list[dict], parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: #0A1800; border: 1px solid #2EA04340;"
            " border-left: 3px solid #2EA043; border-radius: 8px;"
        )
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        header = QLabel("🔑  LOOT — Cracked Keys")
        header.setStyleSheet(
            "color: #2EA043; font-size: 13px; font-weight: 700; letter-spacing: 0.8px;"
        )
        v.addWidget(header)

        for entry in loot_entries[:20]:  # cap at 20
            essid = entry.get("essid", entry.get("id", "?"))
            key = entry.get("key", "?")
            when = entry.get("when", "")[:10]
            row = QLabel(f"  {essid}  →  {key}  [{when}]")
            row.setStyleSheet(
                "color: #CCCCCC; font-size: 14px;"
                " font-family: 'JetBrains Mono', monospace;"
            )
            row.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.addWidget(row)


# ── Typing indicator ───────────────────────────────────────────────────────


class _TypingIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame = 0
        self.setStyleSheet(
            "color: #6E7681; font-size: 14px; padding: 4px 8px;"
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._frame = 0
        self._timer.start(400)
        self._tick()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        dots = "●" * (self._frame % 3 + 1) + "○" * (2 - self._frame % 3)
        self.setText(f"  JAMES is thinking  {dots}")
        self._frame += 1


# ── Main chat panel ────────────────────────────────────────────────────────


class ChatPanel(QWidget):
    """
    The primary conversational interface widget.

    Usage:
        panel = ChatPanel(orchestrator, main_window)
        tabs.addTab(panel, "Agent")
    """

    # Emitted with each line of output so the main log can mirror it
    on_output = pyqtSignal(str)

    def __init__(self, orchestrator, main_window):
        super().__init__()
        self.orchestrator = orchestrator
        self.main_window = main_window
        self._worker: Optional[AgentWorker] = None
        self._history: list[str] = []
        self._history_idx = -1
        self._bubble_count = 0
        self._scroll_anim = None

        self._build_ui()
        self._connect_signals()
        QTimer.singleShot(300, self._show_welcome)

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scroll area for bubbles ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: #1F1F1F;")

        self._bubble_container = QWidget()
        self._bubble_container.setStyleSheet("background: #1F1F1F;")
        self._bubble_layout = QVBoxLayout(self._bubble_container)
        self._bubble_layout.setContentsMargins(16, 16, 16, 8)
        self._bubble_layout.setSpacing(8)
        self._bubble_layout.addStretch()

        self._typing = _TypingIndicator()
        self._typing.hide()
        self._bubble_layout.addWidget(self._typing)

        self._scroll.setWidget(self._bubble_container)
        root.addWidget(self._scroll, stretch=1)

        # ── Suggestion chips ──
        chips_bar = QWidget()
        chips_bar.setFixedHeight(40)
        chips_bar.setStyleSheet(
            "background: #181818; border-top: 1px solid #2B2B2B;"
        )
        chips_layout = QHBoxLayout(chips_bar)
        chips_layout.setContentsMargins(16, 4, 16, 4)
        chips_layout.setSpacing(6)

        chips_lbl = QLabel("Quick:")
        chips_lbl.setObjectName("metaLabel")
        chips_lbl.setFixedWidth(36)
        chips_layout.addWidget(chips_lbl)

        for label, cmd in CHIPS:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #1e1e1e; color: #94A3B8;"
                "  border: 1px solid #2B2B2B; border-radius: 13px;"
                "  padding: 0 12px; font-size: 12px; font-weight: 600;"
                "}"
                "QPushButton:hover {"
                "  background: #2B2B2B; color: #4daafc;"
                "  border-color: #4daafc33;"
                "}"
            )
            btn.clicked.connect(lambda checked, c=cmd: self._send(c))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()

        # Loot counter chip
        self._loot_chip = QPushButton("Loot: 0")
        self._loot_chip.setFixedHeight(26)
        self._loot_chip.setObjectName("successBtn")
        self._loot_chip.setStyleSheet(
            "QPushButton {"
            "  background: #001A08; color: #2EA043;"
            "  border: 1px solid #2EA04340; border-radius: 12px;"
            "  padding: 0 10px; font-size: 13px; font-weight: 700;"
            "}"
            "QPushButton:hover { background: #002010; border-color: #2EA04380; }"
        )
        self._loot_chip.clicked.connect(lambda: self._send("show loot"))
        chips_layout.addWidget(self._loot_chip)
        root.addWidget(chips_bar)

        # ── Input row ──
        input_bar = QWidget()
        input_bar.setFixedHeight(52)
        input_bar.setStyleSheet(
            "background: #181818; border-top: 1px solid #2B2B2B;"
        )
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 8, 16, 8)
        input_layout.setSpacing(8)

        self._input = _HistoryLineEdit(self._history)
        self._input.setPlaceholderText(
            "Talk to JAMES…  (e.g. wifi blitz wlan0)"
        )
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background: #202020; color: #CCCCCC;"
            "  border: 1px solid #2B2B2B; border-radius: 6px;"
            "  padding: 8px 12px; font-size: 14px;"
            "  font-family: 'JetBrains Mono', monospace;"
            "}"
            "QLineEdit:focus {"
            "  border: 1px solid #4daafc;"
            "  background-color: #1A2333;"
            "}"
        )

        self._btn_send = QPushButton("Send")
        self._btn_send.setObjectName("primaryBtn")
        self._btn_send.setFixedWidth(84)
        self._btn_send.setFixedHeight(36)
        self._btn_send.setToolTip("Send command to JAMES (Ctrl+Return)")
        self._btn_send.setShortcut("Ctrl+Return")

        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setFixedWidth(64)
        self._btn_clear.setFixedHeight(36)
        self._btn_clear.setToolTip("Clear chat history (Ctrl+L)")

        input_layout.addWidget(self._input, stretch=1)
        input_layout.addWidget(self._btn_send)
        input_layout.addWidget(self._btn_clear)
        root.addWidget(input_bar)

    def _connect_signals(self):
        self._btn_send.clicked.connect(lambda: self._send(self._input.text()))
        self._input.returnPressed.connect(
            lambda: self._send(self._input.text())
        )
        # Also bind Ctrl+Enter for the input
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self._input)
        shortcut.setContext(Qt.WidgetShortcut)
        shortcut.activated.connect(lambda: self._send(self._input.text()))

        self._btn_clear.clicked.connect(self._clear_chat)

        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        clear_shortcut.activated.connect(self._clear_chat)

    # ── Actions ────────────────────────────────────────────────────

    def _send(self, text: str):
        text = text.strip()
        if not text:
            return
        if self._worker and self._worker.isRunning():
            self._add_bubble(
                "Please wait — JAMES is still thinking…", is_user=False
            )
            return

        self._input.clear()

        # History
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._history_idx = len(self._history)

        # Add user bubble
        self._add_bubble(text, is_user=True)
        self._typing.start()
        self._btn_send.setEnabled(False)

        # Notify main log
        self.on_output.emit(f"[Agent] {text}")

        # Kick off background worker
        self._worker = AgentWorker(self.orchestrator, text)
        self._worker.result_signal.connect(self._on_result)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    @pyqtSlot(str)
    def _on_result(self, text: str):
        self._typing.stop()
        self._btn_send.setEnabled(True)

        # Check for loot response
        if "show loot" in text.lower() or "cracked_keys" in text.lower():
            self._refresh_loot_display()
        else:
            self._add_bubble(text, is_user=False)
            self.on_output.emit(f"[JAMES] {text[:120]}")

        # Refresh loot chip counter
        self._refresh_loot_chip()

    @pyqtSlot(str)
    def _on_error(self, error: str):
        self._typing.stop()
        self._btn_send.setEnabled(True)
        self._add_bubble(f"⚠ Error: {error}", is_user=False)

    def _clear_chat(self):
        # Remove all bubbles except the stretch at index 0
        while self._bubble_layout.count() > 1:
            item = self._bubble_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._bubble_count = 0
        self._show_welcome()

    # ── Bubble helpers ─────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool):
        bubble = _Bubble(text, is_user)
        # Insert before typing indicator (last item)
        insert_at = max(0, self._bubble_layout.count() - 1)
        self._bubble_layout.insertWidget(insert_at, bubble)
        self._bubble_count += 1
        # Limit history to 200 bubbles
        if self._bubble_count > 200:
            # Remove the first real bubble (index 1 because index 0 is stretch)
            item = self._bubble_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
            self._bubble_count -= 1
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Smoothly animate the scrollbar to the bottom of the chat panel."""
        sb = self._scroll.verticalScrollBar()
        self._scroll_anim = QPropertyAnimation(sb, b"value", self)
        self._scroll_anim.setDuration(250)
        self._scroll_anim.setStartValue(sb.value())
        self._scroll_anim.setEndValue(sb.maximum())
        self._scroll_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._scroll_anim.start()

    def _show_welcome(self):
        self._add_bubble(
            "JAMES is online.\n\n"
            "I'm your autonomous pentesting agent — type a command or click a chip above.\n\n"
            "Examples:\n"
            "  • wifi blitz wlan0\n"
            "  • scan 192.168.1.0/24\n"
            "  • show loot\n"
            "  • status\n"
            "  • list skills",
            is_user=False,
        )
        self._refresh_loot_chip()

    def _refresh_loot_chip(self):
        try:
            summary = self.orchestrator.get_loot_summary()
            n = summary.get("cracked_count", 0)
            self._loot_chip.setText(f"Loot: {n}")
        except Exception:
            pass

    def _refresh_loot_display(self):
        try:
            summary = self.orchestrator.get_loot_summary()
            keys = summary.get("keys", [])
            if keys:
                banner = _LootBanner(keys)
                insert_at = max(0, self._bubble_layout.count() - 1)
                self._bubble_layout.insertWidget(insert_at, banner)
                self._bubble_count += 1
            else:
                self._add_bubble("No cracked keys in loot yet.", is_user=False)
        except Exception as exc:
            self._add_bubble(f"Loot read error: {exc}", is_user=False)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def showEvent(self, event):
        """Set focus to the input field when the chat panel is shown."""
        super().showEvent(event)
        self._input.setFocus()


# ── History-aware line edit ────────────────────────────────────────────────


class _HistoryLineEdit(QLineEdit):
    """QLineEdit with ↑/↓ command history navigation."""

    def __init__(self, history: list[str], parent=None):
        super().__init__(parent)
        self._history = history
        self._idx = -1

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.clear()
            self.clearFocus()
        elif event.key() == Qt.Key_Up:
            if self._history:
                self._idx = max(
                    0,
                    (
                        (self._idx - 1)
                        if self._idx > 0
                        else len(self._history) - 1
                    ),
                )
                self.setText(self._history[self._idx])
                self.setCursorPosition(len(self.text()))
        elif event.key() == Qt.Key_Down:
            if self._history:
                if self._idx < len(self._history) - 1:
                    self._idx += 1
                    self.setText(self._history[self._idx])
                    self.setCursorPosition(len(self.text()))
                else:
                    self._idx = len(self._history)
                    self.setText("")
        else:
            self._idx = len(self._history)
            super().keyPressEvent(event)
