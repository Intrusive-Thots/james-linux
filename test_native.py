import unittest
from james.layers.native import CommandResult


class TestCommandResult(unittest.TestCase):
    def test_as_dict_success(self):
        result = CommandResult(
            command="echo 'hello'",
            returncode=0,
            stdout="hello\n",
            stderr="",
            timed_out=False,
        )
        expected = {
            "command": "echo 'hello'",
            "returncode": 0,
            "stdout": "hello\n",
            "stderr": "",
            "timed_out": False,
            "success": True,
        }
        self.assertEqual(result.as_dict(), expected)

    def test_as_dict_failure(self):
        result = CommandResult(
            command="ls /nonexistent",
            returncode=2,
            stdout="",
            stderr="No such file or directory\n",
            timed_out=False,
        )
        expected = {
            "command": "ls /nonexistent",
            "returncode": 2,
            "stdout": "",
            "stderr": "No such file or directory\n",
            "timed_out": False,
            "success": False,
        }
        self.assertEqual(result.as_dict(), expected)

    def test_as_dict_timeout(self):
        result = CommandResult(
            command="sleep 10", returncode=-1, stdout="", stderr="", timed_out=True
        )
        expected = {
            "command": "sleep 10",
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "timed_out": True,
            "success": False,
        }
        self.assertEqual(result.as_dict(), expected)


if __name__ == "__main__":
    unittest.main()
