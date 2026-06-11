import unittest
from unittest.mock import MagicMock
from james.tools.parrot import AircrackSuite
from james.layers.native import CommandResult, NativeLayer


class TestAircrackSuite(unittest.TestCase):
    def setUp(self):
        self.mock_layer = MagicMock(spec=NativeLayer)
        self.suite = AircrackSuite(layer=self.mock_layer)

    def test_check_kill_success(self):
        expected_result = CommandResult(
            command="airmon-ng check kill",
            returncode=0,
            stdout="Killing these processes...",
            stderr=""
        )
        self.mock_layer.run.return_value = expected_result

        result = self.suite.check_kill()

        self.mock_layer.run.assert_called_once_with(
            "airmon-ng check kill",
            sudo=True,
            timeout=15
        )
        self.assertEqual(result, expected_result)
        self.assertTrue(result.success)

    def test_check_kill_failure(self):
        expected_result = CommandResult(
            command="airmon-ng check kill",
            returncode=1,
            stdout="",
            stderr="Failed to kill processes"
        )
        self.mock_layer.run.return_value = expected_result

        result = self.suite.check_kill()

        self.mock_layer.run.assert_called_once_with(
            "airmon-ng check kill",
            sudo=True,
            timeout=15
        )
        self.assertEqual(result, expected_result)
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
