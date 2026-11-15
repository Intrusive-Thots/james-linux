import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from james.core.auto_agent import AutonomousAgent


class TestAutonomousAgent(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.test_dir.cleanup)
        self.workspace_path = Path(self.test_dir.name) / "workspace"
        self.workspace_path.mkdir()
        self.home_path = Path(self.test_dir.name) / "home"
        self.home_path.mkdir()
        home = patch("james.core.auto_agent.Path.home", return_value=self.home_path)
        home.start()
        self.addCleanup(home.stop)
        state = patch.dict(os.environ, {"JAMES_DATA_DIR": str(self.home_path / ".james")})
        state.start()
        self.addCleanup(state.stop)
        ai = patch("james.core.auto_agent.GeminiEngine")
        self.mock_ai = ai.start().return_value
        self.addCleanup(ai.stop)
        self.mock_ai.chat_only.return_value = "```bash\necho 'hello'\n```"
        self.agent = AutonomousAgent(workspace=str(self.workspace_path))

        # Real Git state exercises the branch and clean-workspace guards.
        self.real_run = subprocess.run
        self.git("init", "-b", "repair/test-agent")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test User")
        self.task_file = self.workspace_path / "task_list.md"
        self.task_file.write_text("- [ ] Implement feature X\n- [ ] Fix bug Y\n")
        self.git("add", ".")
        self.git("commit", "-m", "Initial")

    def git(self, *args):
        return self.real_run(
            ["git", *args], cwd=self.workspace_path,
            capture_output=True, text=True, check=True,
        )

    def command_result(self, cmd, **kwargs):
        if cmd[0] == "git":
            return self.real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def test_phases_execution(self):
        with patch("james.core.auto_agent.subprocess.run", side_effect=self.command_result) as run:
            self.agent.load_memory()
            self.assertEqual(self.agent.memory["executions"], 0)
            self.agent.load_repository_index()
            self.assertIsInstance(self.agent.repo_index, list)
            self.agent.load_knowledge_graph()
            self.assertIsNotNone(self.agent.graph.get_node("START"))
            self.agent.discover_next_task()
            self.assertEqual(self.agent.current_task, "Implement feature X")
            self.agent.implement()
            self.assertTrue(self.agent.implementation_success)
            self.assertEqual(self.agent.memory["last_implementation"], "Implement feature X")
            self.agent.test()
            self.assertTrue(self.agent.test_success)
            self.agent.benchmark()
            self.assertIn("execution_time", self.agent.benchmark_metrics)
            self.assertTrue((self.agent.data_dir / "benchmarks.log").exists())
            self.agent.learn()
            self.assertIn("Implement feature X", self.agent.memory["successful_tasks"])
            self.assertEqual(self.agent.memory["executions"], 1)
            self.agent.update_plan()

        self.assertEqual(self.agent.data_dir, self.home_path / ".james" / "auto_agent")
        self.assertFalse((self.workspace_path / ".james").exists())
        self.assertFalse((self.agent.data_dir / "current_task.sh").exists())
        self.assertIn("- [x] Implement feature X", self.task_file.read_text())
        self.assertIn("- [ ] Fix bug Y", self.task_file.read_text())
        self.assertEqual(self.git("log", "--format=%s").stdout.strip(), "Initial")
        self.assertFalse(any(call.args[0][:2] == ["git", "commit"] for call in run.call_args_list))

    def test_failed_verification_preserves_changes_for_review(self):
        self.agent.load_memory()
        self.agent.current_task = "Bad Feature"
        review_file = self.workspace_path / "generated.py"
        original_tasks = self.task_file.read_text()

        def fail_tests(cmd, **kwargs):
            if cmd[0] == "git":
                return self.real_run(cmd, **kwargs)
            if cmd == ["python3", "-m", "pytest"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="failure", stderr="")
            review_file.write_text("# preserve this failed implementation for review\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("james.core.auto_agent.subprocess.run", side_effect=fail_tests) as run:
            self.agent.implement()
            self.assertTrue(self.agent.implementation_success)
            self.agent.test()
            self.agent.update_plan()

        self.assertFalse(self.agent.test_success)
        self.assertTrue(review_file.exists())
        self.assertEqual(self.task_file.read_text(), original_tasks)
        self.assertEqual(self.git("log", "--format=%s").stdout.strip(), "Initial")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["python3", "-m", "pytest"], commands)
        self.assertFalse(any(cmd[:2] in (["git", "reset"], ["git", "clean"]) for cmd in commands))

    @patch("james.core.auto_agent.AUTO_AGENT_ENABLED", True)
    @patch("james.core.auto_agent.time.sleep")
    def test_hourly_loop_pauses_for_review_after_one_task(self, sleep):
        with patch("james.core.auto_agent.subprocess.run", side_effect=self.command_result):
            self.agent.run_hourly_loop(max_iterations=2)

        self.assertEqual(self.agent.memory["executions"], 1)
        self.assertIn("- [x] Implement feature X", self.task_file.read_text())
        self.assertIn("- [ ] Fix bug Y", self.task_file.read_text())
        self.mock_ai.chat_only.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(self.git("log", "--format=%s").stdout.strip(), "Initial")

    @patch("james.core.auto_agent.AUTO_AGENT_ENABLED", False)
    def test_hourly_loop_requires_opt_in(self):
        with patch("james.core.auto_agent.subprocess.run") as run:
            self.agent.run_hourly_loop(max_iterations=1)
        run.assert_not_called()
        self.mock_ai.chat_only.assert_not_called()
        self.assertEqual(self.agent.memory, {})

    def test_protected_branch_blocks_implementation(self):
        self.git("branch", "-m", "master")
        self.agent.current_task = "Unsafe task"
        self.agent.implement()
        self.assertFalse(self.agent.implementation_success)
        self.mock_ai.chat_only.assert_not_called()

    def test_existing_changes_block_implementation(self):
        self.task_file.write_text("uncommitted user changes\n")
        self.agent.current_task = "Unsafe task"
        self.agent.implement()
        self.assertFalse(self.agent.implementation_success)
        self.assertEqual(self.task_file.read_text(), "uncommitted user changes\n")
        self.mock_ai.chat_only.assert_not_called()


if __name__ == "__main__":
    unittest.main()
