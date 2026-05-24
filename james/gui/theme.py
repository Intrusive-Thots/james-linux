"""
JAMES GUI — Elite Cyber Theme v2.

Ultra-premium hacker aesthetic with:
  - Richer colour palette (cyan / violet / amber accents)
  - Glassmorphism panels via gradients + semi-transparent borders
  - Refined typography with Inter/JetBrains Mono
  - Animated progress bar, glow effects on focus/hover
  - Dedicated named styles for every interactive element class
"""

# ── Palette constants (referenced in Python widgets too) ───────────────
PALETTE = {
    "bg_deep":    "#050810",
    "bg_panel":   "#0a0f1e",
    "bg_input":   "#0c1220",
    "bg_hover":   "#111828",
    "border":     "#16213a",
    "border_hi":  "#1e2f50",
    "cyan":       "#00e5ff",
    "cyan_dim":   "#00e5ff55",
    "cyan_glow":  "#00e5ff22",
    "violet":     "#a855f7",
    "violet_dim": "#a855f744",
    "green":      "#00ff88",
    "amber":      "#ffaa00",
    "red":        "#ff4757",
    "red_dim":    "#ff475730",
    "text":       "#c8d6e5",
    "text_dim":   "#4a6a8a",
    "text_mid":   "#7a9ab8",
}

