"""
JAMES GUI — Design System v4 (Antigravity Theme)

Sourced from Antigravity Dark Modern color theme.
Primary:    Blue   #0078D4  (primary actions — button.background)
Active/Nav: Blue   #4daafc  (active tab, focused input — textLink.foreground)
Backgrounds: editor #1F1F1F · panel/sidebar #181818 · dropdown/input #313131
Spacing:    4 / 8 / 12 / 16 / 24
Typography: 4 strict tiers
"""

# ── Palette ────────────────────────────────────────────────────────────
PALETTE = {
    "bg_deep": "#1F1F1F",  # editor.background
    "surface1": "#181818",  # panel.background / sideBar.background
    "surface2": "#202020",  # editorWidget.background
    "hover": "#2B2B2B",  # tab.hoverBackground / textBlockQuote.background
    "border": "#2B2B2B",  # sideBar.border / editorGroup.border
    "gold": "#0078D4",  # button.background / focusBorder (primary blue)
    "gold_hi": "#026EC1",  # button.hoverBackground
    "gold_dim": "#0078D428",  # primary blue @ low opacity
    "cyan": "#4daafc",  # textLink.foreground (active/nav blue)
    "cyan_dim": "#4daafc1A",  # active blue @ low opacity
    "green": "#2EA043",  # editorGutter.addedBackground
    "green_dim": "#2EA04320",  # green @ low opacity
    "red": "#F85149",  # errorForeground
    "red_dim": "#F8514920",  # red @ low opacity
    "amber": "#BB8009",  # editor.findMatchBackground (warm amber)
    "amber_dim": "#BB800920",  # amber @ low opacity
    "text": "#CCCCCC",  # editor.foreground / foreground
    "text_mid": "#6E7681",  # editorLineNumber.foreground
    "text_dim": "#3C3C3C",  # textPreformat.background / border tones
}

