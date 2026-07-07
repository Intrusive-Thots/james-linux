"""
JAMES — Live Activity Sidebar.

Always-visible collapsible panel showing real-time orchestrator activity.
Replaces the full-screen Activity tab — now sits alongside any active tab.

Features:
  - Compact single-line colored entries
  - Collapse to thin icon strip
  - Phase/progress in compact header
  - Filter by type
  - Pause/resume with buffer replay
"""

from datetime import datetime
from collections import deque

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QFrame,
    QComboBox,
    QApplication,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QTextCursor
import logging

logger = logging.getLogger(__name__)

# ── Activity entry types and their colors ────────────────────────────
ACTIVITY_TYPES = {
    "TOOL":     {"icon": "⚡", "color": "#4daafc", "label": "Tool"},
    "PHASE":    {"icon": "🔄", "color": "#BB8009", "label": "Phase"},
    "CHAIN":    {"icon": "⛓️",  "color": "#9B6DFF", "label": "Chain"},
    "AI":       {"icon": "🧠", "color": "#2EA043", "label": "AI"},
    "RESULT":   {"icon": "📋", "color": "#6E7681", "label": "Result"},
    "ERROR":    {"icon": "❌", "color": "#F85149", "label": "Error"},
    "SUCCESS":  {"icon": "✅", "color": "#2EA043", "label": "Success"},
    "INFO":     {"icon": "ℹ️",  "color": "#6E7681", "label": "Info"},
    "PROGRESS": {"icon": "📊", "color": "#4daafc", "label": "Progress"},
}

SIDEBAR_EXPANDED_WIDTH = 320
SIDEBAR_COLLAPSED_WIDTH = 42


