"""Example Echo Tool to demonstrate modularity."""

from __future__ import annotations

import re
from typing import Any

from zagent.tools.base import BaseTool, ToolResult


class EchoTool(BaseTool):
    """Simple tool that echoes the input text."""
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "Echo text back for testing"
    
    def can_handle(self, message: str) -> bool:
        return bool(re.search(r"<echo>(.*?)</echo>", message, re.DOTALL))
    
    def extract_request(self, message: str) -> str | None:
        match = re.search(r"<echo>(.*?)</echo>", message, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        result = ToolResult(
            tool_name=self.name,
            request=request,
            success=True,
            output=f"ECHO: {request}"
        )
        return result.format()
