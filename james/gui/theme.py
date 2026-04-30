"""
JAMES GUI — Premium Dark Cyber Theme.

Ultra-polished dark hacker aesthetic with refined gradients,
glassmorphism accents, and smooth micro-animations.
"""

DARK_STYLESHEET = """
/* ── Base ────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #080c14;
    color: #c8d6e5;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
}

/* ── Menu Bar ────────────────────────────────────────────── */
QMenuBar {
    background-color: #0b1120;
    color: #8899aa;
    border-bottom: 1px solid #141e30;
    padding: 2px 0;
}
QMenuBar::item { padding: 6px 14px; border-radius: 4px; margin: 2px; }
QMenuBar::item:selected { background-color: #141e30; color: #00f0ff; }
QMenu {
    background-color: #0b1120;
    color: #c8d6e5;
    border: 1px solid #1a2940;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { padding: 8px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #00f0ff18; color: #00f0ff; }
QMenu::separator { height: 1px; background: #1a2940; margin: 4px 8px; }

/* ── Tabs ────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background-color: #080c14;
    border-top: 1px solid #141e30;
}
QTabBar {
    qproperty-drawBase: 0;
}
QTabBar::tab {
    background-color: #0b1120;
    color: #4a6a8a;
    padding: 10px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
    font-weight: 600;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #080c14;
    color: #00f0ff;
    border-bottom: 2px solid #00f0ff;
}
QTabBar::tab:hover:!selected {
    color: #6aaabe;
    background-color: #0d1520;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    background-color: #101a2c;
    color: #00f0ff;
    border: 1px solid #1a3050;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #142540;
    border-color: #00f0ff80;
}
QPushButton:pressed {
    background-color: #00f0ff18;
    border-color: #00f0ff;
}
QPushButton:disabled {
    background-color: #0a0e17;
    color: #2a3a4a;
    border-color: #141e30;
}
QPushButton#dangerBtn {
    color: #ff4757;
    border-color: #ff475740;
}
QPushButton#dangerBtn:hover {
    background-color: #ff475718;
    border-color: #ff4757;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0b1120;
    color: #00ff88;
    border: 1px solid #141e30;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #00f0ff33;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #00f0ff60;
}
QLineEdit::placeholder {
    color: #2a4a5a;
}

/* ── Combo ───────────────────────────────────────────────── */
QComboBox {
    background-color: #101a2c;
    color: #c8d6e5;
    border: 1px solid #1a3050;
    border-radius: 6px;
    padding: 7px 10px;
    min-width: 100px;
}
QComboBox:hover { border-color: #00f0ff60; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #4a6a8a;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #0b1120;
    color: #c8d6e5;
    selection-background-color: #00f0ff22;
    selection-color: #00f0ff;
    border: 1px solid #1a3050;
    border-radius: 6px;
    padding: 4px;
    outline: 0;
}

/* ── Group Boxes ─────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #141e30;
    border-radius: 10px;
    margin-top: 14px;
    padding: 20px 12px 12px 12px;
    font-weight: bold;
    color: #00f0ff;
    background-color: #0a0f1a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #00f0ff;
    font-size: 13px;
}

/* ── Named Labels ────────────────────────────────────────── */
QLabel#headerLabel {
    font-size: 22px;
    font-weight: bold;
    color: #00f0ff;
    letter-spacing: 2px;
}
QLabel#statusOk { color: #00ff88; font-weight: bold; }
QLabel#statusBad { color: #ff4757; font-weight: bold; }
QLabel#sectionLabel {
    font-size: 15px;
    font-weight: bold;
    color: #00f0ff;
    padding: 6px 0;
}

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #080c14;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #1a2940;
    border-radius: 4px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover { background-color: #00f0ff44; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #080c14;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background-color: #1a2940;
    border-radius: 4px;
    min-width: 40px;
}
QScrollBar::handle:horizontal:hover { background-color: #00f0ff44; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Progress Bar ────────────────────────────────────────── */
QProgressBar {
    background-color: #0b1120;
    border: 1px solid #141e30;
    border-radius: 6px;
    text-align: center;
    color: #c8d6e5;
    height: 20px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00f0ff, stop:0.5 #00d4ff, stop:1 #00ff88);
    border-radius: 5px;
}

/* ── Splitters ───────────────────────────────────────────── */
QSplitter::handle {
    background-color: #141e30;
    width: 2px;
}

/* ── Table ───────────────────────────────────────────────── */
QHeaderView::section {
    background-color: #0b1120;
    color: #00f0ff;
    border: none;
    border-bottom: 2px solid #141e30;
    border-right: 1px solid #141e30;
    padding: 8px 10px;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QTableWidget {
    background-color: #080c14;
    gridline-color: #0f1520;
    color: #c8d6e5;
    border: none;
    alternate-background-color: #0a0f18;
}
QTableWidget::item { padding: 4px 8px; }
QTableWidget::item:selected {
    background-color: #00f0ff18;
    color: #ffffff;
}
QTableWidget::item:hover {
    background-color: #0d1a28;
}

/* ── Status Bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #0b1120;
    color: #4a6a8a;
    border-top: 1px solid #141e30;
    font-size: 11px;
    padding: 2px 8px;
}
QStatusBar::item { border: none; }

/* ── Scroll Area ─────────────────────────────────────────── */
QScrollArea {
    background-color: #080c14;
    border: none;
}

/* ── Tooltip ─────────────────────────────────────────────── */
QToolTip {
    background-color: #0b1120;
    color: #c8d6e5;
    border: 1px solid #1a3050;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Message Box ─────────────────────────────────────────── */
QMessageBox {
    background-color: #0b1120;
}
QMessageBox QLabel {
    color: #c8d6e5;
}
"""
