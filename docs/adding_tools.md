# Adding Custom Tools to ZAgent

This guide shows you how to create and add custom tools to ZAgent.

## Quick Start: Create a Tool in 3 Steps

### 1. Create Tool File

Create a new Python file in `zagent/tools/` (e.g., `echo_tool.py`):

```python
from zagent.tools.base import BaseTool, ToolResult
import re

class EchoTool(BaseTool):
    """Example tool that echoes text back."""
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "Echo text back to the user"
    
    def can_handle(self, message: str) -> bool:
        return bool(re.search(r"<echo>(.*?)</echo>", message, re.DOTALL))
    
    def extract_request(self, message: str) -> str | None:
        match = re.search(r"<echo>(.*?)</echo>", message, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def execute(self, request: str, context=None) -> str:
        result = ToolResult(
            tool_name=self.name,
            request=request,
            success=True,
            output=f"Echo: {request}"
        )
        return result.format()
```

### 2. That's It!

The tool will be **auto-discovered** when ZAgent starts. No registration needed!

### 3. Test It

```bash
python main.py --token YOUR_TOKEN "test echo tool"
```

Then ask the AI to use: `<echo>hello world</echo>`

---

## Advanced Examples

### File Reader Tool

```python
from pathlib import Path
from zagent.tools.base import BaseTool, ToolResult
import re

class FileReaderTool(BaseTool):
    """Read files from disk."""
    
    FILE_TAG = re.compile(r"<read_file>(.*?)</read_file>", re.DOTALL)
    
    @property
    def name(self) -> str:
        return "file_reader"
    
    @property
    def description(self) -> str:
        return "Read content from files"
    
    def can_handle(self, message: str) -> bool:
        return bool(self.FILE_TAG.search(message))
    
    def extract_request(self, message: str) -> str | None:
        match = self.FILE_TAG.search(message)
        return match.group(1).strip() if match else None
    
    def execute(self, request: str, context=None) -> str:
        try:
            path = Path(request)
            if not path.exists():
                return ToolResult(
                    self.name, request, False,
                    error="File not found"
                ).format()
            
            content = path.read_text(encoding="utf-8")
            return ToolResult(
                self.name, request, True,
                output=content
            ).format()
        except Exception as e:
            return ToolResult(
                self.name, request, False,
                error=str(e)
            ).format()
```

### Web Search Tool

```python
import requests
from zagent.tools.base import BaseTool, ToolResult
import re

class WebSearchTool(BaseTool):
    """Search the web."""
    
    SEARCH_TAG = re.compile(r"<search>(.*?)</search>", re.DOTALL)
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information"
    
    def can_handle(self, message: str) -> bool:
        return bool(self.SEARCH_TAG.search(message))
    
    def extract_request(self, message: str) -> str | None:
        match = self.SEARCH_TAG.search(message)
        return match.group(1).strip() if match else None
    
    def execute(self, request: str, context=None) -> str:
        try:
            # Example using DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {"q": request, "format": "json"}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            abstract = data.get("Abstract", "No results found")
            return ToolResult(
                self.name, request, True,
                output=abstract
            ).format()
        except Exception as e:
            return ToolResult(
                self.name, request, False,
                error=str(e)
            ).format()
```

---

## Configuration

### Enable/Disable Tools

Edit `chat_config.json`:

```json
{
  "tools": {
    "enabled": ["shell", "echo", "file_reader"],
    "max_iterations": 3,
    "auto_discover": true
  }
}
```

- `enabled`: List of tool names to enable
- `max_iterations`: Max tool calls per turn
- `auto_discover`: Auto-load tools from `zagent/tools/`

### Disable Auto-Discovery

If you want manual control:

```json
{
  "tools": {
    "enabled": ["shell"],
    "max_iterations": 3,
    "auto_discover": false
  }
}
```

Then register manually in `zagent/cli.py`:

```python
from zagent.tools.echo_tool import EchoTool

registry = get_global_registry()
registry.register(EchoTool(), enabled=True)
```

---

## Tool Interface Reference

### Required Methods

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier"""
        
    @property
    @abstractmethod
    def description(self) -> str:
        """What the tool does"""
        
    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """Can this tool handle this message?"""
        
    @abstractmethod
    def extract_request(self, message: str) -> str | None:
        """Extract the request from message"""
        
    @abstractmethod
    def execute(self, request: str, context=None) -> str:
        """Execute and return formatted result"""
```

### ToolResult Helper

```python
result = ToolResult(
    tool_name="my_tool",
    request="original request",
    success=True,
    output="output text",
    error="error text if failed",
    metadata={"key": "value"}
)

return result.format()
```

---

## Best Practices

1. **Use Regex for Pattern Matching**: Keep patterns simple and clear
2. **Return ToolResult**: Always use `ToolResult` for consistent formatting
3. **Handle Errors**: Wrap execution in try/except
4. **Add Metadata**: Include useful info like timing, API calls, etc.
5. **User Confirmation**: For dangerous operations (like shell), ask for confirmation

---

## Tips

- Tool names should be short and descriptive
- Use `<toolname>...</toolname>` format for clarity
- Tools are checked in registration order
- First matching tool wins
- Context dict can pass state between turns
