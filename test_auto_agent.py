import unittest
import os
import json
from unittest.mock import patch, MagicMock, ANY
from james.core.auto_agent import AutonomousAgent
import tempfile
from pathlib import Path
import subprocess

class TestAutonomousAgent(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.test_dir.name)
        self.agent = AutonomousAgent(workspace=str(self.workspace_path))

        # Initialize git repo in test dir for rollback tests
        subprocess.run(["git", "init"], cwd=self.workspace_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.workspace_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.workspace_path, capture_output=True)

        # Create dummy task file
        self.task_file = self.workspace_path / "task_list.md"
        self.task_file.write_text("- [ ] Implement feature X\n- [ ] Fix bug Y\n")

        subprocess.run(["git", "add", "."], cwd=self.workspace_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.workspace_path, capture_output=True)

    def tearDown(self):
        self.test_dir.cleanup()

    @patch('subprocess.run')
    @patch('james.core.ai_engine.GeminiEngine.chat_only')
    def test_phases_execution(self, mock_chat, mock_run):
        # Mock subprocess run to return success for tests
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Have chat return a script that just echoes hello
        mock_chat.return_value = "```bash\necho 'hello'\n```"

        # Create dummy james core dir
        (self.workspace_path / "james" / "core").mkdir(parents=True, exist_ok=True)

        self.agent.load_memory()
        self.assertEqual(self.agent.memory["executions"], 0)

        self.agent.load_repository_index()
        self.assertIsInstance(self.agent.repo_index, list)

        self.agent.load_knowledge_graph()
        self.assertIsNotNone(self.agent.graph.get_node("START"))

        self.agent.discover_next_task()
        self.assertEqual(self.agent.current_task, "Implement feature X")

        self.agent.implement()
        self.assertEqual(self.agent.memory["last_implementation"], "Implement feature X")

        self.agent.test()
        self.assertTrue(self.agent.test_success)

        self.agent.benchmark()
        self.assertIn("execution_time", self.agent.benchmark_metrics)
        self.assertTrue((self.workspace_path / ".james" / "benchmarks.log").exists())

        self.agent.learn()
        self.assertIn("Implement feature X", self.agent.memory["successful_tasks"])
        self.assertEqual(self.agent.memory["executions"], 1)

        self.agent.update_plan()
        task_content = self.task_file.read_text()
        self.assertIn("- [x] Implement feature X", task_content)
        self.assertIn("- [ ] Fix bug Y", task_content)

    @patch('subprocess.run')
    @patch('james.core.ai_engine.GeminiEngine.chat_only')
    def test_rollback_on_failure(self, mock_chat, mock_run):
         # Create dummy james core dir
        (self.workspace_path / "james" / "core").mkdir(parents=True, exist_ok=True)

        self.agent.current_task = "Bad Feature"
        mock_chat.return_value = "```bash\necho 'bad code'\n```"

        # Mock implement script execution success, but tests fail
        def side_effect(cmd, **kwargs):
            res = MagicMock()
            if "pytest" in cmd:
                res.returncode = 1
            else:
                res.returncode = 0
            return res
        mock_run.side_effect = side_effect

        self.agent.implement()
        self.agent.test()

        self.assertFalse(self.agent.test_success)

        # Check if git reset and clean were called
        reset_called = False
        clean_called = False
        for call in mock_run.call_args_list:
             cmd = call[0][0]
             if cmd[:3] == ["git", "reset", "--hard"]:
                 reset_called = True
             if cmd[:2] == ["git", "clean"]:
                 clean_called = True

        self.assertTrue(reset_called)
        self.assertTrue(clean_called)

    @patch('time.sleep', return_value=None)
    @patch('subprocess.run')
    @patch('james.core.ai_engine.GeminiEngine.chat_only')
    def test_run_hourly_loop(self, mock_chat, mock_run, mock_sleep):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mock_chat.return_value = "```bash\necho 'success'\n```"

        # Create dummy james core dir
        (self.workspace_path / "james" / "core").mkdir(parents=True, exist_ok=True)

        self.agent.run_hourly_loop(max_iterations=2)

        # Iteration 1 finished Implement feature X, Iteration 2 finished Fix bug Y
        self.assertEqual(self.agent.memory["executions"], 2)

        task_content = self.task_file.read_text()
        self.assertIn("- [x] Implement feature X", task_content)
        self.assertIn("- [x] Fix bug Y", task_content)

        # Ensure sleep was called for the hourly wait
        mock_sleep.assert_any_call(3600)

if __name__ == "__main__":
    unittest.main()
