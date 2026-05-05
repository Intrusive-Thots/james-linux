"""
Toast Notification System for JAMES.

Provides non-intrusive slide-in notifications that auto-dismiss.
Supports info, success, warning, and error levels with distinct
styling and stacking for multiple simultaneous toasts.
"""

from PyQt5.QtWidgets import QLabel, QWidget, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PyQt5.QtGui import QFont


class Toast(QLabel):
    """A single toast notification widget."""

    _active_toasts: list = []  # class-level stack tracker

    STYLES = {
        "info": {
            "bg": "#0d1e30",
            "border": "#00f0ff",
            "text": "#00f0ff",
            "icon": "ℹ️",
        },
        "success": {
            "bg": "#0d2e1a",
            "border": "#00ff88",
            "text": "#00ff88",
            "icon": "✅",
        },
        "warning": {
            "bg": "#2a1a00",
            "border": "#ff6b35",
            "text": "#ff6b35",
            "icon": "⚠️",
        },
        "error": {
            "bg": "#1a0808",
            "border": "#ff4757",
            "text": "#ff4757",
            "icon": "❌",
        },
    }

    def __init__(self, parent: QWidget, message: str, level: str = "info",
                 duration: int = 3000):
        super().__init__(parent)
        style = self.STYLES.get(level, self.STYLES["info"])

        self.setText(f"  {style['icon']}  {message}")
        self.setFont(QFont("JetBrains Mono", 11))
        self.setStyleSheet(f"""
            QLabel {{
                background: {style['bg']};
                color: {style['text']};
                border: 1px solid {style['border']}80;
                border-left: 3px solid {style['border']};
                border-radius: 8px;
                padding: 12px 20px 12px 12px;
                font-weight: bold;
            }}
        """)
        self.setMinimumWidth(320)
        self.setMaximumWidth(500)
        self.adjustSize()
        self.setFixedHeight(max(self.height(), 44))

        # Position: stack above existing toasts
        Toast._active_toasts.append(self)
        self._reposition_all()

        # Opacity effect for fade-out
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

        self.show()
        self.raise_()

        # Slide in animation
        start = QPoint(parent.width(), self.y())
        end = QPoint(parent.width() - self.width() - 20, self.y())
        self._slide = QPropertyAnimation(self, b"pos")
        self._slide.setDuration(300)
        self._slide.setStartValue(start)
        self._slide.setEndValue(end)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self.move(start)
        self._slide.start()

        # Auto-dismiss
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)
        self._dismiss_timer.start(duration)

    def _reposition_all(self):
        """Reposition all active toasts so they stack from top."""
        parent = self.parent()
        if not parent:
            return
        y_offset = 80  # below header
        for toast in Toast._active_toasts:
            x = parent.width() - toast.width() - 20
            toast.move(x, y_offset)
            y_offset += toast.height() + 8

    def _fade_out(self):
        """Animate opacity to 0 then remove."""
        self._fade = QPropertyAnimation(self._opacity, b"opacity")
        self._fade.setDuration(400)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.InCubic)
        self._fade.finished.connect(self._remove)
        self._fade.start()

    def _remove(self):
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        # Reposition remaining
        if Toast._active_toasts:
            Toast._active_toasts[0]._reposition_all()
        self.deleteLater()

    def mousePressEvent(self, event):
        """Click to dismiss early."""
        self._dismiss_timer.stop()
        self._fade_out()


def show_toast(parent: QWidget, message: str, level: str = "info",
               duration: int = 3000):
    """
    Show a toast notification.

    Args:
        parent: Parent widget (usually MainWindow)
        message: Text to display
        level: One of 'info', 'success', 'warning', 'error'
        duration: Auto-dismiss time in ms
    """
    Toast(parent, message, level, duration)
