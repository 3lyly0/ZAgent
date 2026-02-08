"""Shell command execution tool."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from zagent.tools.base import BaseTool, ToolResult


# Regex patterns for shell command extraction
_SHELL_TAG_RE = re.compile(r"<shell>(.*?)</shell>", re.DOTALL | re.IGNORECASE)
_SHELL_FENCE_RE = re.compile(r"```shell\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class ShellTool(BaseTool):
    """Tool for executing shell commands with user confirmation and optional Docker support."""
    
    def __init__(
        self, 
        auto_approve: bool = False, 
        timeout: int = 120,
        use_docker: bool = False,
        container_name: str | None = None
    ) -> None:
        """Initialize shell tool.
        
        Args:
            auto_approve: If True, skip user confirmation (dangerous!)
            timeout: Command execution timeout in seconds
            use_docker: If True, execute commands inside a Docker container
            container_name: Name of the Docker container to use
        """
        self.auto_approve = auto_approve
        self.timeout = timeout
        self.use_docker = use_docker
        self.container_name = container_name
    
    @property
    def name(self) -> str:
        return "shell"
    
    @property
    def description(self) -> str:
        return "Execute shell commands (Local or Docker) with user confirmation"
    
    def can_handle(self, message: str) -> bool:
        """Check if message contains shell command request."""
        return bool(_SHELL_TAG_RE.search(message) or _SHELL_FENCE_RE.search(message))
    
    def extract_request(self, message: str) -> str | None:
        """Extract shell command from message."""
        # Try <shell> tags first
        match = _SHELL_TAG_RE.search(message)
        if match:
            cmd = match.group(1).strip()
            return cmd or None
        
        # Try ```shell code blocks
        match = _SHELL_FENCE_RE.search(message)
        if match:
            cmd = match.group(1).strip()
            return cmd or None
        
        return None
    
    def _execute_local(self, command: str) -> tuple[int, str, str]:
        """Execute command locally."""
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def _execute_docker(self, command: str) -> tuple[int, str, str]:
        """Execute command inside Docker container."""
        if not self.container_name:
            raise RuntimeError("Docker container name not specified")
        
        # Escape command for shell execution inside docker exec
        # We use 'sh -c' to support complex commands and pipes
        escaped_command = command.replace("\"", "\\\"")
        docker_cmd = f'docker exec {self.container_name} sh -c "{escaped_command}"'
        
        proc = subprocess.run(
            docker_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        """Execute shell command.
        
        Args:
            request: The shell command to execute
            context: Optional context
            
        Returns:
            Formatted execution result
        """
        mode = "Docker" if self.use_docker else "Local"
        print(f"\n[tool] assistant requested {mode} shell command:")
        print(request)
        
        # Ask for confirmation unless auto-approved
        if not self.auto_approve:
            choice = input(f"Execute this command on {mode}? [y/N]: ").strip().lower()
            if choice not in {"y", "yes"}:
                result = ToolResult(
                    tool_name=self.name,
                    request=request,
                    success=False,
                    error="user rejected command"
                )
                print("[tool] cancelled")
                return result.format()
        
        print(f"[tool] running on {mode}...\n")
        
        try:
            if self.use_docker:
                returncode, stdout, stderr = self._execute_docker(request)
            else:
                returncode, stdout, stderr = self._execute_local(request)
            
            print("[tool] exit_code:", returncode)
            if stdout:
                print("[tool] stdout:\n" + stdout)
            if stderr:
                print("[tool] stderr:\n" + stderr)
            
            result = ToolResult(
                tool_name=self.name,
                request=request,
                success=returncode == 0,
                output=stdout or "(empty)",
                error=stderr if returncode != 0 else "",
                metadata={
                    "exit_code": returncode,
                    "execution_mode": mode.lower()
                }
            )
            
            return result.format()
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {self.timeout} seconds"
            print(f"[tool] error: {error_msg}")
            result = ToolResult(
                tool_name=self.name,
                request=request,
                success=False,
                error=error_msg
            )
            return result.format()
            
        except Exception as exc:
            error_msg = str(exc)
            print(f"[tool] error: {error_msg}")
            result = ToolResult(
                tool_name=self.name,
                request=request,
                success=False,
                error=error_msg
            )
            return result.format()
