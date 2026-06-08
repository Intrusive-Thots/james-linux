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
        self.assertIn("Ctrl+6", keys)
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

    def test_tab_refocus(self):
        import unittest.mock as mock

        self.window.tabs.setCurrentIndex(0)
        self.assertEqual(self.window.tabs.currentIndex(), 0)

        # Mock _on_tab_changed to verify it is called when switching to the same tab
        with mock.patch.object(
            self.window, "_on_tab_changed"
        ) as mock_on_tab_changed:
            self.window._switch_tab(0)
            mock_on_tab_changed.assert_called_once_with(0)

        # Verify it still changes tab if different
        self.window._switch_tab(1)
        self.assertEqual(self.window.tabs.currentIndex(), 1)

    def test_escape_key_clears_input(self):
        from james.gui.chat_panel import _HistoryLineEdit
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QKeyEvent

        line_edit = _HistoryLineEdit([])
        line_edit.setText("some text")
        self.assertEqual(line_edit.text(), "some text")

        # Synthesize escape key press
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        line_edit.keyPressEvent(event)

        # Verify text is cleared
        self.assertEqual(line_edit.text(), "")

    def test_history_cursor_position(self):
        from james.gui.chat_panel import _HistoryLineEdit
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QKeyEvent

        history = ["cmd1", "cmd2"]
        line_edit = _HistoryLineEdit(history)

        # Ensure the widget receives focus and is somewhat active for cursor positioning
        line_edit.show()

        # Up arrow -> loads "cmd2"
        event_up = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Up, Qt.NoModifier)
        line_edit.keyPressEvent(event_up)

        self.assertEqual(line_edit.text(), "cmd2")
        self.assertEqual(line_edit.cursorPosition(), len("cmd2"))

        # Up arrow -> loads "cmd1"
        line_edit.keyPressEvent(event_up)
        self.assertEqual(line_edit.text(), "cmd1")
        self.assertEqual(line_edit.cursorPosition(), len("cmd1"))

        # Down arrow -> loads "cmd2" again
        event_down = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Down, Qt.NoModifier)
        line_edit.keyPressEvent(event_down)
        self.assertEqual(line_edit.text(), "cmd2")
        self.assertEqual(line_edit.cursorPosition(), len("cmd2"))

        line_edit.close()

    def test_wifi_tab_shortcuts(self):
        # The WiFi tab is a child of the window. Let's find shortcuts defined directly in the tab.
        shortcuts = self.window.wifi_tab.findChildren(QShortcut)
        keys = [s.key().toString() for s in shortcuts]

        # Verify WiFiArsenalTab specific shortcuts are present
        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+R") for s in shortcuts)
        )
        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+S") for s in shortcuts)
        )
        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+C") for s in shortcuts)
        )

    def test_troubleshoot_tab_shortcuts(self):
        from james.gui.tabs.troubleshoot_tab import TroubleshootTab
        troubleshoot_tab = next(
            (
                self.window.tabs.widget(i)
                for i in range(self.window.tabs.count())
                if isinstance(self.window.tabs.widget(i), TroubleshootTab)
            ),
            None,
        )
        self.assertIsNotNone(troubleshoot_tab, "TroubleshootTab not found")

        shortcuts = troubleshoot_tab.findChildren(QShortcut)

        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+R") for s in shortcuts),
            "Ctrl+R shortcut not found in TroubleshootTab"
        )
        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+I") for s in shortcuts),
            "Ctrl+I shortcut not found in TroubleshootTab"
        )

    def test_chat_ctrl_enter(self):
        from james.gui.chat_panel import ChatPanel

        chat_panel = self.window.chat_panel
        shortcuts = chat_panel.findChildren(QShortcut)

        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+Return") for s in shortcuts),
            "Ctrl+Return shortcut not found in ChatPanel input"
        )

        self.assertTrue(
            any(s.key() == QKeySequence("Ctrl+L") for s in shortcuts),
            "Ctrl+L shortcut not found in ChatPanel"
        )

    def test_log_scroll_anim(self):
        from PyQt5.QtCore import QPropertyAnimation

        self.window._on_log_received("test log", "INFO")

        # Verify that the animation object was created and is running
        self.assertTrue(hasattr(self.window, "_log_scroll_anim"))
        anim = self.window._log_scroll_anim
        self.assertIsInstance(anim, QPropertyAnimation)
        self.assertEqual(anim.targetObject(), self.window.terminal.verticalScrollBar())
        self.assertEqual(anim.propertyName(), b"value")

    def test_chat_scroll_anim(self):
        from PyQt5.QtCore import QPropertyAnimation

        chat_panel = self.window.chat_panel
        chat_panel._scroll_to_bottom()

        self.assertTrue(hasattr(chat_panel, "_scroll_anim"))
        anim = chat_panel._scroll_anim
        self.assertIsNotNone(anim)
        self.assertIsInstance(anim, QPropertyAnimation)
        self.assertEqual(anim.targetObject(), chat_panel._scroll.verticalScrollBar())
        self.assertEqual(anim.propertyName(), b"value")

    def test_chat_bubble_fade_anim(self):
        from james.gui.chat_panel import _Bubble
        from PyQt5.QtCore import QPropertyAnimation
        from PyQt5.QtWidgets import QGraphicsOpacityEffect

        bubble = _Bubble("Test fade animation", False)

        # Verify opacity effect is applied
        self.assertTrue(hasattr(bubble, "_opacity"))
        self.assertIsInstance(bubble._opacity, QGraphicsOpacityEffect)
        self.assertEqual(bubble.graphicsEffect(), bubble._opacity)

        # Verify fade animation is configured correctly
        self.assertTrue(hasattr(bubble, "_fade_anim"))
        anim = bubble._fade_anim
        self.assertIsInstance(anim, QPropertyAnimation)
        self.assertEqual(anim.targetObject(), bubble._opacity)
        self.assertEqual(anim.propertyName(), b"opacity")
        self.assertEqual(anim.startValue(), 0.0)
        self.assertEqual(anim.endValue(), 1.0)


if __name__ == "__main__":
    unittest.main()