DARK_STYLESHEET = """
/* ──────────────────────────────────────────────────────────
   BASE  —  Antigravity Dark Modern
────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #1F1F1F;
    color: #CCCCCC;
    font-family: 'Segoe UI', 'Inter', 'Liberation Sans', sans-serif;
    font-size: 14px;
}

/* ──────────────────────────────────────────────────────────
   MENU BAR
────────────────────────────────────────────────────────── */
QMenuBar {
    background: #181818;
    color: #6E7681;
    border-bottom: 1px solid #2B2B2B;
    padding: 2px 4px;
}
QMenuBar::item { padding: 6px 14px; border-radius: 4px; }
QMenuBar::item:selected { background: #2B2B2B; color: #CCCCCC; }
QMenu {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { padding: 8px 24px; border-radius: 4px; margin: 1px; }
QMenu::item:selected { background: #2B2B2B; }
QMenu::separator { height: 1px; background: #2B2B2B; margin: 4px 8px; }

/* ──────────────────────────────────────────────────────────
   TAB BAR  —  #4daafc for active, matches textLink.foreground
────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #1F1F1F;
}
QTabBar { qproperty-drawBase: 0; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #6E7681;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
    font-size: 14px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #4daafc;
    border-bottom: 2px solid #0078D4;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #CCCCCC;
    background: #181818;
    border-radius: 5px 5px 0 0;
}

/* ──────────────────────────────────────────────────────────
   BUTTONS — 3 tiers
────────────────────────────────────────────────────────── */

/* Tier 3 — utility (default) */
QPushButton {
    background: #181818;
    color: #6E7681;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 14px;
    font-weight: 500;
    min-height: 28px;
}
QPushButton:hover {
    background: #2B2B2B;
    color: #CCCCCC;
    border-color: #3C3C3C;
}
QPushButton:pressed { background: #202020; }
QPushButton:disabled { background: #141414; color: #3C3C3C; border-color: #2B2B2B; }
QPushButton:checked { background: #2B2B2B; color: #4daafc; border-color: #0078D455; }

/* Tier 1 — primary action (#0078D4 — button.background) */
QPushButton#primaryBtn {
    background: #0078D4;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 700;
    min-height: 44px;
    padding: 8px 24px;
    letter-spacing: 0.3px;
}
QPushButton#primaryBtn:hover { background: #026EC1; }
QPushButton#primaryBtn:pressed { background: #005BA1; }
QPushButton#primaryBtn:disabled { background: #1A3A5C; color: #4B7AAB; }
QPushButton#primaryBtn:checked { background: #026EC1; }

/* Tier 2 — secondary action */
QPushButton#secondaryBtn {
    background: #202020;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
}
QPushButton#secondaryBtn:hover { background: #2B2B2B; border-color: #3C3C3C; }
QPushButton#secondaryBtn:disabled { color: #3C3C3C; }

/* Danger */
QPushButton#dangerBtn {
    background: transparent;
    color: #F85149;
    border: 1px solid #F8514930;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#dangerBtn:hover { background: #F8514914; border-color: #F8514970; }
QPushButton#dangerBtn:pressed { background: #F8514920; }

/* Success */
QPushButton#successBtn {
    background: transparent;
    color: #2EA043;
    border: 1px solid #2EA04330;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#successBtn:hover { background: #2EA04314; border-color: #2EA04370; }

/* Warning */
QPushButton#warnBtn {
    background: transparent;
    color: #BB8009;
    border: 1px solid #BB800930;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#warnBtn:hover { background: #BB800914; border-color: #BB800970; }

/* ──────────────────────────────────────────────────────────
   INPUTS
────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: #0078D422;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #0078D455;
}
QLineEdit::placeholder { color: #3C3C3C; }

/* ──────────────────────────────────────────────────────────
   COMBO BOX
────────────────────────────────────────────────────────── */
QComboBox {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 14px;
    min-width: 100px;
}
QComboBox:hover { border-color: #3C3C3C; background: #202020; }
QComboBox:focus { border-color: #0078D455; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #6E7681;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #2B2B2B;
    selection-color: #CCCCCC;
    outline: none;
}

/* ──────────────────────────────────────────────────────────
   SPIN BOX
────────────────────────────────────────────────────────── */
QSpinBox {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 14px;
    min-width: 60px;
}
QSpinBox:focus { border-color: #0078D455; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #202020;
    border: none;
    width: 16px;
    border-radius: 2px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #2B2B2B; }

/* ──────────────────────────────────────────────────────────
   GROUP BOXES — minimal borders
────────────────────────────────────────────────────────── */
QGroupBox {
    background: #181818;
    border: 1px solid #2B2B2B;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-size: 12px;
    font-weight: 700;
    color: #3C3C3C;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #6E7681;
    font-size: 12px;
    letter-spacing: 1.5px;
}

/* ──────────────────────────────────────────────────────────
   LABELS — 4-tier system
────────────────────────────────────────────────────────── */
/* T1 — app title */
QLabel#titleLabel {
    font-size: 24px;
    font-weight: 700;
    color: #CCCCCC;
    letter-spacing: 0.3px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
/* T2 — section header */
QLabel#sectionLabel {
    font-size: 16px;
    font-weight: 700;
    color: #CCCCCC;
}
/* T3 — labels (default QLabel) */
QLabel { font-size: 14px; color: #CCCCCC; }
/* T4 — metadata */
QLabel#metaLabel {
    font-size: 12px;
    color: #3C3C3C;
    letter-spacing: 0.5px;
}
QLabel#dimLabel { font-size: 14px; color: #6E7681; }

/* Semantic states */
QLabel#statusOk   { color: #2EA043; font-weight: 700; }
QLabel#statusBad  { color: #F85149; font-weight: 700; }
QLabel#statusWarn { color: #BB8009; font-weight: 700; }
QLabel#goldAccent { color: #4daafc; font-weight: 700; font-size: 16px; }

/* ──────────────────────────────────────────────────────────
   SCROLLBARS — ultra slim, 5px
────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2B2B2B;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #3C3C3C; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2B2B2B;
    border-radius: 2px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #3C3C3C; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ──────────────────────────────────────────────────────────
   PROGRESS BAR — Antigravity blue, thin strip
────────────────────────────────────────────────────────── */
QProgressBar {
    background: #181818;
    border: none;
    border-radius: 3px;
    height: 4px;
    color: transparent;
    text-align: center;
}
QProgressBar::chunk {
    background: #0078D4;
    border-radius: 3px;
}
QProgressBar[textVisible="true"] {
    height: 20px;
    color: #6E7681;
    font-size: 13px;
}
QProgressBar[textVisible="true"]::chunk { border-radius: 4px; }

/* ──────────────────────────────────────────────────────────
   TABLE
────────────────────────────────────────────────────────── */
QHeaderView::section {
    background: #181818;
    color: #6E7681;
    border: none;
    border-bottom: 1px solid #2B2B2B;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QTableWidget {
    background: #1F1F1F;
    gridline-color: #2B2B2B;
    color: #CCCCCC;
    border: none;
    alternate-background-color: #181818;
    font-size: 14px;
    selection-background-color: #2B2B2B;
    selection-color: #CCCCCC;
}
QTableWidget::item { padding: 6px 12px; border: none; }
QTableWidget::item:hover { background: #202020; }

/* ──────────────────────────────────────────────────────────
   SPLITTER
────────────────────────────────────────────────────────── */
QSplitter::handle { background: #2B2B2B; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: #3C3C3C; }

/* ──────────────────────────────────────────────────────────
   STATUS BAR
────────────────────────────────────────────────────────── */
QStatusBar {
    background: #181818;
    color: #3C3C3C;
    border-top: 1px solid #2B2B2B;
    font-size: 13px;
    padding: 0 8px;
    min-height: 22px;
}
QStatusBar::item { border: none; }

/* ──────────────────────────────────────────────────────────
   CHECKBOX
────────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #CCCCCC;
    font-size: 14px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #2B2B2B;
    border-radius: 3px;
    background: #181818;
}
QCheckBox::indicator:hover { border-color: #3C3C3C; }
QCheckBox::indicator:checked {
    background: #0078D4;
    border-color: #0078D4;
}

/* ──────────────────────────────────────────────────────────
   MISC
────────────────────────────────────────────────────────── */
QScrollArea { background: #1F1F1F; border: none; }
QFrame#hline { background: #2B2B2B; max-height: 1px; min-height: 1px; }
QFrame#vline { background: #2B2B2B; max-width: 1px; min-width: 1px; }
QToolTip {
    background: #181818;
    color: #CCCCCC;
    border: 1px solid #2B2B2B;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}
QDialog { background: #181818; }
QMessageBox { background: #181818; }
QMessageBox QLabel { color: #CCCCCC; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

# ── Per-widget style constants ─────────────────────────────────────────
TERMINAL_STYLE = (
    "background: #141414;"
    "color: #2EA043;"
    "border: 1px solid #2B2B2B;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 14px;"
    "selection-background-color: #0078D422;"
)

LOG_STYLE = (
    "background: #141414;"
    "color: #6E7681;"
    "border: 1px solid #2B2B2B;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 14px;"
)

HEADER_STYLE = "background: #181818;" "border-bottom: 1px solid #2B2B2B;"

SESSION_STRIP_STYLE = "background: #181818;" "border-top: 1px solid #2B2B2B;"

SURFACE_CARD_STYLE = (
    "background: #202020;" "border: 1px solid #2B2B2B;" "border-radius: 8px;"
)

METRIC_CARD_STYLE = (
    "background: #181818;" "border: 1px solid #2B2B2B;" "border-radius: 6px;"
)
