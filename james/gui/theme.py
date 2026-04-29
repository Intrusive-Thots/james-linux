"""Dark hacker theme stylesheet for JAMES GUI."""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0a0e17;
    color: #c8d6e5;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
}
QMenuBar {
    background-color: #0f1923;
    color: #c8d6e5;
    border-bottom: 1px solid #1a2940;
}
QMenuBar::item:selected { background-color: #1a2940; }
QMenu {
    background-color: #0f1923;
    color: #c8d6e5;
    border: 1px solid #1a2940;
}
QMenu::item:selected { background-color: #00f0ff22; color: #00f0ff; }
QTabWidget::pane {
    border: 1px solid #1a2940;
    background-color: #0a0e17;
}
QTabBar::tab {
    background-color: #0f1923;
    color: #5a7a9a;
    padding: 8px 20px;
    border: 1px solid #1a2940;
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0a0e17;
    color: #00f0ff;
    border-top: 2px solid #00f0ff;
}
QTabBar::tab:hover { color: #00f0ff; }
QPushButton {
    background-color: #1a2940;
    color: #00f0ff;
    border: 1px solid #00f0ff44;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #00f0ff22;
    border-color: #00f0ff;
}
QPushButton:pressed { background-color: #00f0ff33; }
QPushButton#dangerBtn {
    color: #ff4757;
    border-color: #ff475744;
}
QPushButton#dangerBtn:hover {
    background-color: #ff475722;
    border-color: #ff4757;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f1923;
    color: #00ff88;
    border: 1px solid #1a2940;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #00f0ff44;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #00f0ff;
}
QComboBox {
    background-color: #1a2940;
    color: #c8d6e5;
    border: 1px solid #1a2940;
    border-radius: 4px;
    padding: 6px;
}
QComboBox:hover { border-color: #00f0ff; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #0f1923;
    color: #c8d6e5;
    selection-background-color: #00f0ff33;
}
QGroupBox {
    border: 1px solid #1a2940;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #00f0ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLabel#headerLabel {
    font-size: 22px;
    font-weight: bold;
    color: #00f0ff;
}
QLabel#statusOk { color: #00ff88; }
QLabel#statusBad { color: #ff4757; }
QLabel#sectionLabel {
    font-size: 15px;
    font-weight: bold;
    color: #00f0ff;
    padding: 4px 0;
}
QScrollBar:vertical {
    background-color: #0a0e17;
    width: 10px;
}
QScrollBar::handle:vertical {
    background-color: #1a2940;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #00f0ff44; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QProgressBar {
    background-color: #0f1923;
    border: 1px solid #1a2940;
    border-radius: 4px;
    text-align: center;
    color: #c8d6e5;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00f0ff, stop:1 #00ff88);
    border-radius: 3px;
}
QSplitter::handle { background-color: #1a2940; }
QHeaderView::section {
    background-color: #0f1923;
    color: #00f0ff;
    border: 1px solid #1a2940;
    padding: 4px;
}
QTableWidget {
    background-color: #0a0e17;
    gridline-color: #1a2940;
    color: #c8d6e5;
}
QTableWidget::item:selected { background-color: #00f0ff22; }
"""
