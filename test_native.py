import unittest
from james.layers.native import CommandResult

class TestCommandResult(unittest.TestCase):
    def test_success_property(self):
        """Test that the success property correctly reflects returncode and timed_out."""

        # Happy path: returncode is 0 and not timed out
        result_success = CommandResult(
            command="echo 'hello'",
            returncode=0,
            stdout="hello\n",
            stderr="",
            timed_out=False
        )
        self.assertTrue(result_success.success)

        # Error condition: returncode is non-zero
        result_fail_code = CommandResult(
            command="false",
            returncode=1,
            stdout="",
            stderr="",
            timed_out=False
        )
        self.assertFalse(result_fail_code.success)

        # Error condition: timed out (even if returncode happens to be 0)
        result_fail_timeout = CommandResult(
            command="sleep 10",
            returncode=0,
            stdout="",
            stderr="",
            timed_out=True
        )
        self.assertFalse(result_fail_timeout.success)

        # Error condition: non-zero returncode AND timed out
        result_fail_both = CommandResult(
            command="sleep 10",
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True
        )
        self.assertFalse(result_fail_both.success)

if __name__ == '__main__':
    unittest.main()
