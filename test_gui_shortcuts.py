import sys
import unittest
from PyQt5.QtWidgets import QApplication, QShortcut
from PyQt5.QtGui import QKeySequence

# Create a global application instance
app = QApplication(sys.argv)

from james.gui.main_window import MainWindow
from james.core.orchestrator import Orchestrator

class TestMainWindowShortcuts(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()
        self.window = MainWindow(self.orchestrator)

    def tearDown(self):
        self.window.close()

    def test_shortcuts_exist(self):
        shortcuts = self.window.findChildren(QShortcut)
        keys = [s.key().toString() for s in shortcuts]

        # Verify required shortcuts are present
        self.assertIn("Ctrl+Q", keys)
        self.assertIn("Ctrl+L", keys)
        self.assertIn("Ctrl+Shift+C", keys)
        self.assertIn("Ctrl+K", keys)
        self.assertIn("Ctrl+1", keys)
        self.assertIn("Ctrl+2", keys)
        self.assertIn("Ctrl+3", keys)
        self.assertIn("Ctrl+4", keys)
        self.assertIn("Ctrl+5", keys)

if __name__ == "__main__":
    unittest.main()
