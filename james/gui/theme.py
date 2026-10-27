"""
JAMES GUI — Design System v4 (Tactical Theme)

Aligned with the React web app palette (web/tailwind.config.js).
Primary:    Teal   #2EC4B6  (primary actions)
Active/Nav: Cyan   #22D3EE  (active tab, focused input, accent)
Backgrounds: canvas #0B1120 · panel #111827 · elevated #1F2937 · surface #161E2E
Spacing:    4 / 8 / 12 / 16 / 24
Typography: 4 strict tiers (Inter / JetBrains Mono)
"""

# ── Palette ────────────────────────────────────────────────────────────
PALETTE = {
    "bg_deep": "#0B1120",  # canvas / React bg
    "surface1": "#111827",  # panel / React bg-panel
    "surface2": "#161E2E",  # surface / React bg-surface
    "hover": "#1c3146",  # hover / React border-hover base
    "border": "#1c3146",  # line / React line
    "gold": "#2EC4B6",  # accent teal / React accent
    "gold_hi": "#26a89c",  # accent teal hover
    "gold_dim": "#2EC4B628",  # accent teal @ low opacity
    "cyan": "#22D3EE",  # accent cyan / React accent.cyan
    "cyan_dim": "#22D3EE1A",  # accent cyan @ low opacity
    "green": "#10B981",  # success / React success
    "green_dim": "#10B98120",  # success @ low opacity
    "red": "#EF4444",  # danger / React danger
    "red_dim": "#EF444420",  # danger @ low opacity
    "amber": "#F59E0B",  # warning / React warning
    "amber_dim": "#F59E0B20",  # warning @ low opacity
    "text": "#E5E7EB",  # text.primary / React text.primary
    "text_mid": "#94A3B8",  # text.secondary / React text.secondary
    "text_dim": "#64748B",  # text.muted / React text.muted
}

