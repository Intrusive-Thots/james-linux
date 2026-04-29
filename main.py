#!/usr/bin/env python3
"""
JAMES Linux — Application Entry Point.

Launch the PyQt5 desktop agent.
"""

import sys
import logging

from PyQt5.QtWidgets import QApplication

from james.gui.main_window import MainWindow
from james.gui.theme import DARK_STYLESHEET


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("JAMES Linux")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