class ActivitySidebar(QWidget):
    """
    Collapsible sidebar showing real-time orchestrator activity.

    Hooks into:
      - orchestrator.on_print → general tool output
      - orchestrator.on_progress → phase/step progress
      - orchestrator.on_task_update → task state changes
    """

    # Signals for thread-safe GUI updates
    _append_signal = pyqtSignal(str, str)   # (message, activity_type)
    _progress_signal = pyqtSignal(str, int, int)  # (phase, num, total)
    _task_signal = pyqtSignal(dict)         # task entry dict
    expand_requested = pyqtSignal()         # auto-expand on chain start

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.orchestrator = main_window.orchestrator
        self._entry_count = 0
        self._paused = False
        self._collapsed = False
        self._filter_type = "ALL"
        self._buffer = deque(maxlen=5000)
        self._current_phase = "Idle"
        self._current_step = "—"

        self.setMinimumWidth(SIDEBAR_COLLAPSED_WIDTH)
        self.setMaximumWidth(SIDEBAR_EXPANDED_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._build_ui()
        self._connect_signals()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # ── Collapsed strip (shown when collapsed) ──────
        self._collapsed_strip = QWidget()
        self._collapsed_strip.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)
        self._collapsed_strip.setStyleSheet("background: #141414;")
        cs_layout = QVBoxLayout(self._collapsed_strip)
        cs_layout.setContentsMargins(4, 8, 4, 8)
        cs_layout.setSpacing(8)

        self._btn_expand = QPushButton("◀")
        self._btn_expand.setFixedSize(34, 34)
        self._btn_expand.setToolTip("Expand activity sidebar")
        self._btn_expand.setStyleSheet(
            "QPushButton { background: #202020; color: #4daafc;"
            " border: 1px solid #2B2B2B; border-radius: 6px;"
            " font-size: 14px; font-weight: 700; }"
            "QPushButton:hover { background: #2B2B2B; border-color: #4daafc; }"
        )
        self._btn_expand.clicked.connect(self._expand)
        cs_layout.addWidget(self._btn_expand)

        # Collapsed live dot
        self._collapsed_dot = QLabel("●")
        self._collapsed_dot.setAlignment(Qt.AlignCenter)
        self._collapsed_dot.setStyleSheet(
            "color: #2EA043; font-size: 14px; font-weight: 900;"
        )
        cs_layout.addWidget(self._collapsed_dot)

        # Collapsed event count
        self._collapsed_count = QLabel("0")
        self._collapsed_count.setAlignment(Qt.AlignCenter)
        self._collapsed_count.setStyleSheet(
            "color: #3C3C3C; font-size: 11px;"
        )
        cs_layout.addWidget(self._collapsed_count)

        cs_layout.addStretch()
        self._collapsed_strip.hide()
        self._root.addWidget(self._collapsed_strip)

        # ── Expanded panel ──────────────────────────────
        self._expanded_panel = QWidget()
        self._expanded_panel.setStyleSheet("background: #141414;")
        ep_layout = QVBoxLayout(self._expanded_panel)
        ep_layout.setContentsMargins(0, 0, 0, 0)
        ep_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(
            "background: #181818; border-bottom: 1px solid #2B2B2B;"
        )
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(10, 0, 6, 0)
        hdr_layout.setSpacing(6)

        self._live_dot = QLabel("●")
        self._live_dot.setStyleSheet(
            "color: #2EA043; font-size: 14px; font-weight: 900;"
        )
        self._live_dot_visible = True

        title = QLabel("ACTIVITY")
        title.setStyleSheet(
            "color: #4daafc; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1.5px;"
        )

        self._lbl_count = QLabel("0")
        self._lbl_count.setStyleSheet("color: #3C3C3C; font-size: 11px;")

        hdr_layout.addWidget(self._live_dot)
        hdr_layout.addWidget(title)
        hdr_layout.addWidget(self._lbl_count)
        hdr_layout.addStretch()

        # Collapse button
        self._btn_collapse = QPushButton("▶")
        self._btn_collapse.setFixedSize(26, 26)
        self._btn_collapse.setToolTip("Collapse sidebar")
        self._btn_collapse.setStyleSheet(
            "QPushButton { background: transparent; color: #3C3C3C;"
            " border: none; font-size: 12px; }"
            "QPushButton:hover { color: #4daafc; }"
        )
        self._btn_collapse.clicked.connect(self._collapse)
        hdr_layout.addWidget(self._btn_collapse)

        ep_layout.addWidget(header)

        # Phase/status mini-bar
        self._phase_bar = QWidget()
        self._phase_bar.setFixedHeight(28)
        self._phase_bar.setStyleSheet(
            "background: #0D1117; border-bottom: 1px solid #1B2332;"
        )
        pb_layout = QHBoxLayout(self._phase_bar)
        pb_layout.setContentsMargins(10, 0, 10, 0)
        pb_layout.setSpacing(6)

        self._lbl_phase = QLabel("Idle")
        self._lbl_phase.setStyleSheet(
            "color: #6E7681; font-size: 11px; font-weight: 600;"
        )
        self._lbl_step = QLabel("")
        self._lbl_step.setStyleSheet(
            "color: #3C3C3C; font-size: 11px;"
        )

        pb_layout.addWidget(self._lbl_phase, stretch=1)
        pb_layout.addWidget(self._lbl_step)
        ep_layout.addWidget(self._phase_bar)

        # Progress bar (thin)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(3)
        self._progress.setStyleSheet(
            "QProgressBar { background: #0D1117; border: none; }"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #0078D4, stop:1 #4daafc);"
            "}"
        )
        ep_layout.addWidget(self._progress)

        # Activity feed
        self._feed = QPlainTextEdit()
        self._feed.setReadOnly(True)
        self._feed.setMaximumBlockCount(5000)
        self._feed.setFont(QFont("JetBrains Mono", 11))
        self._feed.setStyleSheet(
            "QPlainTextEdit {"
            "  background: #0D1117; color: #6E7681;"
            "  border: none; padding: 6px;"
            "  font-family: 'JetBrains Mono', monospace;"
            "  font-size: 12px;"
            "  selection-background-color: #0078D422;"
            "}"
        )
        self._feed.setPlaceholderText(
            "Activity will appear\nas JAMES runs tools…"
        )
        ep_layout.addWidget(self._feed, stretch=1)

        # Controls bar
        ctrl = QWidget()
        ctrl.setFixedHeight(32)
        ctrl.setStyleSheet(
            "background: #181818; border-top: 1px solid #2B2B2B;"
        )
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(6, 0, 6, 0)
        ctrl_layout.setSpacing(4)

        self._btn_pause = QPushButton("⏸")
        self._btn_pause.setFixedSize(26, 24)
        self._btn_pause.setCheckable(True)
        self._btn_pause.setToolTip("Pause/Resume feed")
        self._btn_pause.setStyleSheet(
            "QPushButton { background: transparent; color: #6E7681;"
            " border: none; font-size: 12px; }"
            "QPushButton:hover { color: #4daafc; }"
            "QPushButton:checked { color: #BB8009; }"
        )
        self._btn_pause.clicked.connect(self._toggle_pause)

        self._filter_combo = QComboBox()
        self._filter_combo.setFixedHeight(22)
        self._filter_combo.setStyleSheet(
            "QComboBox { background: #202020; color: #6E7681;"
            " border: 1px solid #2B2B2B; border-radius: 4px;"
            " padding: 0 6px; font-size: 11px; min-width: 60px; }"
            "QComboBox:hover { border-color: #3C3C3C; }"
            "QComboBox::drop-down { border: none; width: 16px; }"
            "QComboBox::down-arrow {"
            "  border-left: 3px solid transparent;"
            "  border-right: 3px solid transparent;"
            "  border-top: 4px solid #6E7681; margin-right: 4px;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background: #181818; color: #CCCCCC;"
            "  border: 1px solid #2B2B2B; font-size: 11px;"
            "  selection-background-color: #2B2B2B;"
            "}"
        )
        self._filter_combo.addItem("All", "ALL")
        for type_key, type_info in ACTIVITY_TYPES.items():
            self._filter_combo.addItem(
                f"{type_info['icon']} {type_info['label']}", type_key
            )
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        btn_clear = QPushButton("⌫")
        btn_clear.setFixedSize(26, 24)
        btn_clear.setToolTip("Clear feed")
        btn_clear.setStyleSheet(
            "QPushButton { background: transparent; color: #6E7681;"
            " border: none; font-size: 12px; }"
            "QPushButton:hover { color: #F85149; }"
        )
        btn_clear.clicked.connect(self._clear)

        btn_copy = QPushButton("⧉")
        btn_copy.setFixedSize(26, 24)
        btn_copy.setToolTip("Copy feed")
        btn_copy.setStyleSheet(
            "QPushButton { background: transparent; color: #6E7681;"
            " border: none; font-size: 13px; }"
            "QPushButton:hover { color: #4daafc; }"
        )
        btn_copy.clicked.connect(self._copy)

        ctrl_layout.addWidget(self._btn_pause)
        ctrl_layout.addWidget(self._filter_combo, stretch=1)
        ctrl_layout.addWidget(btn_clear)
        ctrl_layout.addWidget(btn_copy)
        ep_layout.addWidget(ctrl)

        self._root.addWidget(self._expanded_panel)

        # ── Pulse timer ─────────────────────────────────
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_dot)
        self._pulse_timer.start(800)

    # ── Collapse / Expand ────────────────────────────────────────

    def _collapse(self):
        self._collapsed = True
        self._expanded_panel.hide()
        self._collapsed_strip.show()
        self.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)

    def _expand(self):
        self._collapsed = False
        self._collapsed_strip.hide()
        self._expanded_panel.show()
        self.setFixedWidth(SIDEBAR_EXPANDED_WIDTH)

    def auto_expand(self):
        """Auto-expand when a chain starts (called externally)."""
        if self._collapsed:
            self._expand()

    # ── Hook into orchestrator ───────────────────────────────────

    def _hook_orchestrator(self):
        """Wire into orchestrator callbacks for real-time activity."""
        self._orig_on_print = self.orchestrator.on_print
        self._orig_on_progress = self.orchestrator.on_progress
        self._orig_on_task_update = self.orchestrator.on_task_update

        self.orchestrator.on_print = self._on_orch_print
        self.orchestrator.on_progress = self._on_orch_progress
        self.orchestrator.on_task_update = self._on_orch_task_update

    def _on_orch_print(self, msg: str):
        """Intercept orchestrator print — classify and forward."""
        if self._orig_on_print:
            self._orig_on_print(msg)
        activity_type = self._classify_message(msg)
        self._append_signal.emit(msg, activity_type)

        # Auto-expand on chain starts
        if activity_type == "CHAIN":
            self.expand_requested.emit()

    def _on_orch_progress(self, phase: str, num: int, total: int):
        if self._orig_on_progress:
            self._orig_on_progress(phase, num, total)
        self._progress_signal.emit(phase, num, total)

    def _on_orch_task_update(self, entry):
        if self._orig_on_task_update:
            self._orig_on_task_update(entry)
        try:
            self._task_signal.emit(entry.as_dict())
        except Exception:
            pass

    def _classify_message(self, msg: str) -> str:
        """Classify orchestrator message into activity type.

        Priority order (most specific → least):
          1. ERROR  — explicit failure indicators (highest priority)
          2. CHAIN  — structural chain markers (━━━, PHASE headers)
          3. PHASE  — step markers [1/4], [2/4], etc.
          4. SUCCESS — explicit win indicators (🔑, cracked)
          5. AI     — AI-prefixed recommendations
          6. PROGRESS — action emoji (📡, 🎯, 🔓, etc.)
          7. TOOL   — tool-name keywords (nmap, hashcat, etc.)
          8. RESULT — findings/summaries
          9. INFO   — everything else
        """
        msg_lower = msg.lower()

        # 1. ERROR — highest priority (failures must always stand out)
        if any(s in msg_lower for s in ["❌", "failed", "⚠"]):
            return "ERROR"
        # "error" as word boundary — avoid false hits on "error-free"
        if " error" in msg_lower or msg_lower.startswith("error"):
            return "ERROR"

        # 2. CHAIN markers (structural — ━━━ bars, PHASE headers)
        if any(s in msg for s in ["━", "[PHASE", "PHASE 1", "PHASE 2",
                                    "PHASE 3", "PHASE 4"]):
            return "CHAIN"

        # 3. PHASE step markers [1/4], [2/4] etc.
        if any(s in msg for s in ["[1/", "[2/", "[3/", "[4/", "[5/",
                                    "[6/", "[7/", "[8/"]):
            return "PHASE"

        # 4. SUCCESS — explicit win markers (not generic "complete")
        if any(s in msg_lower for s in ["✅", "🔑", "cracked", "🏁"]):
            return "SUCCESS"
        if "success" in msg_lower and "success" != msg_lower:
            return "SUCCESS"

        # 5. AI recommendations
        if any(s in msg_lower for s in ["🧠", "ai recommends", "ai analysis"]):
            return "AI"

        # 6. PROGRESS — action/status emoji (more specific than keywords)
        if any(s in msg for s in ["📡", "💥", "🎯", "🔓", "🌐", "👑",
                                    "🕵", "😈", "🍍", "🤖", "💀"]):
            return "PROGRESS"

        # 7. TOOL — explicit tool name mentions
        if any(s in msg_lower for s in ["nmap", "nikto", "gobuster",
                                          "hashcat", "aircrack", "hydra",
                                          "sqlmap", "hcxdumptool",
                                          "aireplay", "airodump",
                                          "masscan", "reaver", "bully",
                                          "mdk4", "john", "sslscan",
                                          "ettercap"]):
            return "TOOL"
        # Tool verbs (only if no emoji caught it as PROGRESS)
        if any(s in msg_lower for s in ["scanning", "bruting", "cracking",
                                          "capturing", "deauthing"]):
            return "TOOL"

        # 8. RESULT — findings and summaries
        if any(s in msg_lower for s in ["found", "discovered", "summary",
                                          "📊", "📋", "result"]):
            return "RESULT"

        # 9. INFO — default
        return "INFO"

    # ── Signal connections ───────────────────────────────────────

    def _connect_signals(self):
        self._append_signal.connect(self._on_append)
        self._progress_signal.connect(self._on_progress)
        self._task_signal.connect(self._on_task_update)
        self.expand_requested.connect(self.auto_expand)

    @pyqtSlot(str, str)
    def _on_append(self, message: str, activity_type: str):
        """Append an activity entry (GUI thread)."""
        ts = datetime.now().strftime("%H:%M:%S")
        type_info = ACTIVITY_TYPES.get(activity_type, ACTIVITY_TYPES["INFO"])

        # Buffer for filtering/replay
        self._buffer.append((ts, message, activity_type))
        self._entry_count += 1
        self._lbl_count.setText(str(self._entry_count))
        self._collapsed_count.setText(str(self._entry_count))

        # Update phase from chain/phase events
        if activity_type in ("CHAIN", "PHASE"):
            clean = message[:35].strip("━ ").strip()
            if clean:
                self._current_phase = clean
                self._lbl_phase.setText(clean)
                self._lbl_phase.setStyleSheet(
                    f"color: {type_info['color']}; font-size: 11px; font-weight: 600;"
                )

        # Apply filter
        if self._filter_type != "ALL" and activity_type != self._filter_type:
            return
        if self._paused:
            return

        # Format and append
        self._insert_entry(ts, message, activity_type, type_info)

        # Flash activity indicator
        self._flash_dot()

    def _insert_entry(self, ts, message, activity_type, type_info):
        """Insert a single formatted entry into the feed."""
        icon = type_info["icon"]
        color = type_info["color"]

        cursor = self._feed.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Timestamp
        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QColor("#2B2B2B"))
        fmt_ts.setFontFamily("JetBrains Mono")
        cursor.insertText(f"{ts} ", fmt_ts)

        # Icon
        fmt_icon = QTextCharFormat()
        fmt_icon.setForeground(QColor(color))
        fmt_icon.setFontWeight(QFont.Bold)
        cursor.insertText(f"{icon} ", fmt_icon)

        # Message (truncated for compact view)
        fmt_msg = QTextCharFormat()
        if activity_type in ("SUCCESS", "ERROR", "CHAIN"):
            fmt_msg.setForeground(QColor(color))
            fmt_msg.setFontWeight(QFont.Bold)
        elif activity_type == "PHASE":
            fmt_msg.setForeground(QColor("#CCCCCC"))
        else:
            fmt_msg.setForeground(QColor("#8B949E"))

        # Truncate long messages for sidebar width
        display_msg = message[:80] + ("…" if len(message) > 80 else "")
        cursor.insertText(f"{display_msg}\n", fmt_msg)

        # Auto-scroll
        sb = self._feed.verticalScrollBar()
        self._scroll_anim = QPropertyAnimation(sb, b"value")
        self._scroll_anim.setDuration(150)
        self._scroll_anim.setStartValue(sb.value())
        self._scroll_anim.setEndValue(sb.maximum())
        self._scroll_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._scroll_anim.start()

    @pyqtSlot(str, int, int)
    def _on_progress(self, phase: str, num: int, total: int):
        self._progress.setVisible(True)
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(num)
        self._current_phase = phase
        self._current_step = f"{num}/{total}"
        self._lbl_phase.setText(phase)
        self._lbl_phase.setStyleSheet(
            "color: #BB8009; font-size: 11px; font-weight: 600;"
        )
        self._lbl_step.setText(self._current_step)

        if num >= total:
            QTimer.singleShot(3000, lambda: self._progress.setVisible(False))
            self._lbl_phase.setText("Complete")
            self._lbl_phase.setStyleSheet(
                "color: #2EA043; font-size: 11px; font-weight: 600;"
            )

    @pyqtSlot(dict)
    def _on_task_update(self, entry: dict):
        action = entry.get("action", "?")
        status = entry.get("status", "?")
        tool = entry.get("tool", "")

        if status == "running":
            self._lbl_phase.setText(f"{tool}: {action}"[:30])
            self._lbl_phase.setStyleSheet(
                "color: #BB8009; font-size: 11px; font-weight: 600;"
            )
            self._append_signal.emit(
                f"Task started: {action} ({tool})", "TOOL"
            )
        elif status == "done":
            self._lbl_phase.setText("Ready")
            self._lbl_phase.setStyleSheet(
                "color: #2EA043; font-size: 11px; font-weight: 600;"
            )
        elif status == "error":
            self._lbl_phase.setText("Error")
            self._lbl_phase.setStyleSheet(
                "color: #F85149; font-size: 11px; font-weight: 600;"
            )

    # ── UI actions ───────────────────────────────────────────────

    def _toggle_pause(self):
        self._paused = self._btn_pause.isChecked()
        if self._paused:
            self._btn_pause.setText("▶")
        else:
            self._btn_pause.setText("⏸")
            self._replay_buffer()

    def _replay_buffer(self):
        self._feed.clear()
        for ts, msg, atype in self._buffer:
            if self._filter_type != "ALL" and atype != self._filter_type:
                continue
            type_info = ACTIVITY_TYPES.get(atype, ACTIVITY_TYPES["INFO"])
            self._insert_entry(ts, msg, atype, type_info)
        sb = self._feed.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_filter_changed(self, index: int):
        self._filter_type = self._filter_combo.currentData() or "ALL"
        self._replay_buffer()

    def _clear(self):
        self._feed.clear()
        self._buffer.clear()
        self._entry_count = 0
        self._lbl_count.setText("0")
        self._collapsed_count.setText("0")
        self._lbl_phase.setText("Idle")
        self._lbl_phase.setStyleSheet(
            "color: #6E7681; font-size: 11px; font-weight: 600;"
        )
        self._lbl_step.setText("")
        self._progress.setVisible(False)

    def _copy(self):
        QApplication.clipboard().setText(self._feed.toPlainText())
        from james.gui.toast import show_toast
        show_toast(self.main_window, "Activity log copied", "info")

    def _flash_dot(self):
        """Flash live dot on activity."""
        self._live_dot.setStyleSheet(
            "color: #4daafc; font-size: 14px; font-weight: 900;"
        )
        self._collapsed_dot.setStyleSheet(
            "color: #4daafc; font-size: 14px; font-weight: 900;"
        )
        QTimer.singleShot(300, lambda: (
            self._live_dot.setStyleSheet(
                "color: #2EA043; font-size: 14px; font-weight: 900;"
            ),
            self._collapsed_dot.setStyleSheet(
                "color: #2EA043; font-size: 14px; font-weight: 900;"
            ),
        ))

    def _pulse_dot(self):
        if self._paused:
            return
        if self._live_dot_visible:
            dim = "color: #1A3A2A; font-size: 14px; font-weight: 900;"
            self._live_dot.setStyleSheet(dim)
            self._collapsed_dot.setStyleSheet(dim)
        else:
            bright = "color: #2EA043; font-size: 14px; font-weight: 900;"
            self._live_dot.setStyleSheet(bright)
            self._collapsed_dot.setStyleSheet(bright)
        self._live_dot_visible = not self._live_dot_visible
