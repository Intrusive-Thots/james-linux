"""Guard against placeholder stubs in core packages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_agent_not_placeholder():
    content = (ROOT / "james/core/agent/agent.py").read_text()
    assert "PLACEHOLDER" not in content, "agent.py still contains PLACEHOLDER"
    assert "class Agent" in content, "Agent class missing"

def test_orchestrator_not_placeholder():
    content = (ROOT / "james/core/orchestrator/orchestrator.py").read_text()
    assert "PLACEHOLDER" not in content, "orchestrator.py still contains PLACEHOLDER"
    assert "class Orchestrator" in content, "Orchestrator class missing"
