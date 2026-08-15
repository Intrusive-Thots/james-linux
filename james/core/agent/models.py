"""Agent data models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class AgentAction:
    """A single planned action the agent will execute."""

    description: str
    method: str  # orchestrator method name
    args: dict = field(default_factory=dict)
    requires_confirm: bool = False


@dataclass
class AgentPlan:
    """Multi-step plan the agent generates from user input."""

    intent: str
    summary: str
    actions: list[AgentAction] = field(default_factory=list)


@dataclass
class PlanStep:
    """A single step in a tracked attack plan."""

    description: str
    action: str
    status: str = "pending"  # pending / running / done / failed
    result_summary: str = ""


@dataclass
class AttackPlan:
    """Multi-turn attack plan tracked across the conversation."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    current_step: int = 0
    status: str = "active"  # active / complete / aborted
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def summary(self) -> str:
        """Render a compact plan status."""
        lines = [f"🎯 Attack Plan: {self.goal}"]
        lines.append(f"   Status: {self.status.upper()}")
        lines.append("")
        for i, step in enumerate(self.steps):
            icon = {"pending": "⬜", "running": "🔄", "done": "✅",
                    "failed": "❌"}.get(step.status, "⬜")
            marker = " ◀" if i == self.current_step and self.status == "active" else ""
            lines.append(f"   {icon} {i+1}. {step.description}{marker}")
            if step.result_summary:
                lines.append(f"      └─ {step.result_summary[:80]}")
        return "\n".join(lines)
