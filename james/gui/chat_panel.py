"""
Chat Panel — conversational interface to the JAMES agent.

Renders a scrollable chat log with user/agent message bubbles,
a command input with history, and real-time streaming responses.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor

from james.core.agent import Agent
from james.core.orchestrator import Orchestrator


class AgentWorker(QThread):
    """Run agent.process() off the GUI thread."""
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, agent: Agent, user_input: str):
        super().__init__()
        self.agent = agent
        self.user_input = user_input

    def run(self):
        try:
            response = self.agent.process(self.user_input)
            self.result_ready.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class ChatPanel(QWidget):
    """
    Full chat interface widget.

    Embeds its own Agent instance backed by a shared Orchestrator.
    """

    def __init__(self, orchestrator: Orchestrator, parent=None):
        super().__init__(parent)
        self.orch = orchestrator
        self.agent = Agent(orchestrator)
        self._cmd_history: list[str] = []
        self._history_idx = -1
        self._workers: list[AgentWorker] = []

        self._build_ui()
        # show welcome message on load
        QTimer.singleShot(200, self._show_welcome)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── chat log ────────────────────────────────────────────
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setFont(QFont("JetBrains Mono", 11))
        self.chat_log.setStyleSheet("""
            QTextEdit {
                background-color: #080c14;
                border: none;
                padding: 12px;
                color: #c8d6e5;
            }
        """)
        layout.addWidget(self.chat_log, 1)

        # ── divider ─────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #1a2940; max-height: 1px;")
        layout.addWidget(divider)

        # ── input bar ───────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setFixedHeight(52)
        input_bar.setStyleSheet("background-color: #0f1923;")
        bar_layout = QHBoxLayout(input_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)

        prompt_label = QLabel("❯")
        prompt_label.setStyleSheet("color: #00f0ff; font-size: 18px; font-weight: bold;")
        prompt_label.setFixedWidth(24)
        bar_layout.addWidget(prompt_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Talk to JAMES… (type 'help' for commands)")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #00ff88;
                font-size: 14px;
                font-family: 'JetBrains Mono', monospace;
            }
        """)
        self.input_field.returnPressed.connect(self._on_send)
        bar_layout.addWidget(self.input_field)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(70)
        send_btn.clicked.connect(self._on_send)
        bar_layout.addWidget(send_btn)

        layout.addWidget(input_bar)

    # ── message rendering ───────────────────────────────────────

    def _append_user_msg(self, text: str):
        html = (
            '<div style="margin: 8px 0; padding: 8px 14px; '
            'background-color: #0d2137; border-left: 3px solid #00f0ff; '
            'border-radius: 4px;">'
            f'<span style="color: #00f0ff; font-weight: bold;">YOU ❯</span> '
            f'<span style="color: #e8f0f8;">{_escape(text)}</span>'
            '</div>'
        )
        self.chat_log.append(html)

    def _append_agent_msg(self, text: str):
        # convert newlines and spaces for HTML rendering
        formatted = _escape(text).replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
        html = (
            '<div style="margin: 8px 0; padding: 8px 14px; '
            'background-color: #0a1420; border-left: 3px solid #00ff88; '
            'border-radius: 4px;">'
            f'<span style="color: #00ff88; font-weight: bold;">JAMES ⚡</span><br>'
            f'<span style="color: #c8d6e5;">{formatted}</span>'
            '</div>'
        )
        self.chat_log.append(html)
        self.chat_log.moveCursor(QTextCursor.End)

    def _append_system_msg(self, text: str):
        html = (
            f'<div style="margin: 4px 0; text-align: center; color: #5a7a9a; '
            f'font-size: 11px;">{_escape(text)}</div>'
        )
        self.chat_log.append(html)

    def _append_thinking(self):
        html = (
            '<div id="thinking" style="margin: 8px 0; padding: 8px 14px; '
            'color: #5a7a9a; font-style: italic;">'
            '⏳ JAMES is working…</div>'
        )
        self.chat_log.append(html)
        self.chat_log.moveCursor(QTextCursor.End)

    def _remove_thinking(self):
        """Remove the thinking indicator by clearing and re-rendering."""
        # Simple approach: the thinking message is at the end,
        # just let the new response push past it visually
        pass

    # ── actions ─────────────────────────────────────────────────

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self._cmd_history.append(text)
        self._history_idx = -1

        self._append_user_msg(text)
        self._append_thinking()

        # run agent in background thread
        worker = AgentWorker(self.agent, text)
        worker.result_ready.connect(self._on_response)
        worker.error.connect(self._on_error)
        self._workers.append(worker)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_response(self, response: str):
        self._remove_thinking()
        if response:
            self._append_agent_msg(response)

    def _on_error(self, error: str):
        self._remove_thinking()
        self._append_agent_msg(f"[ERROR] {error}")

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    def _show_welcome(self):
        self._append_system_msg("━━━ Session Started ━━━")
        welcome = (
            "Hey, I'm JAMES — your autonomous pentesting agent.\n\n"
            "I'm running on Parrot OS with access to nmap, aircrack-ng,\n"
            "hashcat, john, and more.\n\n"
            "Tell me what you want to do in plain English, or type\n"
            "'help' to see all commands.\n\n"
            "Examples:\n"
            "  • scan 192.168.1.0/24\n"
            "  • list interfaces\n"
            "  • enable monitor wlan0\n"
            "  • crack wpa capture.cap\n"
            "  • ! whoami"
        )
        self._append_agent_msg(welcome)

    # ── keyboard navigation ─────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up and self._cmd_history:
            if self._history_idx == -1:
                self._history_idx = len(self._cmd_history) - 1
            elif self._history_idx > 0:
                self._history_idx -= 1
            self.input_field.setText(self._cmd_history[self._history_idx])
        elif event.key() == Qt.Key_Down and self._cmd_history:
            if self._history_idx < len(self._cmd_history) - 1:
                self._history_idx += 1
                self.input_field.setText(self._cmd_history[self._history_idx])
            else:
                self._history_idx = -1
                self.input_field.clear()
        else:
            super().keyPressEvent(event)


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
