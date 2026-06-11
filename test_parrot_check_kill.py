import unittest
from unittest.mock import MagicMock
from james.layers.native import NativeLayer, CommandResult
from james.tools.parrot import AircrackSuite

class TestAircrackSuiteCheckKill(unittest.TestCase):
    def setUp(self):
        self.mock_layer = MagicMock(spec=NativeLayer)
        self.suite = AircrackSuite(self.mock_layer)

    def test_check_kill_success(self):
        """Test check_kill execution."""
        # Setup mock behavior
        expected_result = CommandResult(
            command="airmon-ng check kill",
            returncode=0,
            stdout="Killing these processes:\n  PID Name\n  999 wpa_supplicant\n",
            stderr=""
        )
        self.mock_layer.run.return_value = expected_result

        # Call function
        result = self.suite.check_kill()

        # Assertions
        self.mock_layer.run.assert_called_once_with(
            "airmon-ng check kill", sudo=True, timeout=15
        )
        self.assertEqual(result, expected_result)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.command, "airmon-ng check kill")

    def test_check_kill_failure(self):
        """Test check_kill handling of error."""
        # Setup mock behavior for error case
        expected_result = CommandResult(
            command="airmon-ng check kill",
            returncode=1,
            stdout="",
            stderr="airmon-ng: command not found"
        )
        self.mock_layer.run.return_value = expected_result

        # Call function
        result = self.suite.check_kill()

        # Assertions
        self.mock_layer.run.assert_called_once_with(
            "airmon-ng check kill", sudo=True, timeout=15
        )
        self.assertEqual(result, expected_result)
        self.assertEqual(result.returncode, 1)

if __name__ == '__main__':
    unittest.main()
