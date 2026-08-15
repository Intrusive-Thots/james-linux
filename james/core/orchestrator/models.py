"""Orchestrator data models."""
from datetime import datetime
from typing import Optional

class TaskEntry:
    """Single entry in the task log."""

    def __init__(self, action: str, tool: str, params: dict):
        self.timestamp = datetime.now().isoformat()
        self.action = action
        self.tool = tool
        self.params = params
        self.result: Optional[dict] = None
        self.status = "pending"  # pending | running | done | error

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "tool": self.tool,
            "params": self.params,
            "result": self.result,
            "status": self.status,
        }
