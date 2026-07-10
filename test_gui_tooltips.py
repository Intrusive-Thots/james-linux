import sys
import unittest
from PyQt5.QtWidgets import QApplication

# Create a global application instance
app = QApplication(sys.argv)

from james.gui.main_window import MainWindow
from james.gui.tabs.wifi_tab import WiFiArsenalTab
from james.core.orchestrator import Orchestrator


class TestGUITooltips(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()
        self.main_window = MainWindow(self.orchestrator)
        self.wifi_tab = WiFiArsenalTab(self.main_window)

    def tearDown(self):
        self.main_window.close()
        self.wifi_tab.close()

    def test_main_window_tooltips(self):
        self.assertEqual(self.main_window.tabs.tabToolTip(0), "Conversational AI (Ctrl+1)")
        self.assertEqual(self.main_window.tabs.tabToolTip(1), "Wi-Fi auditing and tools (Ctrl+2)")
        self.assertEqual(self.main_window.tabs.tabToolTip(2), "Automated routines (Ctrl+3)")
        self.assertEqual(self.main_window.tabs.tabToolTip(3), "Evil Twin pipeline (Ctrl+4)")
        self.assertEqual(self.main_window.tabs.tabToolTip(4), "Experimental wireless assessments (Ctrl+5)")
        self.assertEqual(self.main_window.tabs.tabToolTip(5), "System configuration and diagnostics (Ctrl+6)")

        self.assertEqual(
            self.main_window._btn_logs.toolTip(), "View log files (Ctrl+L)"
        )
        self.assertEqual(
            self.main_window._btn_power.toolTip(),
            "Restart, stop, or reboot",
        )

        # To get the dynamically created buttons we need to search for them or find them by text/properties
        # But for copy/clear they are not stored as instance attributes. Let's find them from layout.
        from PyQt5.QtWidgets import QPushButton

        buttons = self.main_window.findChildren(QPushButton)
        copy_btn = next((b for b in buttons if b.text() == "Copy"), None)
        clear_btn = next((b for b in buttons if b.text() == "Clear"), None)

        self.assertIsNotNone(copy_btn, "Copy button not found")
        self.assertEqual(
            copy_btn.toolTip(), "Copy terminal output to clipboard (Ctrl+C)"
        )

        self.assertIsNotNone(clear_btn, "Clear button not found")
        self.assertEqual(
            clear_btn.toolTip(), "Clear terminal output (Ctrl+Shift+C)"
        )

    def test_wifi_tab_tooltips(self):
        self.assertEqual(
            self.wifi_tab.btn_hw_info.toolTip(),
            "Show hardware info for the selected interface (Ctrl+H)",
        )
        self.assertEqual(
            self.wifi_tab.btn_monitor_on.toolTip(),
            "Enable monitor mode on the selected interface (Ctrl+M)",
        )
        self.assertEqual(
            self.wifi_tab.btn_monitor_off.toolTip(),
            "Disable monitor mode on the selected interface (Ctrl+M)",
        )
        self.assertEqual(
            self.wifi_tab.btn_refresh.toolTip(),
            "Refresh network interfaces (Ctrl+R)",
        )
        self.assertEqual(
            self.wifi_tab.btn_start_scan.toolTip(),
            "Scan for nearby Wi-Fi networks (Ctrl+S)",
        )
        self.assertEqual(
            self.wifi_tab.btn_stop_scan.toolTip(),
            "Stop ongoing Wi-Fi scan (Ctrl+S)",
        )
        self.assertEqual(
            self.wifi_tab.btn_airgeddon.toolTip(),
            "Launch Evil Twin attack pipeline",
        )
        self.assertEqual(
            self.wifi_tab.btn_airgeddon_stop.toolTip(),
            "Stop Evil Twin pipeline",
        )

    def test_chat_panel_tooltips(self):
        from james.gui.chat_panel import ChatPanel

        chat_panel = self.main_window.tabs.widget(0)
        self.assertIsInstance(chat_panel, ChatPanel)
        self.assertEqual(chat_panel._btn_clear.toolTip(), "Clear chat history (Ctrl+L)")
        self.assertEqual(chat_panel._btn_send.toolTip(), "Send command to JAMES (Ctrl+Return)")

    def test_troubleshoot_tab_tooltips(self):
        from james.gui.tabs.troubleshoot_tab import TroubleshootTab
        # TroubleshootTab is now nested inside the Config tab's sub-tabs
        troubleshoot_tab = None
        for w in self.main_window.findChildren(TroubleshootTab):
            troubleshoot_tab = w
            break
        self.assertIsNotNone(troubleshoot_tab, "TroubleshootTab not found")

        self.assertEqual(
            troubleshoot_tab.btn_check_deps.toolTip(),
            "Check all dependencies (Ctrl+R)",
        )
        self.assertEqual(
            troubleshoot_tab.btn_install_deps.toolTip(),
            "Auto-install missing dependencies (Ctrl+I)",
        )


    def test_airgeddon_tab_tooltips(self):
        from james.gui.tabs.airgeddon_tab import AirgeddonTab
        tab = next(
            (
                self.main_window.tabs.widget(i)
                for i in range(self.main_window.tabs.count())
                if isinstance(self.main_window.tabs.widget(i), AirgeddonTab)
            ),
            None,
        )
        self.assertIsNotNone(tab, "AirgeddonTab not found")
        self.assertEqual(tab.btn_refresh.toolTip(), "Refresh network interfaces (Ctrl+R)")
        self.assertEqual(tab.btn_scan_start.toolTip(), "Start network scan (Ctrl+S)")
        self.assertEqual(tab.btn_scan_stop.toolTip(), "Stop network scan (Ctrl+S)")

    def test_autopilot_tab_tooltips(self):
        from james.gui.tabs.autopilot_tab import AutoPilotTab
        tab = next(
            (
                self.main_window.tabs.widget(i)
                for i in range(self.main_window.tabs.count())
                if isinstance(self.main_window.tabs.widget(i), AutoPilotTab)
            ),
            None,
        )
        self.assertIsNotNone(tab, "AutoPilotTab not found")
        self.assertEqual(tab.btn_start.toolTip(), "Start full Auto-Pilot (Ctrl+S)")
        self.assertEqual(tab.btn_stop.toolTip(), "Abort Auto-Pilot (Ctrl+S)")

    def test_setup_tab_tooltips(self):
        from james.gui.tabs.setup_tab import SetupTab
        setup_tab = None
        for w in self.main_window.findChildren(SetupTab):
            setup_tab = w
            break
        self.assertIsNotNone(setup_tab, "SetupTab not found")

        self.assertEqual(
            setup_tab.btn_bridge.toolTip(),
            "Bridge networks (Ctrl+B)",
        )
        self.assertEqual(
            setup_tab.btn_restart_nm.toolTip(),
            "Restart NetworkManager (Ctrl+R)",
        )
        self.assertEqual(
            setup_tab.btn_flush_iptables.toolTip(),
            "Flush iptables (Ctrl+F)",
        )

if __name__ == "__main__":
    unittest.main()
