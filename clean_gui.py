import re

with open("james/gui/main_window.py", "r") as f:
    content = f.read()

# 1. Remove context badge strip creation
content = content.replace(
    """        # context badge strip
        self.ctx_strip = self._make_context_strip()
        root.addWidget(self.ctx_strip)\n""",
    "",
)

# 2. Simplify tabs
tabs_old = """        agent_tab = self._make_agent_tab()
        self.tabs.addTab(agent_tab, "🤖 Agent")
        self.tabs.setTabToolTip(0, "Conversational AI — talk to JAMES in plain English")

        self.tabs.addTab(self._make_dashboard_tab(), "⚡ Dashboard")
        self.tabs.setTabToolTip(1, "System status + interactive terminal")

        self.tabs.addTab(self._make_oneclick_tab(), "🧪 Skills")
        self.tabs.setTabToolTip(2, "Browse and run automated skill workflows")

        self.tabs.addTab(self._make_recon_tab(), "🔍 Recon")
        self.tabs.setTabToolTip(3, "nmap scanning — quick and full port scans")

        self.tabs.addTab(self._make_wifi_tab(), "📡 Wi-Fi")
        self.tabs.setTabToolTip(4, "Wi-Fi auditing — monitor mode, deauth, AutoPwn")

        self.tabs.addTab(self._make_cracking_tab(), "🔓 Cracking")
        self.tabs.setTabToolTip(5, "WPA handshake + hash cracking")

        self.tabs.addTab(self._make_log_tab(), "📋 Log")
        self.tabs.setTabToolTip(6, "Task history and JSON export")"""

tabs_new = """        self.tabs.addTab(self.chat_panel, "🤖 Agent")
        self.tabs.setTabToolTip(0, "Conversational AI — talk to JAMES in plain English")

        self.tabs.addTab(self._make_dashboard_tab(), "⚡ Dashboard")
        self.tabs.setTabToolTip(1, "System status + interactive terminal")

        self.tabs.addTab(self._make_oneclick_tab(), "🧪 Skills")
        self.tabs.setTabToolTip(2, "Browse and run automated skill workflows")

        self.tabs.addTab(self._make_log_tab(), "📋 Log")
        self.tabs.setTabToolTip(3, "Task history and JSON export")"""

content = content.replace(tabs_old, tabs_new)

# 3. Remove context timer
timer_old = """        # Refresh context badges every 5 seconds
        self._ctx_timer = QTimer(self)
        self._ctx_timer.timeout.connect(self._refresh_context_strip)
        self._ctx_timer.start(5000)\n"""
content = content.replace(timer_old, "")

# 4. Remove initial interface refresh
init_old = """        # initial system check and load interfaces
        QTimer.singleShot(300, self._run_system_check)
        QTimer.singleShot(400, self._refresh_interfaces)"""
init_new = """        # initial system check
        QTimer.singleShot(300, self._run_system_check)"""
content = content.replace(init_old, init_new)

# 5. Remove timer stops in closeEvent
close_old = """        # Stop timers
        self._ctx_timer.stop()
        self._clock_timer.stop()"""
close_new = """        # Stop timers
        self._clock_timer.stop()"""
content = content.replace(close_old, close_new)

# 6. Remove timer starts in _on_kill_complete
kill_old = """        self._restore_kill_btn()
        # Refresh the interface list
        QTimer.singleShot(3000, self._refresh_interfaces)"""
kill_new = """        self._restore_kill_btn()"""
content = content.replace(kill_old, kill_new)

# 7. Remove timer starts in _on_reboot_complete
reboot_old = """        self._term_print(f"[SYS] {len(self.known_targets)} saved targets preserved.")

        # Refresh interfaces
        QTimer.singleShot(1000, self._refresh_interfaces)

        # Refresh context strip
        self._refresh_context_strip()

        # Restore button"""
reboot_new = """        self._term_print(f"[SYS] {len(self.known_targets)} saved targets preserved.")

        # Restore button"""
content = content.replace(reboot_old, reboot_new)

with open("james/gui/main_window.py", "w") as f:
    f.write(content)
