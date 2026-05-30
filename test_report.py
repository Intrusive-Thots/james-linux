import unittest
from unittest.mock import patch
from pathlib import Path
from james.core.report import save_report


class TestReport(unittest.TestCase):

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
