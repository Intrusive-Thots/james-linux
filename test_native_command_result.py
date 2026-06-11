import unittest
from james.layers.native import CommandResult

class TestCommandResult(unittest.TestCase):
    def test_success_when_returncode_0_and_not_timed_out(self):
        result = CommandResult(command="ls", returncode=0, stdout="", stderr="", timed_out=False)
        self.assertTrue(result.success)

    def test_failure_when_returncode_nonzero_and_not_timed_out(self):
        result = CommandResult(command="ls", returncode=1, stdout="", stderr="", timed_out=False)
        self.assertFalse(result.success)

    def test_failure_when_returncode_0_and_timed_out(self):
        result = CommandResult(command="ls", returncode=0, stdout="", stderr="", timed_out=True)
        self.assertFalse(result.success)

    def test_failure_when_returncode_nonzero_and_timed_out(self):
        result = CommandResult(command="ls", returncode=-1, stdout="", stderr="", timed_out=True)
        self.assertFalse(result.success)

if __name__ == "__main__":
    unittest.main()