DARK_STYLESHEET = """
/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   BASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QMainWindow, QWidget {
    background-color: #050810;
    color: #c8d6e5;
    font-family: 'Inter', 'Segoe UI', 'JetBrains Mono', 'Fira Code', sans-serif;
    font-size: 13px;
}
QWidget#centralwidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #060a18, stop:0.5 #050810, stop:1 #080c18);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   MENU BAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QMenuBar {
    background-color: #080c1a;
    color: #7a9ab8;
    border-bottom: 1px solid #16213a;
    padding: 3px 4px;
    spacing: 2px;
}
QMenuBar::item { padding: 6px 16px; border-radius: 5px; }
QMenuBar::item:selected { background: #111828; color: #00e5ff; }
QMenu {
    background-color: #0a0f1e;
    color: #c8d6e5;
    border: 1px solid #1e2f50;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 9px 28px; border-radius: 6px; margin: 2px; }
QMenu::item:selected { background: #00e5ff18; color: #00e5ff; }
QMenu::separator { height: 1px; background: #16213a; margin: 5px 10px; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   TAB BAR  — pill style
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QTabWidget::pane {
    border: 1px solid #16213a;
    border-top: none;
    background: #050810;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}
QTabBar { qproperty-drawBase: 0; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #4a6a8a;
    padding: 10px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.3px;
}
QTabBar::tab:selected {
    color: #00e5ff;
    border-bottom: 2px solid #00e5ff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #00e5ff0a, stop:1 transparent);
}
QTabBar::tab:hover:!selected {
    color: #7ab8cc;
    background: #0d1520;
    border-radius: 6px 6px 0 0;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   BUTTONS — layered variants
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #111e33, stop:1 #0c1528);
    color: #00e5ff;
    border: 1px solid #1e3558;
    border-radius: 7px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.2px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #172840, stop:1 #101e35);
    border-color: #00e5ff88;
    color: #33eeff;
}
QPushButton:pressed {
    background: #00e5ff18;
    border-color: #00e5ff;
    padding-top: 9px;
    padding-bottom: 7px;
}
QPushButton:checked {
    background: #00e5ff22;
    border-color: #00e5ff99;
    color: #00e5ff;
}
QPushButton:disabled {
    background: #080c17;
    color: #253545;
    border-color: #111828;
}

/* Primary action — glowing cyan */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #003d55, stop:1 #005570);
    border: 1px solid #00e5ff55;
    color: #00e5ff;
    font-size: 14px;
    padding: 11px 24px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00506e, stop:1 #006888);
    border-color: #00e5ffaa;
}

/* Danger — red glow */
QPushButton#dangerBtn {
    color: #ff4757;
    border-color: #ff475740;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #280d12, stop:1 #1c080d);
}
QPushButton#dangerBtn:hover {
    background: #ff475720;
    border-color: #ff4757aa;
    color: #ff6877;
}

/* Success — green */
QPushButton#successBtn {
    color: #00ff88;
    border-color: #00ff8840;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0a2a1c, stop:1 #071e14);
}
QPushButton#successBtn:hover {
    background: #00ff8820;
    border-color: #00ff88aa;
}

/* Warning — amber */
QPushButton#warnBtn {
    color: #ffaa00;
    border-color: #ffaa0040;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a1f00, stop:1 #1c1500);
}
QPushButton#warnBtn:hover {
    background: #ffaa0020;
    border-color: #ffaa00aa;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #0c1220;
    color: #00ff88;
    border: 1px solid #16213a;
    border-radius: 7px;
    padding: 8px 12px;
    selection-background-color: #00e5ff33;
    selection-color: #ffffff;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #00e5ff55;
    background: #0e1525;
}
QLineEdit::placeholder { color: #1e3545; }

/* ── Chat input override ── */
QLineEdit#chatInput {
    background: #0d1628;
    color: #c8d6e5;
    border: 1px solid #1e2f50;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
QLineEdit#chatInput:focus { border-color: #00e5ff66; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   COMBO BOX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QComboBox {
    background: #0c1525;
    color: #c8d6e5;
    border: 1px solid #1e3558;
    border-radius: 7px;
    padding: 7px 12px;
    min-width: 100px;
}
QComboBox:hover { border-color: #00e5ff55; background: #0e1a2e; }
QComboBox:focus { border-color: #00e5ff77; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #4a6a8a;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #0a0f1e;
    color: #c8d6e5;
    selection-background-color: #00e5ff22;
    selection-color: #00e5ff;
    border: 1px solid #1e3558;
    border-radius: 8px;
    padding: 4px;
    outline: 0;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SPIN BOX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QSpinBox {
    background: #0c1220;
    color: #c8d6e5;
    border: 1px solid #16213a;
    border-radius: 7px;
    padding: 6px 10px;
    min-width: 60px;
}
QSpinBox:focus { border-color: #00e5ff55; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #111828;
    border: none;
    width: 18px;
    border-radius: 3px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #1a2840;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   GROUP BOXES — glassmorphism panels
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QGroupBox {
    border: 1px solid #16213a;
    border-radius: 12px;
    margin-top: 18px;
    padding: 18px 14px 14px 14px;
    font-weight: 700;
    font-size: 11px;
    color: #4a7a9a;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0c1020, stop:1 #080c18);
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: #00e5ff99;
    font-size: 10px;
    letter-spacing: 2px;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   LABELS — semantic variants
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QLabel#headerLabel {
    font-size: 22px;
    font-weight: 800;
    color: #00e5ff;
    letter-spacing: 3px;
    font-family: 'JetBrains Mono', monospace;
}
QLabel#subHeader {
    font-size: 11px;
    color: #4a6a8a;
    letter-spacing: 2px;
    font-weight: 500;
}
QLabel#statusOk  { color: #00ff88; font-weight: 700; }
QLabel#statusBad { color: #ff4757; font-weight: 700; }
QLabel#statusWarn { color: #ffaa00; font-weight: 700; }
QLabel#sectionLabel {
    font-size: 14px;
    font-weight: 700;
    color: #00e5ff;
    padding: 6px 0;
    letter-spacing: 0.5px;
}
QLabel#lootKey {
    color: #00ff88;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: bold;
}
QLabel#dimLabel { color: #4a6a8a; font-size: 11px; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SCROLLBARS — ultra slim
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1a2940;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #00e5ff44; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #1a2940;
    border-radius: 3px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #00e5ff44; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PROGRESS BAR — animated gradient
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QProgressBar {
    background: #0c1220;
    border: 1px solid #16213a;
    border-radius: 8px;
    text-align: center;
    color: #7a9ab8;
    font-size: 11px;
    font-weight: 600;
    height: 22px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00e5ff, stop:0.4 #00b4ff, stop:0.7 #a855f7, stop:1 #00ff88);
    border-radius: 7px;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QHeaderView::section {
    background: #0a0f1e;
    color: #00e5ff88;
    border: none;
    border-bottom: 1px solid #16213a;
    border-right: 1px solid #0d1528;
    padding: 9px 12px;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QTableWidget {
    background: #050810;
    gridline-color: #0d1528;
    color: #c8d6e5;
    border: none;
    alternate-background-color: #080c18;
    border-radius: 8px;
}
QTableWidget::item { padding: 5px 10px; border: none; }
QTableWidget::item:selected {
    background: #00e5ff18;
    color: #ffffff;
}
QTableWidget::item:hover { background: #0d1828; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SPLITTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QSplitter::handle { background: #16213a; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: #00e5ff44; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STATUS BAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QStatusBar {
    background: #080c1a;
    color: #3a5a7a;
    border-top: 1px solid #16213a;
    font-size: 11px;
    padding: 3px 10px;
}
QStatusBar::item { border: none; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SCROLL AREA / FRAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QScrollArea { background: #050810; border: none; }
QFrame#separator {
    background: #16213a;
    max-height: 1px;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   TOOLTIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QToolTip {
    background: #0a0f1e;
    color: #c8d6e5;
    border: 1px solid #1e3558;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 12px;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   MESSAGE BOX / DIALOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
QDialog { background: #080c1a; }
QMessageBox { background: #080c1a; }
QMessageBox QLabel { color: #c8d6e5; font-size: 13px; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

# ── Per-widget style snippets ──────────────────────────────────────────
TERMINAL_STYLE = (
    "background: #030508;"
    "color: #00ff88;"
    "border: 1px solid #0e1a2e;"
    "border-radius: 8px;"
    "padding: 8px;"
    "font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;"
    "font-size: 12px;"
    "selection-background-color: #00e5ff33;"
)

LOG_STYLE = (
    "background: #040710;"
    "color: #00cc66;"
    "border: 1px solid #0e1a2e;"
    "border-radius: 8px;"
    "padding: 6px;"
    "font-family: 'JetBrains Mono', monospace;"
    "font-size: 11px;"
)

HEADER_GRADIENT = (
    "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
    "stop:0 #050810, stop:0.4 #080c18, stop:1 #050810);"
    "border-bottom: 1px solid #16213a;"
    "padding: 12px 16px;"
)
