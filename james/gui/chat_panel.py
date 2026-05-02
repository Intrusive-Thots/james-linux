"""
Chat Panel — conversational interface to the JAMES agent.

Renders a scrollable chat log with user/agent message bubbles,
a command input with history, real-time streaming responses,
clickable suggestion chips, and an animated thinking indicator.
"""

import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextBlockFormat

from james.core.agent import Agent
from james.core.orchestrator import Orchestrator


# ── suggestion chip definitions ──────────────────────────────────

_CONTEXT_CHIPS = {
    # After a scan result
    "scan": ["full scan {target}", "run skill vuln_scan", "osint {target}", "network dominate {target}"],
    "recon": ["full scan {target}", "run skill vuln_scan", "os detect {target}", "stealth recon {target}"],
    # After interface list
    "list_interfaces": ["enable monitor {interface}", "run skill wifi_audit", "wifi blitz {interface}"],
    # After monitor on
    "monitor_on": ["run skill handshake_harvest", "wifi blitz {interface}", "scan aps", "run skill wifi_dos"],
    # After web commands
    "web": ["web pwn {target}", "run skill full_web_audit", "nikto {target}"],
    # After wifi attack
    "wifi_hack": ["show loot", "crack wpa", "scan aps"],
    # Default
    "default": ["status", "list skills", "help", "show loot"],
}


class AgentWorker(QThread):
    """Run agent.process() off the GUI thread."""
    result_ready = pyqtSignal(str, str)   # (response, intent)
    error = pyqtSignal(str)

    def __init__(self, agent: Agent, user_input: str):
        super().__init__()
        self.agent = agent
        self.user_input = user_input

    def run(self):
        try:
            response = self.agent.process(self.user_input)
            # Guess intent from input for chip selection
            intent = _guess_intent(self.user_input)
            self.result_ready.emit(response, intent)
        except Exception as e:
            self.error.emit(str(e))


