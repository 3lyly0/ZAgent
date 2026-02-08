"""Base tool system for extensible functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all tools/hands."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description."""
        pass
    
    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """Check if this tool can handle the given message.
        
        Args:
            message: The assistant's message content
            
        Returns:
            True if this tool can handle the message
        """
        pass
    
    @abstractmethod
    def extract_request(self, message: str) -> str | None:
        """Extract the tool request from the message.
        
        Args:
            message: The assistant's message content
            
        Returns:
            The extracted request or None if not found
        """
        pass
    
    @abstractmethod
    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        """Execute the tool with the given request.
        
        Args:
            request: The extracted request
            context: Optional context information
            
        Returns:
            The formatted result
        """
        pass
    
    def format_result(self, result: Any) -> str:
        """Format the execution result.
        
        Args:
            result: The raw execution result
            
        Returns:
            Formatted result string
        """
        return str(result)


class ToolResult:
    """Container for tool execution results."""
    
    def __init__(
        self,
        tool_name: str,
        request: str,
        success: bool,
        output: str = "",
        error: str = "",
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Initialize tool result.
        
        Args:
            tool_name: Name of the tool that executed
            request: The original request
            success: Whether execution was successful
            output: Standard output
            error: Error output if any
            metadata: Additional metadata
        """
        self.tool_name = tool_name
        self.request = request
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
    
    def format(self) -> str:
        """Format result as a string."""
        lines = [f"TOOL_RESULT {self.tool_name}"]
        lines.append(f"request: {self.request}")
        lines.append(f"success: {'yes' if self.success else 'no'}")
        
        if self.output:
            lines.append(f"output:\n{self.output}")
        
        if self.error:
            lines.append(f"error:\n{self.error}")
        
        for key, value in self.metadata.items():
            lines.append(f"{key}: {value}")
        
        return "\n".join(lines)
