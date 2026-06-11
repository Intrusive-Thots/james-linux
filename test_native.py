import unittest
from unittest.mock import patch
from james.layers.native import NativeLayer, CommandResult

class TestNativeLayer(unittest.TestCase):
    def setUp(self):
        self.layer = NativeLayer()

    @patch.object(NativeLayer, 'run')
    def test_check_tool_valid(self, mock_run):
        # Mocking the self.run call for deterministic tests
        mock_run.return_value = CommandResult(command="which ls", returncode=0, stdout="/bin/ls\n", stderr="")

        result = self.layer.check_tool("ls")

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch.object(NativeLayer, 'run')
    def test_check_tool_invalid(self, mock_run):
        # Mocking the self.run call for deterministic tests
        mock_run.return_value = CommandResult(command="which this_tool_should_not_exist_xyz123", returncode=1, stdout="", stderr="which: no this_tool_should_not_exist_xyz123 in (...)")

        result = self.layer.check_tool("this_tool_should_not_exist_xyz123")

        self.assertFalse(result)
        mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
