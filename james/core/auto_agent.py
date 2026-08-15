import os
import json
import time
import subprocess
import logging
from typing import Optional, Dict, List
from pathlib import Path

from james.core.sedge import DecisionGraph, Node, Edge, SelfEvolvingAgent
from james.core.ai_engine import GeminiEngine

logger = logging.getLogger("auto_agent")

# Opt-in: set JAMES_AUTO_AGENT=1 to enable the hourly self-improvement loop.
AUTO_AGENT_ENABLED = os.environ.get("JAMES_AUTO_AGENT", "").strip() in ("1", "true", "yes")

class AutonomousAgent:
    """
    Autonomous Self-Improving AI Agent.
    Implements the core hourly loop to continuously improve the system.

    Data (memory, knowledge graph, benchmarks) lives under ~/.james/
    so it never pollutes the git working tree.
    """
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        # Persist agent state outside the repo (P2.4)
        self.data_dir = Path.home() / ".james" / "auto_agent"
        self.memory_file = self.data_dir / "auto_agent_memory.json"
        self.graph_file = self.data_dir / "knowledge_graph.json"
        self.plan_file = self.workspace / "implementation_plan.md"
        self.task_file = self.workspace / "task_list.md"

        # Ensure data dir exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.graph = DecisionGraph()
        self.sedge_agent = SelfEvolvingAgent(self.graph)
        self.memory: Dict = {}
        self.repo_index: List[str] = []
        self.current_task: Optional[str] = None
        self.benchmark_metrics: Dict = {}
        self.test_success: bool = False

        self.ai = GeminiEngine()

    def load_memory(self):
        if self.memory_file.exists():
            with open(self.memory_file, "r") as f:
                self.memory = json.load(f)
        else:
            self.memory = {"executions": 0, "successful_tasks": []}
        logger.info(f"Loaded memory. Executions: {self.memory.get('executions')}")

    def load_repository_index(self):
        # Gather all python files for context
        self.repo_index = []
        for root, _, files in os.walk(self.workspace):
            if ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    self.repo_index.append(os.path.join(root, file))
        logger.info(f"Indexed {len(self.repo_index)} repository files.")

    def load_knowledge_graph(self):
        if self.graph_file.exists():
            self.sedge_agent.load_graph(str(self.graph_file))
            logger.info("Knowledge graph loaded.")
        else:
            self.graph.add_node(Node(id="START", state_type="state"))
            self.sedge_agent.save_graph(str(self.graph_file))
            logger.info("Initialized new knowledge graph.")

    def load_implementation_plan(self):
        if self.plan_file.exists():
            self.plan_content = self.plan_file.read_text()
            logger.info("Implementation plan loaded.")
        else:
            self.plan_content = ""

    def discover_next_task(self):
        if self.task_file.exists():
            lines = self.task_file.read_text().splitlines()
            pending = [line for line in lines if line.startswith("- [ ]")]
            if pending:
                self.current_task = pending[0].replace("- [ ]", "").strip()
                logger.info(f"Discovered next task: {self.current_task}")
            else:
                self.current_task = None
                logger.info("No pending tasks found.")
        else:
            self.current_task = None

    def verify_dependencies(self):
        req_file = self.workspace / "requirements.txt"
        if req_file.exists():
            logger.info("Verifying dependencies...")
            subprocess.run(["pip", "install", "-r", str(req_file)], capture_output=True)

    def _generate_code(self, task_description: str) -> str:
        """Uses GeminiEngine to generate bash commands/python code based on the task description."""
        context = {
            "task": task_description,
            "workspace": str(self.workspace),
            "repo_files": self.repo_index[:10]
        }
        prompt = f"Implement the following task: {task_description}. Provide a valid bash script that implements this task by modifying the existing files (e.g. using sed, awk, or echoing python code into a file) and writing any necessary tests. Output ONLY the bash script inside a ```bash``` block."

        response = self.ai.chat_only(prompt, context)

        if response:
             if "```bash" in response:
                 code = response.split("```bash")[1].split("```")[0].strip()
                 return code
             elif "```" in response:
                 code = response.split("```")[1].split("```")[0].strip()
                 return code
             return response.strip()
        return ""

    def implement(self):
        if self.current_task:
            logger.info(f"Implementing task: {self.current_task}")

            # Use AI to generate code
            generated_script = self._generate_code(self.current_task)

            if generated_script:
                script_file = self.data_dir / "current_task.sh"
                script_file.write_text(generated_script)
                os.chmod(script_file, 0o755)

                logger.info("Executing implementation script...")
                result = subprocess.run([str(script_file)], capture_output=True, text=True, cwd=self.workspace)

                if result.returncode == 0:
                    logger.info("Implementation script executed successfully.")
                    self.memory["last_implementation"] = self.current_task
                else:
                    logger.warning(f"Implementation script failed: {result.stderr}")
                    self.memory["last_implementation"] = None

                # Clean up script
                if script_file.exists():
                    os.remove(script_file)
            else:
                 logger.warning(f"Failed to generate implementation for task: {self.current_task}")
                 self.memory["last_implementation"] = None
        else:
            logger.info("No task to implement.")

    def _get_current_commit(self) -> str:
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=self.workspace, check=True)
            return result.stdout.strip()
        except Exception:
            return ""

    def test(self):
        logger.info("Running self verification (pytest)...")
        # Run actual tests to verify changes
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(["python3", "-m", "pytest"], capture_output=True, text=True, cwd=self.workspace, env=env)
        self.test_success = (result.returncode == 0)

        if self.test_success:
            logger.info("Self verification passed.")

            # Commit the successful changes
            try:
                subprocess.run(["git", "add", "."], cwd=self.workspace, check=True)
                commit_msg = f"Auto-implemented: {self.current_task}" if self.current_task else "Auto-agent improvements"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.workspace, check=True)
                logger.info(f"Committed changes: {commit_msg}")
            except Exception as e:
                logger.warning(f"Failed to commit changes: {e}")
        else:
            logger.warning("Self verification failed. Rolling back changes.")
            # Rollback to last clean state
            try:
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=self.workspace, check=True)
                subprocess.run(["git", "clean", "-fd"], cwd=self.workspace, check=True)
                logger.info("Rolled back working directory to last commit.")
            except Exception as e:
                logger.error(f"Failed to rollback changes: {e}")

    def benchmark(self):
        logger.info("Running benchmarks...")
        start_time = time.time()

        # Run the actual test suite as a benchmark for performance
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        subprocess.run(["python3", "-m", "pytest"], capture_output=True, text=True, cwd=self.workspace, env=env)

        end_time = time.time()
        self.benchmark_metrics["execution_time"] = end_time - start_time
        logger.info(f"Benchmark complete: {self.benchmark_metrics}")

        # Log benchmark under ~/.james
        bench_log = self.data_dir / "benchmarks.log"
        with open(bench_log, "a") as f:
            f.write(f"{time.time()},{self.current_task},{self.benchmark_metrics['execution_time']}\n")

    def learn(self):
        logger.info("Updating learning engine...")
        if self.current_task and self.test_success:
            if "successful_tasks" not in self.memory:
                self.memory["successful_tasks"] = []
            if self.current_task not in self.memory["successful_tasks"]:
                self.memory["successful_tasks"].append(self.current_task)

            # Update knowledge graph (sedge)
            node_id = f"TASK_{len(self.memory['successful_tasks'])}"
            if not self.graph.get_node(node_id):
                self.graph.add_node(Node(id=node_id, state_type="action", metadata={"task": self.current_task}))
                self.graph.add_edge(Edge(from_node="START", to_node=node_id, success_weight=1.0))

            self.sedge_agent.feedback(success=True)
            self.sedge_agent.save_graph(str(self.graph_file))

        self.memory["executions"] = self.memory.get("executions", 0) + 1
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f)

    def update_plan(self):
        if self.current_task and self.test_success and self.task_file.exists():
            logger.info("Updating task queue...")
            lines = self.task_file.read_text().splitlines()
            new_lines = []
            for line in lines:
                if self.current_task in line and line.startswith("- [ ]"):
                    new_lines.append(line.replace("- [ ]", "- [x]"))
                else:
                    new_lines.append(line)
            self.task_file.write_text("\n".join(new_lines) + "\n")

            # Commit the updated task list
            try:
                subprocess.run(["git", "add", str(self.task_file)], cwd=self.workspace, check=True)
                subprocess.run(["git", "commit", "-m", f"Update task list: {self.current_task} completed"], cwd=self.workspace, check=True)
            except Exception:
                pass

    def schedule_next_run(self):
        logger.info("Scheduling next hourly loop...")
        time.sleep(3600)

    def run_hourly_loop(self, max_iterations: Optional[int] = None):
        if not AUTO_AGENT_ENABLED:
            logger.warning(
                "Autonomous agent is disabled. Set JAMES_AUTO_AGENT=1 to enable."
            )
            return

        iteration = 0

        # Ensure we are on a clean branch/state
        try:
             subprocess.run(["git", "checkout", "-b", "auto-agent-workspace"], capture_output=True, cwd=self.workspace)
        except Exception:
             pass

        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
            logger.info(f"Starting hourly loop iteration {iteration + 1}")
            self.load_memory()
            self.load_repository_index()
            self.load_knowledge_graph()
            self.load_implementation_plan()
            self.discover_next_task()
            self.verify_dependencies()
            self.implement()
            self.test()
            self.benchmark()
            self.learn()
            self.update_plan()
            if max_iterations is None or iteration < max_iterations - 1:
                self.schedule_next_run()
            iteration += 1
