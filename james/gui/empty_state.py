"""Reusable empty-state panel for JAMES desktop tabs.

Honest, centered, muted — headline + one-line explainer, no decorative chrome.
Matches the React empty-state pattern (icon glyph + headline + explainer).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from james.gui.theme import PALETTE


class EmptyState(QFrame):
    """Centered empty-state panel for a table/list that has nothing to show yet.

    Usage::

        empty = EmptyState(
            "No networks detected yet",
            "Run a scan to populate the airspace table.",
        )
        layout.addWidget(empty)
        # later: empty.setVisible(table.rowCount() == 0)
    """

    def __init__(
        self,
        headline: str,
        explainer: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            "QFrame#emptyState {"
            f"  background: {PALETTE['bg_deep']};"
            "  border: none;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 40, 24, 40)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Badge — a simple rounded square, no emoji (craft floor).
        badge = QLabel("·")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(40, 40)
        badge.setStyleSheet(
            f"background: {PALETTE['surface2']};"
            f"border: 1px solid {PALETTE['border']};"
            "border-radius: 10px;"
            f"color: {PALETTE['text_dim']};"
            "font-size: 22px; font-weight: 700;"
        )
        layout.addWidget(badge, 0, Qt.AlignHCenter)

        title = QLabel(headline)
        title.setObjectName("sectionLabel")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 14px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        layout.addWidget(title)

        if explainer:
            body = QLabel(explainer)
            body.setObjectName("dimLabel")
            body.setAlignment(Qt.AlignCenter)
            body.setWordWrap(True)
            body.setMaximumWidth(420)
            body.setStyleSheet(
                f"color: {PALETTE['text_mid']}; font-size: 13px;"
                "background: transparent; border: none;"
            )
            layout.addWidget(body, 0, Qt.AlignHCenter)

        self._title = title
        self._body = body if explainer else None

    def set_copy(self, headline: str, explainer: str = "") -> None:
        self._title.setText(headline)
        if self._body is not None:
            self._body.setText(explainer)
            self._body.setVisible(bool(explainer))
