"""Command-line interface for ZAgent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from zagent.core.auth import AuthConfig
from zagent.core.client import ZAIClient
from zagent.core.state import ChatState, DEFAULT_FEATURES
from zagent.tools import get_global_registry, auto_discover_tools


# Configuration files
SYSTEM_PROMPT_FILE = "system.txt"
CHAT_CONFIG_FILE = "chat_config.json"

# Terminal colors
_GRAY = "\033[90m"
_RESET = "\033[0m"

# System hint for tools
_TOOL_SYSTEM_HINT = (
    "\n\nAVAILABLE TOOLS:\n"
    "1. Shell: <shell>command</shell> - Execute terminal commands.\n"
    "2. Read File: <read_file>path</read_file> - Read file contents.\n"
    "3. Write File: <write_file path=\"path\">content</write_file> - Write to files.\n"
    "4. Report: <report title=\"title\">finding</report> - Document findings with auto-IDs.\n"
    "\nUSAGE RULES:\n"
    "- Output ONLY one tool tag per response when an action is required.\n"
    "- Use absolute paths when possible.\n"
    "- After tool result is returned, analyze the output and continue."
)


def _load_system_prompt() -> str | None:
    """Load system prompt from file."""
    path = Path(__file__).parent.parent / SYSTEM_PROMPT_FILE
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def _load_chat_config() -> dict[str, Any]:
    """Load chat configuration from file."""
    path = Path(__file__).parent.parent / CHAT_CONFIG_FILE
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("chat_config.json must contain a JSON object")
    return data


def _merge_features(config: dict[str, Any]) -> dict[str, Any]:
    """Merge default features with config features."""
    raw_features = config.get("features", {})
    if not isinstance(raw_features, dict):
        raw_features = {}
    merged = dict(DEFAULT_FEATURES)
    merged.update(raw_features)
    return merged


def _build_state(system_prompt: str | None, config: dict[str, Any]) -> ChatState:
    """Build chat state from config."""
    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}

    prompt = (system_prompt or "").strip()
    if prompt:
        prompt = f"{prompt}{_TOOL_SYSTEM_HINT}"
    else:
        prompt = _TOOL_SYSTEM_HINT.strip()

    return ChatState(
        model=str(config.get("model", "GLM-4-6-API-V1")),
        system_prompt=prompt,
        features=_merge_features(config),
        runtime_show_thinking=bool(runtime.get("show_thinking", True)),
        runtime_thinking_color=str(runtime.get("thinking_color", "gray")),
    )


def _setup_tools(config: dict[str, Any]) -> None:
    """Setup and configure tools."""
    registry = get_global_registry()
    
    # Auto-discover tools if enabled
    tools_config = config.get("tools", {})
    if tools_config.get("auto_discover", True):
        discovered = auto_discover_tools()
        
        # Configure ShellTool specifically if it was discovered
        shell_config = tools_config.get("shell", {})
        if shell_config:
            shell_tool = registry.get_tool("shell")
            if shell_tool and hasattr(shell_tool, 'use_docker'):
                shell_tool.auto_approve = shell_config.get("auto_approve", False)
                shell_tool.use_docker = shell_config.get("use_docker", False)
                shell_tool.container_name = shell_config.get("container_name", "zagent-sandbox")
        
        # Configure File Tools if discovered
        for tool_name in ["file_read", "file_write"]:
            tool = registry.get_tool(tool_name)
            if tool and hasattr(tool, 'use_docker'):
                tool.use_docker = shell_config.get("use_docker", False)
                tool.container_name = shell_config.get("container_name", "zagent-sandbox")
        
        if discovered > 0:
            print(f"[init] discovered {discovered} tool(s)")
    
    # Configure enabled tools
    enabled_tools = tools_config.get("enabled")
    if isinstance(enabled_tools, list):
        all_tools = {tool.name for tool in registry._tools.values()}
        for tool_name in all_tools:
            if tool_name in enabled_tools:
                registry.enable(tool_name)
            else:
                registry.disable(tool_name)


def _print_thinking(delta: str, color: str) -> None:
    """Print thinking output with color."""
    if color == "gray":
        print(f"{_GRAY}{delta}{_RESET}", end="", flush=True)
        return
    print(delta, end="", flush=True)


def _stream_current_turn(
    client: ZAIClient,
    state: ChatState,
    prompt: str
) -> None:
    """Stream a single turn and update state."""
    completion_payload = state.build_completion_payload(prompt)
    for event in client.stream_completion(state.chat_id, completion_payload):
        if event.get("type") != "chat:completion":
            continue
        data = event.get("data", {})
        delta = data.get("delta_content")
        if not delta:
            continue

        phase = data.get("phase", "answer")
        if phase == "thinking" and state.runtime_show_thinking:
            _print_thinking(delta, state.runtime_thinking_color)
        else:
            state.apply_assistant_delta(delta)
            print(delta, end="", flush=True)

        if data.get("phase") == "done" or data.get("done") is True:
            state.finish_turn()
    
    # Safety: always finish turn after loop to ensure parentId is updated
    # and we can proceed to tool execution even if 'done' signal was missed.
    state.finish_turn()
    print()


def _run_turn(client: ZAIClient, state: ChatState, prompt: str) -> None:
    """Execute a single conversation turn."""
    state.begin_turn(prompt)
    _stream_current_turn(client, state, prompt)


def _run_turn_with_tools(
    client: ZAIClient,
    state: ChatState,
    prompt: str,
    max_iterations: int = 3
) -> None:
    """Execute a turn with tool support."""
    registry = get_global_registry()
    
    _run_turn(client, state, prompt)
    
    for _ in range(max_iterations):
        executed, result = registry.execute_if_applicable(state.current_assistant_content)
        if not executed:
            return
        _run_turn(client, state, result)


def run() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ZAgent - Modular AI Agent with extensible tools"
    )
    parser.add_argument("--token", help="API token (saved after first use)")
    parser.add_argument("--cookie", default=None, help="Optional cookie")
    parser.add_argument("--save-auth", action="store_true", help="Save authentication credentials")
    parser.add_argument("--clear-auth", action="store_true", help="Clear saved authentication")
    parser.add_argument("prompt", nargs="*", help="Initial prompt")
    args = parser.parse_args()

    # Handle auth management
    auth_config = AuthConfig()
    
    if args.clear_auth:
        auth_config.clear()
        print("Authentication cleared.")
        return
    
    # Get token from args or saved config
    token = args.token
    cookie = args.cookie
    
    if not token:
        token = auth_config.get_token()
        if not token:
            print("Error: No token provided and no saved authentication found.")
            print("Use --token to provide a token, or save it with --save-auth")
            return
        cookie = cookie or auth_config.get_cookie()
        print("[init] using saved authentication")
    
    # Save auth if requested
    if args.save_auth or (args.token and not auth_config.has_auth()):
        auth_config.save_auth(token, cookie)
        print("[init] authentication saved")

    # Initialize client and state
    client = ZAIClient(token=token, cookie=cookie)
    config = _load_chat_config()
    state = _build_state(_load_system_prompt(), config)
    
    # Setup tools
    _setup_tools(config)
    
    # Get tool config
    tools_config = config.get("tools", {})
    max_iterations = tools_config.get("max_iterations", 3)

    # Get first prompt
    first_prompt = " ".join(args.prompt).strip()
    if not first_prompt:
        first_prompt = input("You: ").strip()
    if not first_prompt:
        raise SystemExit("empty prompt")

    # Create new chat
    state.begin_turn(first_prompt)
    new_chat_payload = state.build_new_chat_payload(first_prompt)
    state.chat_id = client.create_chat(new_chat_payload)
    print(f"chat_id: {state.chat_id}")

    # Stream first response
    _stream_current_turn(client, state, first_prompt)

    # Handle tools for first response
    registry = get_global_registry()
    for i in range(max_iterations):
        executed, result = registry.execute_if_applicable(state.current_assistant_content)
        if not executed:
            break
        print(f"\n{_GRAY}[iteration {i+1}/{max_iterations}]{_RESET}")
        _run_turn(client, state, result)

    # Main conversation loop
    while True:
        try:
            prompt = input("\nYou: ").strip()
            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit", "/exit", "/quit"}:
                break
            
            _run_turn(client, state, prompt)
            
            # Sub-loop for tools
            for i in range(max_iterations):
                executed, result = registry.execute_if_applicable(state.current_assistant_content)
                if not executed:
                    break
                print(f"\n{_GRAY}[iteration {i+1}/{max_iterations}]{_RESET}")
                _run_turn(client, state, result)
                
        except KeyboardInterrupt:
            print("\n[stop] interrupted by user")
            continue


if __name__ == "__main__":
    run()
