# ZAgent: Modular Elite Bug Hunter 🕵️‍♂️🛡️

ZAgent is a powerful, modular AI agent designed for professional security researchers and bug hunters. It automates reconnaissance, vulnerability discovery, and reporting within a secure, containerized environment.

## Key Features

- **Modular Tool System**: Easily extend ZAgent by adding new tools to `zagent/tools/`.
- **Auto-Discovery**: Tools are automatically registered at runtime.
- **Docker Sandbox**: Safely execute shell commands and file operations.
- **Persistent Auth**: Your credentials are saved securely for repeated use.
- **Structured Reporting**: Automatically documents findings in `report.md` with incremental IDs.
- **Relentless Persona**: Optimized to pivot and never surrender until a weakness is found.

## Installation 🛠️

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/3lyly0/ZAgent.git
   cd ZAgent
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Docker Setup (Recommended)**:
   Ensure Docker is running and create a sandbox container:
   ```bash
   docker run -itd --name zagent-sandbox alpine sh
   ```

## Usage 🚀

### First Run

Provide your API token (and optional cookie). ZAgent will save these for future sessions.

```bash
python main.py --token YOUR_TOKEN --save-auth "start hunting on example.com"
```

### Configuration

Customize behaviors in `chat_config.json`:

```json
{
  "tools": {
    "shell": {
      "auto_approve": false,   // Set to true for hands-free automation
      "use_docker": true,      // Execution takes place inside Docker
      "container_name": "zagent-sandbox"
    }
  }
}
```

# Subsequent runs (uses saved auth)
python main.py "your prompt here"
```

### Authentication

```bash
# Save auth explicitly
python main.py --token YOUR_TOKEN --save-auth

# Clear saved auth
python main.py --clear-auth

# Use with cookie
python main.py --token YOUR_TOKEN --cookie "your_cookie"
```

## Project Structure 📁

```
ZAgent/
├── zagent/                # Main package
│   ├── core/             # Core functionality
│   │   ├── auth.py       # Auth persistence
│   │   ├── client.py     # API client
│   │   └── state.py      # Chat state management
│   ├── tools/            # Tool modules
│   │   ├── base.py       # Base tool class
│   │   ├── shell_tool.py # Shell command execution
│   │   └── __init__.py   # Tool registry
│   └── cli.py            # CLI interface
├── docs/                 # Documentation
│   └── adding_tools.md   # Tool development guide
├── main.py               # Entry point
├── system.txt            # System prompt
└── chat_config.json      # Configuration
```

## Configuration ⚙️

Edit `chat_config.json` to customize:

```json
{
  "model": "GLM-4-6-API-V1",
  "features": {
    "enable_thinking": false,
    "web_search": false
  },
  "runtime": {
    "show_thinking": true,
    "thinking_color": "gray"
  },
  "tools": {
    "enabled": ["shell"],
    "max_iterations": 3,
    "auto_discover": true
  }
}
```

## Available Tools 🛠️

### Shell Tool

Execute shell commands with confirmation:

```
Assistant: <shell>ls -la</shell>
[tool] assistant requested shell command:
ls -la
Execute this command? [y/N]: y
```

## Adding Custom Tools 🎨

See [docs/adding_tools.md](docs/adding_tools.md) for detailed guide.

**Quick example:**

```python
# Create zagent/tools/my_tool.py
from zagent.tools.base import BaseTool, ToolResult
import re

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Does something awesome"
    
    def can_handle(self, message: str) -> bool:
        return bool(re.search(r"<mytool>", message))
    
    def extract_request(self, message: str) -> str | None:
        match = re.search(r"<mytool>(.*?)</mytool>", message, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def execute(self, request: str, context=None) -> str:
        # Your logic here
        return ToolResult(
            self.name, request, True,
            output="Result!"
        ).format()
```

That's it! The tool will be auto-discovered on next run.

## Examples 💡

### Basic Chat

```bash
python main.py "explain quantum computing"
```

### Interactive Mode

```bash
python main.py
You: what can you do?
Assistant: [response]
You: help me with python
Assistant: [response]
You: exit
```

### Using Tools

```bash
python main.py "list files in current directory"
# AI will use <shell>ls</shell> or <shell>dir</shell>
```

## Architecture Highlights 🏗️

- **BaseTool**: Abstract class for all tools
- **ToolRegistry**: Manages tool lifecycle
- **Auto-Discovery**: Scans `zagent/tools/` for tool classes
- **AuthConfig**: Secure credential storage
- **Modular**: Each component has single responsibility

## Development 🔧

### Adding Dependencies

```bash
pip install new_package
# Update requirements.txt if you create one
```

### Testing Tools

```bash
# Test shell tool
python main.py "run 'echo test'"

# Test custom tool
python main.py "use my custom tool"
```

## Security 🔒

- Auth saved to `~/.zagent_auth.json` (user-readable only)
- Shell commands require explicit confirmation
- No auto-execution of dangerous operations

## Contributing 🤝

1. Create tool in `zagent/tools/`
2. Inherit from `BaseTool`
3. Implement required methods
4. Tool auto-loads on restart

## License

Open source - use as you wish!

## Credits

Built with ❤️ by 3lyly0

---

**Need help?** Check [docs/adding_tools.md](docs/adding_tools.md) for detailed examples.
