import unittest
from james.layers.native import CommandResult


class TestCommandResultSuccess(unittest.TestCase):
    def test_success_property(self):
        # success should be True when returncode is 0
        res = CommandResult(
            command="ls", returncode=0, stdout="out", stderr=""
        )
        self.assertTrue(res.success)

        # False when returncode is non-zero
        res2 = CommandResult(
            command="ls", returncode=1, stdout="out", stderr=""
        )
        self.assertFalse(res2.success)

        # False when timed_out is True
        res3 = CommandResult(
            command="ls",
            returncode=0,
            stdout="out",
            stderr="",
            timed_out=True,
        )
        self.assertFalse(res3.success)

        # False when returncode!=0 and timed_out=True
        res4 = CommandResult(
            command="ls",
            returncode=1,
            stdout="out",
            stderr="",
            timed_out=True,
        )
        self.assertFalse(res4.success)


if __name__ == "__main__":
    unittest.main()
