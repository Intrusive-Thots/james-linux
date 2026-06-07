import unittest
from unittest.mock import patch
from pathlib import Path
from james.core.report import save_report, generate_html_report


class TestReport(unittest.TestCase):

    def test_generate_html_report_empty(self):
        html = generate_html_report(
            task_log=[],
            context={},
            loot_summary={},
            tool_status={},
            skills=[],
            known_targets=set(),
            wordlist_inventory=[]
        )
        self.assertIn("JAMES", html)
        self.assertIn("PENETRATION TEST REPORT", html)
        self.assertIn("Tasks Executed", html)
        self.assertIn("Session Context", html) # The HTML comment <!-- Session Context --> is always generated
        # Verify that the conditionally rendered parts are NOT present in the empty report
        self.assertNotIn("🎯 Session Context", html)
        self.assertNotIn("🎯 Discovered Targets (", html)
        self.assertNotIn("🔑 Cracked Credentials (", html)
        self.assertIn("No tasks recorded in this session.", html)

    def test_generate_html_report_full(self):
        html = generate_html_report(
            task_log=[
                {"status": "success", "timestamp": "2023-10-10", "action": "scan", "tool": "nmap", "result": {"foo": "bar"}},
                {"status": "error", "timestamp": "2023-10-10", "action": "crack", "tool": "hashcat"}
            ],
            context={"TARGET": "192.168.1.1", "IFACE": "wlan0"},
            loot_summary={"cracked_count": 1, "keys": [{"essid": "HomeWiFi", "key": "password123", "method": "WPA", "when": "2023-10-10"}]},
            tool_status={"nmap": True, "aircrack-ng": False},
            skills=["network_discovery", "wifi_attacks"],
            known_targets={"192.168.1.1", "192.168.1.2"},
            wordlist_inventory=[{"name": "rockyou.txt"}]
        )
        self.assertIn("192.168.1.1", html)
        self.assertIn("wlan0", html)
        self.assertIn("HomeWiFi", html)
        self.assertIn("password123", html)
        self.assertIn("nmap", html)
        self.assertIn("Session Context", html)
        self.assertIn("Discovered Targets (2)", html)
        self.assertIn("Cracked Credentials (1)", html)
        self.assertIn("error", html)

    @patch.object(Path, "write_text")
    @patch.object(Path, "mkdir")
    def test_save_report_with_custom_path(self, mock_mkdir, mock_write_text):
        html_content = "<html><body>Report</body></html>"
        custom_path = "/tmp/custom_report.html"

        result = save_report(html_content, path=custom_path)

        self.assertEqual(result, Path(custom_path))
        mock_write_text.assert_called_once_with(html_content, encoding="utf-8")
        mock_mkdir.assert_not_called()

    @patch("james.core.report.datetime")
    @patch.object(Path, "home")
    def test_save_report_with_default_path(
        self, mock_home, mock_datetime
    ):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_home.return_value = tmp_path
            mock_datetime.now.return_value.strftime.return_value = (
                "20231010_120000"
            )

            html_content = "<html><body>Report</body></html>"

            result = save_report(html_content)

            expected_path = (
                tmp_path / ".james" / "loot" / "report_20231010_120000.html"
            )
            self.assertEqual(result, expected_path)
            self.assertTrue(expected_path.exists())
            self.assertEqual(expected_path.read_text(encoding="utf-8"), html_content)


if __name__ == "__main__":
    unittest.main()
