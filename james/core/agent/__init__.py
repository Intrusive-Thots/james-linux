"""JAMES Agent package — stable public API.

The full agent implementation is kept in agent.py to preserve the historical
intent handlers and orchestrator integration.
"""
from .agent import Agent, AgentAction, AgentPlan, PlanStep, AttackPlan, INTENT_PATTERNS

__all__ = [
    "Agent",
    "AgentAction",
    "AgentPlan",
    "PlanStep",
    "AttackPlan",
    "INTENT_PATTERNS",
]
