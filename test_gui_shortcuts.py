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
        self.assertIn("Ctrl+Tab", keys)
        self.assertIn("Ctrl+Shift+Tab", keys)

    def test_tab_cycling(self):
        # Initial tab is 0
        self.window.tabs.setCurrentIndex(0)
        self.assertEqual(self.window.tabs.currentIndex(), 0)

        # Test _next_tab wrapping
        count = self.window.tabs.count()
        self.assertTrue(count > 0, "There should be at least one tab")

        self.window.tabs.setCurrentIndex(count - 1)
        self.window._next_tab()
        self.assertEqual(self.window.tabs.currentIndex(), 0)

        # Test _prev_tab wrapping
        self.window.tabs.setCurrentIndex(0)
        self.window._prev_tab()
        self.assertEqual(self.window.tabs.currentIndex(), count - 1)

        # Test basic cycling
        self.window.tabs.setCurrentIndex(1)
        self.window._next_tab()
        self.assertEqual(self.window.tabs.currentIndex(), 2 % count)
        self.window._prev_tab()
        self.assertEqual(self.window.tabs.currentIndex(), 1)

    def test_wifi_tab_shortcuts(self):
        # The WiFi tab is a child of the window. Let's find shortcuts defined directly in the tab.
        shortcuts = self.window.wifi_tab.findChildren(QShortcut)
        keys = [s.key().toString() for s in shortcuts]

        # Verify WiFiArsenalTab specific shortcuts are present
        self.assertTrue(any(s.key() == QKeySequence("Ctrl+R") for s in shortcuts))
        self.assertTrue(any(s.key() == QKeySequence("Ctrl+S") for s in shortcuts))
        self.assertTrue(any(s.key() == QKeySequence("Ctrl+C") for s in shortcuts))

if __name__ == "__main__":
    unittest.main()
