"""
JAMES GUI — Design System v3

Primary:    Gold   #C8961A  (primary actions ONLY)
Active/Nav: Cyan   #00C8FF  (active tab, focused input ONLY)
Spacing:    4 / 8 / 12 / 16 / 24
Typography: 4 strict tiers
"""

# ── Palette ────────────────────────────────────────────────────────────
PALETTE = {
    "bg_deep":   "#08111F",
    "surface1":  "#0D1726",
    "surface2":  "#111D2E",
    "hover":     "#162437",
    "border":    "#1A2A3D",
    "gold":      "#C8961A",
    "gold_hi":   "#DBA820",
    "gold_dim":  "#C8961A28",
    "cyan":      "#00C8FF",
    "cyan_dim":  "#00C8FF1A",
    "green":     "#00C875",
    "green_dim": "#00C87520",
    "red":       "#E63946",
    "red_dim":   "#E6394620",
    "amber":     "#F0A500",
    "amber_dim": "#F0A50020",
    "text":      "#C8D6E5",
    "text_mid":  "#6E7B8B",
    "text_dim":  "#3D5060",
}

DARK_STYLESHEET = """
/* ──────────────────────────────────────────────────────────
   BASE
────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #08111F;
    color: #C8D6E5;
    font-family: 'Segoe UI', 'Inter', 'Liberation Sans', sans-serif;
    font-size: 11px;
}

/* ──────────────────────────────────────────────────────────
   MENU BAR
────────────────────────────────────────────────────────── */
QMenuBar {
    background: #0D1726;
    color: #6E7B8B;
    border-bottom: 1px solid #1A2A3D;
    padding: 2px 4px;
}
QMenuBar::item { padding: 6px 14px; border-radius: 4px; }
QMenuBar::item:selected { background: #162437; color: #C8D6E5; }
QMenu {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { padding: 8px 24px; border-radius: 4px; margin: 1px; }
QMenu::item:selected { background: #162437; }
QMenu::separator { height: 1px; background: #1A2A3D; margin: 4px 8px; }

/* ──────────────────────────────────────────────────────────
   TAB BAR  — cyan for active only
────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #08111F;
}
QTabBar { qproperty-drawBase: 0; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #6E7B8B;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
    font-size: 11px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #00C8FF;
    border-bottom: 2px solid #00C8FF;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #C8D6E5;
    background: #0D1726;
    border-radius: 5px 5px 0 0;
}

/* ──────────────────────────────────────────────────────────
   BUTTONS — 3 tiers
────────────────────────────────────────────────────────── */

/* Tier 3 — utility (default) */
QPushButton {
    background: #0D1726;
    color: #6E7B8B;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 500;
    min-height: 28px;
}
QPushButton:hover {
    background: #162437;
    color: #C8D6E5;
    border-color: #253A50;
}
QPushButton:pressed { background: #111D2E; }
QPushButton:disabled { background: #0A1220; color: #3D5060; border-color: #1A2A3D; }
QPushButton:checked { background: #162437; color: #00C8FF; border-color: #00C8FF55; }

/* Tier 1 — primary action (GOLD, dominant) */
QPushButton#primaryBtn {
    background: #C8961A;
    color: #08111F;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    min-height: 44px;
    padding: 8px 24px;
    letter-spacing: 0.3px;
}
QPushButton#primaryBtn:hover { background: #DBA820; }
QPushButton#primaryBtn:pressed { background: #B8861A; }
QPushButton#primaryBtn:disabled { background: #3D2A00; color: #6E5010; }
QPushButton#primaryBtn:checked { background: #DBA820; }

/* Tier 2 — secondary action */
QPushButton#secondaryBtn {
    background: #111D2E;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    min-height: 36px;
}
QPushButton#secondaryBtn:hover { background: #162437; border-color: #253A50; }
QPushButton#secondaryBtn:disabled { color: #3D5060; }

/* Danger */
QPushButton#dangerBtn {
    background: transparent;
    color: #E63946;
    border: 1px solid #E6394630;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#dangerBtn:hover { background: #E6394614; border-color: #E6394870; }
QPushButton#dangerBtn:pressed { background: #E6394620; }

/* Success */
QPushButton#successBtn {
    background: transparent;
    color: #00C875;
    border: 1px solid #00C87530;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#successBtn:hover { background: #00C87514; border-color: #00C87570; }

/* Warning */
QPushButton#warnBtn {
    background: transparent;
    color: #F0A500;
    border: 1px solid #F0A50030;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#warnBtn:hover { background: #F0A50014; border-color: #F0A50070; }

/* ──────────────────────────────────────────────────────────
   INPUTS
────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    selection-background-color: #00C8FF22;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #00C8FF55;
}
QLineEdit::placeholder { color: #3D5060; }

/* ──────────────────────────────────────────────────────────
   COMBO BOX
────────────────────────────────────────────────────────── */
QComboBox {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    min-width: 100px;
}
QComboBox:hover { border-color: #253A50; background: #111D2E; }
QComboBox:focus { border-color: #00C8FF55; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #6E7B8B;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #162437;
    selection-color: #C8D6E5;
    outline: none;
}

/* ──────────────────────────────────────────────────────────
   SPIN BOX
────────────────────────────────────────────────────────── */
QSpinBox {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 11px;
    min-width: 60px;
}
QSpinBox:focus { border-color: #00C8FF55; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #111D2E;
    border: none;
    width: 16px;
    border-radius: 2px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #162437; }

/* ──────────────────────────────────────────────────────────
   GROUP BOXES — minimal borders
────────────────────────────────────────────────────────── */
QGroupBox {
    background: #0D1726;
    border: 1px solid #1A2A3D;
    border-radius: 8px;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    color: #6E7B8B;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
    background: #0D1726;
    border-radius: 3px;
}

/* ──────────────────────────────────────────────────────────
   LABELS — 4-tier system
────────────────────────────────────────────────────────── */
/* T1 — app title */
QLabel#titleLabel {
    font-size: 20px;
    font-weight: 700;
    color: #C8D6E5;
    letter-spacing: 0.3px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
/* T2 — section header */
QLabel#sectionLabel {
    font-size: 13px;
    font-weight: 700;
    color: #C8D6E5;
}
/* T3 — labels (default QLabel) */
QLabel { font-size: 11px; color: #C8D6E5; }
/* T4 — metadata */
QLabel#metaLabel {
    font-size: 9px;
    color: #3D5060;
    letter-spacing: 0.5px;
}
QLabel#dimLabel { font-size: 11px; color: #6E7B8B; }

/* Semantic states */
QLabel#statusOk   { color: #00C875; font-weight: 700; }
QLabel#statusBad  { color: #E63946; font-weight: 700; }
QLabel#statusWarn { color: #F0A500; font-weight: 700; }
QLabel#goldAccent { color: #C8961A; font-weight: 700; font-size: 13px; }

/* ──────────────────────────────────────────────────────────
   SCROLLBARS — ultra slim, 5px
────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #1A2A3D;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #253A50; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #1A2A3D;
    border-radius: 2px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #253A50; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ──────────────────────────────────────────────────────────
   PROGRESS BAR — gold, thin strip
────────────────────────────────────────────────────────── */
QProgressBar {
    background: #0D1726;
    border: none;
    border-radius: 3px;
    height: 4px;
    color: transparent;
    text-align: center;
}
QProgressBar::chunk {
    background: #C8961A;
    border-radius: 3px;
}
QProgressBar[textVisible="true"] {
    height: 20px;
    color: #6E7B8B;
    font-size: 10px;
}
QProgressBar[textVisible="true"]::chunk { border-radius: 4px; }

/* ──────────────────────────────────────────────────────────
   TABLE
────────────────────────────────────────────────────────── */
QHeaderView::section {
    background: #0D1726;
    color: #6E7B8B;
    border: none;
    border-bottom: 1px solid #1A2A3D;
    padding: 8px 12px;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QTableWidget {
    background: #08111F;
    gridline-color: #1A2A3D;
    color: #C8D6E5;
    border: none;
    alternate-background-color: #0D1726;
    font-size: 11px;
    selection-background-color: #162437;
    selection-color: #C8D6E5;
}
QTableWidget::item { padding: 6px 12px; border: none; }
QTableWidget::item:hover { background: #111D2E; }

/* ──────────────────────────────────────────────────────────
   SPLITTER
────────────────────────────────────────────────────────── */
QSplitter::handle { background: #1A2A3D; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: #253A50; }

/* ──────────────────────────────────────────────────────────
   STATUS BAR
────────────────────────────────────────────────────────── */
QStatusBar {
    background: #0D1726;
    color: #3D5060;
    border-top: 1px solid #1A2A3D;
    font-size: 10px;
    padding: 0 8px;
    min-height: 22px;
}
QStatusBar::item { border: none; }

/* ──────────────────────────────────────────────────────────
   MISC
────────────────────────────────────────────────────────── */
QScrollArea { background: #08111F; border: none; }
QFrame#hline { background: #1A2A3D; max-height: 1px; min-height: 1px; }
QFrame#vline { background: #1A2A3D; max-width: 1px; min-width: 1px; }
QToolTip {
    background: #0D1726;
    color: #C8D6E5;
    border: 1px solid #1A2A3D;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}
QDialog { background: #0D1726; }
QMessageBox { background: #0D1726; }
QMessageBox QLabel { color: #C8D6E5; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

# ── Per-widget style constants ─────────────────────────────────────────
TERMINAL_STYLE = (
    "background: #050C18;"
    "color: #00C875;"
    "border: 1px solid #1A2A3D;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 11px;"
    "selection-background-color: #00C8FF22;"
)

LOG_STYLE = (
    "background: #050C18;"
    "color: #6E7B8B;"
    "border: 1px solid #1A2A3D;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 11px;"
)

HEADER_STYLE = (
    "background: #0D1726;"
    "border-bottom: 1px solid #1A2A3D;"
)

SESSION_STRIP_STYLE = (
    "background: #0D1726;"
    "border-top: 1px solid #1A2A3D;"
)

SURFACE_CARD_STYLE = (
    "background: #111D2E;"
    "border: 1px solid #1A2A3D;"
    "border-radius: 8px;"
)

METRIC_CARD_STYLE = (
    "background: #0D1726;"
    "border: 1px solid #1A2A3D;"
    "border-radius: 6px;"
)
