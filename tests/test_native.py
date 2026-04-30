import unittest
from unittest.mock import patch
from james.layers.native import NativeLayer

class TestNativeLayer(unittest.TestCase):

    @patch('james.layers.native.subprocess.run')
    def test_execute_success(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "hello\n"
        mock_run.return_value.stderr = ""

        layer = NativeLayer()
        code, out, err = layer.execute(["echo", "hello"])

        self.assertEqual(code, 0)
        self.assertEqual(out, "hello\n")
        self.assertEqual(err, "")
        mock_run.assert_called_once()

    @patch('james.layers.native.os.geteuid')
    @patch('james.layers.native.subprocess.run')
    def test_execute_sudo(self, mock_run, mock_geteuid):
        mock_geteuid.return_value = 1000  # Not root
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        layer = NativeLayer()
        layer.execute(["ls"], require_root=True)

        # Check if sudo was prepended
        called_cmd = mock_run.call_args[0][0]
        self.assertEqual(called_cmd[0], "sudo")
        self.assertEqual(called_cmd[1], "ls")

if __name__ == '__main__':
    unittest.main()
