import unittest
from james.layers.native import CommandResult

class TestCommandResult(unittest.TestCase):
    def test_as_dict(self):
        # Happy path
        result = CommandResult(
            command="ls -la",
            returncode=0,
            stdout="total 0",
            stderr="",
            timed_out=False
        )
        d = result.as_dict()
        self.assertEqual(d["command"], "ls -la")
        self.assertEqual(d["returncode"], 0)
        self.assertEqual(d["stdout"], "total 0")
        self.assertEqual(d["stderr"], "")
        self.assertEqual(d["timed_out"], False)

        # Unsuccessful
        result_fail = CommandResult(
            command="ls /nonexistent",
            returncode=2,
            stdout="",
            stderr="No such file or directory",
            timed_out=False
        )
        d_fail = result_fail.as_dict()
        self.assertEqual(d_fail["command"], "ls /nonexistent")
        self.assertEqual(d_fail["returncode"], 2)

        # Timed out
        result_timeout = CommandResult(
            command="sleep 10",
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True
        )
        d_timeout = result_timeout.as_dict()
        self.assertEqual(d_timeout["timed_out"], True)
        self.assertEqual(d_timeout["returncode"], -1)

if __name__ == '__main__':
    unittest.main()
