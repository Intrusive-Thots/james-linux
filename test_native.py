import unittest
from james.layers.native import CommandResult

class TestCommandResult(unittest.TestCase):
    def test_success_property(self):
        # Case 1: returncode 0, not timed_out -> success is True
        result = CommandResult(command="ls", returncode=0, stdout="", stderr="", timed_out=False)
        self.assertTrue(result.success)

        # Case 2: returncode 0, timed_out -> success is False
        result = CommandResult(command="ls", returncode=0, stdout="", stderr="", timed_out=True)
        self.assertFalse(result.success)

        # Case 3: returncode != 0, not timed_out -> success is False
        result = CommandResult(command="ls", returncode=1, stdout="", stderr="", timed_out=False)
        self.assertFalse(result.success)

        # Case 4: returncode != 0, timed_out -> success is False
        result = CommandResult(command="ls", returncode=-1, stdout="", stderr="", timed_out=True)
        self.assertFalse(result.success)

if __name__ == '__main__':
    unittest.main()
