import unittest
from james.layers.native import CommandResult

class TestCommandResult(unittest.TestCase):
    """Test suite for the CommandResult dataclass in james.layers.native."""

    def test_as_dict_success(self):
        """Test as_dict on a successful command execution."""
        result = CommandResult(
            command="echo 'hello'",
            returncode=0,
            stdout="hello",
            stderr="",
            timed_out=False
        )

        d = result.as_dict()
        self.assertEqual(d["command"], "echo 'hello'")
        self.assertEqual(d["returncode"], 0)
        self.assertEqual(d["stdout"], "hello")
        self.assertEqual(d["stderr"], "")
        self.assertEqual(d["timed_out"], False)

    def test_as_dict_failed(self):
        """Test as_dict on a failed command execution."""
        result = CommandResult(
            command="cat nonexistent",
            returncode=1,
            stdout="",
            stderr="No such file or directory",
            timed_out=False
        )

        d = result.as_dict()
        self.assertEqual(d["command"], "cat nonexistent")
        self.assertEqual(d["returncode"], 1)
        self.assertEqual(d["stdout"], "")
        self.assertEqual(d["stderr"], "No such file or directory")
        self.assertEqual(d["timed_out"], False)

    def test_as_dict_timed_out(self):
        """Test as_dict on a command that timed out."""
        result = CommandResult(
            command="sleep 10",
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True
        )

        d = result.as_dict()
        self.assertEqual(d["command"], "sleep 10")
        self.assertEqual(d["returncode"], -1)
        self.assertEqual(d["stdout"], "")
        self.assertEqual(d["stderr"], "")
        self.assertEqual(d["timed_out"], True)

if __name__ == '__main__':
    unittest.main()
