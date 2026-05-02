from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Optional
import json

class MCPToolClient:
    """
    Base generic MCPToolClient that holds registered tools.
    In a real MCP implementation, this would act as a bridge to standard MCP protocols.
    For this native implementation, it registers python functions and exposes them as CrewAI tools.
    """

    def __init__(self, name: str):
        self.name = name
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}

    def register_tool(self, name: str, description: str, func: Callable):
        """Register a python callable as a tool."""
        self._tools[name] = func
        self._descriptions[name] = description

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a registered tool and return the output as a JSON string."""
        if tool_name not in self._tools:
            return json.dumps({"error": f"Tool {tool_name} not found"})

        try:
            result = self._tools[tool_name](**kwargs)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_tools(self) -> Dict[str, str]:
        """Returns a dict of tool name -> description"""
        return self._descriptions