DARK_STYLESHEET = """
/* ──────────────────────────────────────────────────────────
   BASE  —  JAMES Tactical
────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #0B1120;
    color: #E5E7EB;
    font-family: 'Inter', 'Segoe UI', 'Liberation Sans', sans-serif;
    font-size: 14px;
}

/* ──────────────────────────────────────────────────────────
   MENU BAR
────────────────────────────────────────────────────────── */
QMenuBar {
    background: #111827;
    color: #94A3B8;
    border-bottom: 1px solid #1c3146;
    padding: 2px 4px;
}
QMenuBar::item { padding: 6px 14px; border-radius: 4px; }
QMenuBar::item:selected { background: #1c3146; color: #E5E7EB; }
QMenu {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { padding: 8px 24px; border-radius: 4px; margin: 1px; }
QMenu::item:selected { background: #1c3146; }

/* ──────────────────────────────────────────────────────────
   TAB BAR  —  #22D3EE active highlight
────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #0B1120;
}
QTabBar { qproperty-drawBase: 0; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #94A3B8;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
    font-size: 14px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #22D3EE;
    border-bottom: 2.5px solid #22D3EE;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #E5E7EB;
    background: #1a2436;
    border-radius: 5px 5px 0 0;
}

/* ──────────────────────────────────────────────────────────
   BUTTONS — 3 tiers
────────────────────────────────────────────────────────── */

/* Tier 3 — utility (default) */
QPushButton {
    background: #111827;
    color: #94A3B8;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 14px;
    font-weight: 500;
    min-height: 28px;
}
QPushButton:hover {
    background: #1c3146;
    color: #E5E7EB;
    border-color: #64748B;
}
QPushButton:pressed { background: #161E2E; }
QPushButton:disabled { background: #071018; color: #64748B; border-color: #1c3146; }
QPushButton:checked { background: #1c3146; color: #22D3EE; border-color: #2EC4B655; }

/* Tier 1 — primary action (solid teal) */
QPushButton#primaryBtn {
    background: #2EC4B6;
    color: #04221E;
    border: 1px solid #2EC4B644;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 700;
    min-height: 44px;
    padding: 8px 24px;
    letter-spacing: 0.3px;
}
QPushButton#primaryBtn:hover {
    background: #26a89c;
    border-color: #22D3EE;
}
QPushButton#primaryBtn:pressed {
    background: #1a8a80;
}
QPushButton#primaryBtn:disabled { background: #0d3a38; color: #3a7a74; }
QPushButton#primaryBtn:checked { background: #26a89c; }

/* Tier 2 — secondary action */
QPushButton#secondaryBtn {
    background: #161E2E;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
}
QPushButton#secondaryBtn:hover { background: #1c3146; border-color: #64748B; }
QPushButton#secondaryBtn:disabled { color: #64748B; }

/* Danger button */
QPushButton#dangerBtn {
    background: transparent;
    color: #EF4444;
    border: 1px solid #EF444430;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#dangerBtn:hover { background: #EF444418; border-color: #EF4444; color: #f87171; }
QPushButton#dangerBtn:pressed { background: #EF444420; }

/* Success button */
QPushButton#successBtn {
    background: transparent;
    color: #10B981;
    border: 1px solid #10B98130;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#successBtn:hover { background: #10B98118; border-color: #10B981; color: #34d399; }

/* Warning button */
QPushButton#warnBtn {
    background: transparent;
    color: #F59E0B;
    border: 1px solid #F59E0B30;
    border-radius: 6px;
    min-height: 28px;
    font-weight: 600;
}
QPushButton#warnBtn:hover { background: #F59E0B18; border-color: #F59E0B; color: #fbbf24; }

/* ──────────────────────────────────────────────────────────
   INPUTS — focused glowing shifts
────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: #22D3EE22;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #22D3EE;
    background-color: #0d1f2a;
}
QLineEdit::placeholder { color: #64748B; }

/* ──────────────────────────────────────────────────────────
   COMBO BOX
────────────────────────────────────────────────────────── */
QComboBox {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 14px;
    min-width: 100px;
}
QComboBox:hover { border-color: #64748B; background: #161E2E; }
QComboBox:focus { border-color: #2EC4B655; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94A3B8;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #1c3146;
    selection-color: #E5E7EB;
    outline: none;
}

/* ──────────────────────────────────────────────────────────
   SPIN BOX
────────────────────────────────────────────────────────── */
QSpinBox {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 14px;
    min-width: 60px;
}
QSpinBox:focus { border-color: #2EC4B655; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #161E2E;
    border: none;
    width: 16px;
    border-radius: 2px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #1c3146; }

/* ──────────────────────────────────────────────────────────
   GROUP BOXES
────────────────────────────────────────────────────────── */
QGroupBox {
    background: #111827;
    border: 1px solid #1c3146;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-size: 12px;
    font-weight: 700;
    color: #64748B;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #94A3B8;
    font-size: 12px;
    letter-spacing: 1.5px;
}

/* ──────────────────────────────────────────────────────────
   LABELS — 4-tier system
────────────────────────────────────────────────────────── */
QLabel#titleLabel {
    font-size: 24px;
    font-weight: 700;
    color: #E5E7EB;
    letter-spacing: 0.3px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
QLabel#sectionLabel {
    font-size: 16px;
    font-weight: 700;
    color: #E5E7EB;
}
QLabel { font-size: 14px; color: #E5E7EB; }
QLabel#metaLabel {
    font-size: 12px;
    color: #64748B;
    letter-spacing: 0.5px;
}
QLabel#dimLabel { font-size: 14px; color: #94A3B8; }

/* Semantic Status labels */
QLabel#statusOk   { color: #10B981; font-weight: 700; }
QLabel#statusBad  { color: #EF4444; font-weight: 700; }
QLabel#statusWarn { color: #F59E0B; font-weight: 700; }
QLabel#goldAccent { color: #22D3EE; font-weight: 700; font-size: 16px; }

/* ──────────────────────────────────────────────────────────
   SCROLLBARS
────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #1c3146;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #22D3EE; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 5px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #1c3146;
    border-radius: 2px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #22D3EE; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ──────────────────────────────────────────────────────────
   PROGRESS BAR — Gradient sweep chunk
────────────────────────────────────────────────────────── */
QProgressBar {
    background: #111827;
    border: none;
    border-radius: 3px;
    height: 4px;
    color: transparent;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2EC4B6, stop:1 #22D3EE);
    border-radius: 3px;
}
QProgressBar[textVisible="true"] {
    height: 20px;
    color: #94A3B8;
    font-size: 13px;
}
QProgressBar[textVisible="true"]::chunk { border-radius: 4px; }

/* ──────────────────────────────────────────────────────────
   TABLES
────────────────────────────────────────────────────────── */
QHeaderView::section {
    background: #111827;
    color: #94A3B8;
    border: none;
    border-bottom: 1px solid #1c3146;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QTableWidget {
    background: #0B1120;
    gridline-color: #1c3146;
    color: #E5E7EB;
    border: none;
    alternate-background-color: #111827;
    font-size: 14px;
    selection-background-color: #1c3146;
    selection-color: #E5E7EB;
}
QTableWidget::item { padding: 6px 12px; border: none; }
QTableWidget::item:hover { background: #161E2E; }

/* ──────────────────────────────────────────────────────────
   SPLITTERS & MISC
────────────────────────────────────────────────────────── */
QSplitter::handle { background: #1c3146; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: #64748B; }

QStatusBar {
    background: #111827;
    color: #64748B;
    border-top: 1px solid #1c3146;
    font-size: 13px;
    padding: 0 8px;
    min-height: 22px;
}
QStatusBar::item { border: none; }

QCheckBox {
    spacing: 8px;
    color: #E5E7EB;
    font-size: 14px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #1c3146;
    border-radius: 3px;
    background: #111827;
}
QCheckBox::indicator:hover { border-color: #64748B; }
QCheckBox::indicator:checked {
    background: #22D3EE;
    border-color: #22D3EE;
}

QScrollArea { background: #0B1120; border: none; }
QFrame#hline { background: #1c3146; max-height: 1px; min-height: 1px; }
QFrame#vline { background: #1c3146; max-width: 1px; min-width: 1px; }
QToolTip {
    background: #111827;
    color: #E5E7EB;
    border: 1px solid #1c3146;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}
QDialog { background: #111827; }
QMessageBox { background: #111827; }
QMessageBox QLabel { color: #E5E7EB; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

# ── Per-widget style constants ─────────────────────────────────────────
TERMINAL_STYLE = (
    "background: #071018;"
    "color: #10B981;"
    "border: 1px solid #1c3146;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 14px;"
    "selection-background-color: #22D3EE22;"
)

LOG_STYLE = (
    "background: #071018;"
    "color: #94A3B8;"
    "border: 1px solid #1c3146;"
    "border-radius: 6px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Consolas', monospace;"
    "font-size: 14px;"
)

HEADER_STYLE = "background: #111827;" "border-bottom: 1px solid #1c3146;"

SESSION_STRIP_STYLE = "background: #111827;" "border-top: 1px solid #1c3146;"

SURFACE_CARD_STYLE = (
    "background: #161E2E;" "border: 1px solid #1c3146;" "border-radius: 8px;"
)

METRIC_CARD_STYLE = (
    "background: #111827;" "border: 1px solid #1c3146;" "border-radius: 6px;"
)
