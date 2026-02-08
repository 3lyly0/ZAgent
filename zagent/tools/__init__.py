"""Tool registry and auto-discovery system."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any

from zagent.tools.base import BaseTool


class ToolRegistry:
    """Registry for managing and discovering tools."""
    
    def __init__(self) -> None:
        """Initialize tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._enabled_tools: set[str] = set()
    
    def register(self, tool: BaseTool, enabled: bool = True) -> None:
        """Register a tool.
        
        Args:
            tool: The tool instance to register
            enabled: Whether the tool is enabled by default
        """
        self._tools[tool.name] = tool
        if enabled:
            self._enabled_tools.add(tool.name)
    
    def enable(self, tool_name: str) -> None:
        """Enable a tool by name."""
        if tool_name in self._tools:
            self._enabled_tools.add(tool_name)
    
    def disable(self, tool_name: str) -> None:
        """Disable a tool by name."""
        self._enabled_tools.discard(tool_name)
    
    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_enabled_tools(self) -> list[BaseTool]:
        """Get list of enabled tools."""
        return [
            tool for name, tool in self._tools.items()
            if name in self._enabled_tools
        ]
    
    def find_tool_for_message(self, message: str) -> BaseTool | None:
        """Find the first enabled tool that can handle the message.
        
        Args:
            message: The assistant's message
            
        Returns:
            The tool that can handle the message, or None
        """
        for tool in self.get_enabled_tools():
            if tool.can_handle(message):
                return tool
        return None
    
    def execute_if_applicable(
        self,
        message: str,
        context: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """Execute tool if applicable to message.
        
        Args:
            message: The assistant's message
            context: Optional context
            
        Returns:
            Tuple of (was_executed, result)
        """
        tool = self.find_tool_for_message(message)
        if not tool:
            return False, None
        
        request = tool.extract_request(message)
        if not request:
            return False, None
        
        result = tool.execute(request, context)
        return True, result
    
    def auto_discover(self, package_name: str = "zagent.tools") -> int:
        """Auto-discover and register tools from package.
        
        Args:
            package_name: Package to search for tools
            
        Returns:
            Number of tools discovered
        """
        discovered = 0
        
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent
            
            # Iterate through all modules in package
            for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
                if module_name.startswith("_") or module_name == "base":
                    continue
                
                try:
                    module = importlib.import_module(f"{package_name}.{module_name}")
                    
                    # Find BaseTool subclasses in module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (obj is not BaseTool and 
                            issubclass(obj, BaseTool) and 
                            obj.__module__ == module.__name__):
                            
                            # Instantiate and register tool
                            tool_instance = obj()
                            self.register(tool_instance, enabled=True)
                            discovered += 1
                            
                except Exception as e:
                    print(f"Warning: Could not load tool from {module_name}: {e}")
                    
        except Exception as e:
            print(f"Warning: Could not auto-discover tools: {e}")
        
        return discovered


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def auto_discover_tools() -> int:
    """Auto-discover tools and register them globally.
    
    Returns:
        Number of tools discovered
    """
    registry = get_global_registry()
    return registry.auto_discover()
