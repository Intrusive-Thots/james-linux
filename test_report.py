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
    @patch.object(Path, "write_text")
    @patch.object(Path, "mkdir")
    @patch.object(Path, "home")
    def test_save_report_with_default_path(
        self, mock_home, mock_mkdir, mock_write_text, mock_datetime
    ):
        mock_home.return_value = Path("/mock/home")
        mock_datetime.now.return_value.strftime.return_value = (
            "20231010_120000"
        )

        html_content = "<html><body>Report</body></html>"

        result = save_report(html_content)

        expected_path = Path(
            "/mock/home/.james/loot/report_20231010_120000.html"
        )
        self.assertEqual(result, expected_path)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write_text.assert_called_once_with(html_content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
