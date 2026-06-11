import unittest
import sys
from PyQt5.QtWidgets import QApplication
from james.remote.gui_remote import GUIRemote

class TestGUIRemote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prevent "Must construct a QApplication before a QWidget" error
        cls.app = QApplication(sys.argv)

    def test_is_running_initial_state(self):
        remote = GUIRemote()
        self.assertFalse(remote.is_running())

    def test_is_running_when_running(self):
        remote = GUIRemote()
        remote.running = True
        self.assertTrue(remote.is_running())

    def test_is_running_when_stopped(self):
        remote = GUIRemote()
        remote.running = True
        remote.running = False
        self.assertFalse(remote.is_running())

if __name__ == '__main__':
    unittest.main()