def _guess_intent(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(scan|recon|nmap)\b", t):
        return "scan"
    if re.search(r"\b(interfaces?|wifi|wlan|wireless)\b", t) and not re.search(r"\b(blitz|pwn|dominate)\b", t):
        return "list_interfaces"
    if re.search(r"\bmonitor\b", t):
        return "monitor_on"
    if re.search(r"\b(web|nikto|gobuster|sqlmap|http|url)\b", t):
        return "web"
    if re.search(r"\b(blitz|handshake|deauth|pmkid|wps|capture)\b", t):
        return "wifi_hack"
    return "default"


class SuggestionBar(QWidget):
    """A horizontal row of clickable command suggestion chips."""

    command_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("background: transparent;")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 6, 16, 6)
        self._layout.setSpacing(8)
        self._layout.addStretch()
        self._buttons: list[QPushButton] = []

    def set_chips(self, commands: list[str], context: dict):
        # Clear old chips
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        for cmd_template in commands:
            # Fill in context variables
            cmd = cmd_template
            for k, v in context.items():
                cmd = cmd.replace(f"{{{k}}}", v)
            # Skip if still has unfilled placeholders (no context value)
            if "{" in cmd:
                continue

            btn = QPushButton(f"↗ {cmd}")
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0d1e30;
                    color: #5a9abf;
                    border: 1px solid #1a3050;
                    border-radius: 14px;
                    padding: 2px 14px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #142540;
                    color: #00f0ff;
                    border-color: #00f0ff60;
                }
            """)
            final_cmd = cmd
            btn.clicked.connect(lambda _, c=final_cmd: self.command_selected.emit(c))
            self._layout.insertWidget(self._layout.count() - 1, btn)
            self._buttons.append(btn)

    def clear_chips(self):
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()


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
        self._thinking_cursor_pos: int = -1
        self._dot_count = 0
        self._active_workers = 0

        self._build_ui()

        # Animated dots timer
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(400)
        self._dot_timer.timeout.connect(self._animate_dots)

        # Show welcome message on load
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
                background-color: #060a12;
                border: none;
                padding: 16px;
                color: #c8d6e5;
            }
        """)
        layout.addWidget(self.chat_log, 1)

        # ── suggestion bar ──────────────────────────────────────
        self.suggestion_bar = SuggestionBar()
        self.suggestion_bar.command_selected.connect(self._inject_command)
        layout.addWidget(self.suggestion_bar)

        # ── divider ─────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #141e3000, stop:0.5 #1a2940, stop:1 #141e3000); max-height: 1px;"
        )
        layout.addWidget(divider)

        # ── input bar ───────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setFixedHeight(56)
        input_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d1528, stop:1 #0b1120);
            }
        """)
        bar_layout = QHBoxLayout(input_bar)
        bar_layout.setContentsMargins(16, 8, 16, 8)
        bar_layout.setSpacing(10)

        prompt_label = QLabel("❯")
        prompt_label.setStyleSheet(
            "color: #00f0ff; font-size: 20px; font-weight: bold; background: transparent;"
        )
        prompt_label.setFixedWidth(28)
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

        # History hint
        hist_hint = QLabel("↑↓ history")
        hist_hint.setStyleSheet(
            "color: #1a3050; font-size: 10px; background: transparent; padding-right: 4px;"
        )
        bar_layout.addWidget(hist_hint)

        self.send_btn = QPushButton("Send ⚡")
        self.send_btn.setFixedWidth(90)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff20, stop:1 #00ff8820);
                border: 1px solid #00f0ff50;
                border-radius: 6px;
                color: #00f0ff;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff35, stop:1 #00ff8835);
                border-color: #00f0ff;
            }
            QPushButton:disabled {
                background: #0a0e17;
                color: #2a3a4a;
                border-color: #141e30;
            }
        """)
        self.send_btn.clicked.connect(self._on_send)
        bar_layout.addWidget(self.send_btn)

        layout.addWidget(input_bar)

    # ── message rendering ───────────────────────────────────────

    def _append_user_msg(self, text: str):
        html = (
            '<div style="margin: 10px 0 10px 60px; padding: 12px 16px; '
            'background-color: #0d2137; '
            'border-left: 3px solid #00f0ff; border-radius: 8px;">'
            f'<span style="color: #00f0ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;">YOU ❯</span> '
            f'<span style="color: #e8f0f8;">{_escape(text)}</span>'
            '</div>'
        )
        self.chat_log.append(html)

    def _append_agent_msg(self, text: str):
        formatted = _escape(text).replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
        html = (
            '<div style="margin: 10px 40px 10px 0; padding: 14px 16px; '
            'background-color: #081018; '
            'border-left: 3px solid #00ff88; border-radius: 8px;">'
            f'<span style="color: #00ff88; font-weight: bold; font-size: 11px; letter-spacing: 1px;">JAMES ⚡</span><br>'
            f'<span style="color: #c8d6e5; line-height: 1.7;">{formatted}</span>'
            '</div>'
        )
        self.chat_log.append(html)
        self.chat_log.moveCursor(QTextCursor.End)

    def _append_error_msg(self, text: str):
        formatted = _escape(text).replace('\n', '<br>')
        html = (
            '<div style="margin: 10px 40px 10px 0; padding: 14px 16px; '
            'background-color: #120808; '
            'border-left: 3px solid #ff4757; border-radius: 8px;">'
            f'<span style="color: #ff4757; font-weight: bold; font-size: 11px; letter-spacing: 1px;">ERROR ✕</span><br>'
            f'<span style="color: #e8a0a0; line-height: 1.7;">{formatted}</span>'
            '</div>'
        )
        self.chat_log.append(html)
        self.chat_log.moveCursor(QTextCursor.End)

    def _append_system_msg(self, text: str):
        html = (
            f'<div style="margin: 12px 0; text-align: center; color: #2a4a5a; '
            f'font-size: 11px; letter-spacing: 2px;">{_escape(text)}</div>'
        )
        self.chat_log.append(html)

    def _append_thinking(self):
        """Insert animated thinking indicator and record its block position."""
        self._thinking_cursor_pos = self.chat_log.document().blockCount()
        html = (
            '<div id="thinking" style="margin: 8px 40px 8px 0; padding: 12px 16px; '
            'color: #3a5a7a; font-style: italic; border-left: 3px solid #1a2940; '
            'border-radius: 8px; background-color: #0a0f18;">'
            '⏳ JAMES is thinking<span id="dots">&nbsp;•</span></div>'
        )
        self.chat_log.append(html)
        self.chat_log.moveCursor(QTextCursor.End)
        self._dot_count = 0
        self._dot_timer.start()

    def _remove_thinking(self):
        """Remove the last thinking indicator block from the document."""
        self._dot_timer.stop()
        if self._thinking_cursor_pos < 0:
            return
        doc = self.chat_log.document()
        total_blocks = doc.blockCount()
        # Walk backwards from end to find and remove thinking block(s)
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.End)
        # Select and delete everything from thinking_cursor_pos onward
        # We scan backwards for the thinking div
        full_html = self.chat_log.toHtml()
        if 'id="thinking"' in full_html or "JAMES is thinking" in full_html:
            # Simple strategy: find the block with the thinking text and remove it
            for i in range(total_blocks - 1, -1, -1):
                block = doc.findBlockByNumber(i)
                if "thinking" in block.text().lower() or "is thinking" in block.text():
                    cursor = QTextCursor(block)
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.removeSelectedText()
                    # Also remove the empty line left behind
                    if cursor.atBlockStart() and cursor.block().text() == "":
                        cursor.deleteChar()
                    break
        self._thinking_cursor_pos = -1

    def _animate_dots(self):
        """Cycle the dot count in the thinking indicator."""
        self._dot_count = (self._dot_count + 1) % 4
        # We can't easily animate inside QTextEdit HTML; update the last line text
        doc = self.chat_log.document()
        for i in range(doc.blockCount() - 1, max(doc.blockCount() - 5, -1), -1):
            block = doc.findBlockByNumber(i)
            text = block.text()
            if "is thinking" in text:
                dots = " •" * (self._dot_count + 1)
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.BlockUnderCursor)
                new_html = (
                    '<div style="margin: 8px 40px 8px 0; padding: 12px 16px; '
                    'color: #3a5a7a; font-style: italic; border-left: 3px solid #1a2940; '
                    f'border-radius: 8px; background-color: #0a0f18;">⏳ JAMES is thinking{dots}</div>'
                )
                cursor.insertHtml(new_html)
                break

    # ── actions ─────────────────────────────────────────────────

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("…")
        self._cmd_history.append(text)
        self._history_idx = -1
        self.suggestion_bar.clear_chips()

        self._append_user_msg(text)
        self._append_thinking()
        self._active_workers += 1

        worker = AgentWorker(self.agent, text)
        worker.result_ready.connect(self._on_response)
        worker.error.connect(self._on_error)
        self._workers.append(worker)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_response(self, response: str, intent: str):
        self._remove_thinking()
        if response:
            self._append_agent_msg(response)

        # Show suggestion chips based on intent and current context
        chips = _CONTEXT_CHIPS.get(intent, _CONTEXT_CHIPS["default"])
        self.suggestion_bar.set_chips(chips, self.agent.context)

        self._active_workers -= 1
        self._restore_input()

    def _on_error(self, error: str):
        self._remove_thinking()
        self._append_error_msg(error)
        self._active_workers -= 1
        self._restore_input()

    def _restore_input(self):
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send ⚡")
        self.input_field.setFocus()

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    def _inject_command(self, cmd: str):
        """Inject a suggestion chip command into the input and send it."""
        self.input_field.setText(cmd)
        self._on_send()

    def _show_welcome(self):
        self._append_system_msg("━━━ Session Started ━━━")

        welcome_html = """
<div style="margin: 16px 0; padding: 20px; background: linear-gradient(135deg, #081018, #0a1520);
    border: 1px solid #1a3050; border-radius: 12px;">
  <div style="color: #00ff88; font-weight: bold; font-size: 14px; letter-spacing: 2px; margin-bottom: 8px;">
    ⚡ JAMES v0.4.0 — Autonomous Pentesting Agent
  </div>
  <div style="color: #6a8aaa; font-size: 12px; line-height: 1.8; margin-bottom: 14px;">
    Running on Parrot OS with <span style="color:#00f0ff;">35+ tools</span>,
    <span style="color:#ff6b35;">5 one-click attack chains</span>,
    and <span style="color:#00ff88;">persistent loot caching</span>.<br>
    Tell me what you want to do in plain English.
  </div>
  <div style="color: #4a6a8a; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-bottom: 8px;">
    QUICK START
  </div>
  <table style="width: 100%; border-collapse: collapse;">
    <tr>
      <td style="padding: 4px 8px; color: #00f0ff;">scan 192.168.1.0/24</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ discover hosts &amp; open ports</td>
    </tr>
    <tr>
      <td style="padding: 4px 8px; color: #ff6b35;">wifi blitz wlan0</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ PMKID + Handshake + WPS auto-chain</td>
    </tr>
    <tr>
      <td style="padding: 4px 8px; color: #ff6b35;">web pwn http://target</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ WAF + SQLi + DirBust + Nikto chain</td>
    </tr>
    <tr>
      <td style="padding: 4px 8px; color: #00f0ff;">scan aps wlan0mon</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ list nearby Wi-Fi networks</td>
    </tr>
    <tr>
      <td style="padding: 4px 8px; color: #00ff88;">show loot</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ view all cracked keys</td>
    </tr>
    <tr>
      <td style="padding: 4px 8px; color: #00f0ff;">help</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ full command reference</td>
    </tr>
  </table>
</div>
"""
        self.chat_log.insertHtml(welcome_html)
        self.chat_log.moveCursor(QTextCursor.End)

        # Show default suggestion chips
        self.suggestion_bar.set_chips(
            ["scan 192.168.1.0/24", "list interfaces", "show loot", "list skills", "help"],
            {}
        )

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
