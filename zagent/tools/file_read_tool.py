import os
import re
import subprocess
from typing import Any, Dict

from zagent.tools.base import BaseTool, ToolResult

_READ_FILE_RE = re.compile(r"<read_file>(.*?)</read_file>", re.DOTALL)

class FileReadTool(BaseTool):
    """Tool for reading file contents (Local or Docker)."""
    
    def __init__(
        self, 
        use_docker: bool = False,
        container_name: str | None = None
    ) -> None:
        self.use_docker = use_docker
        self.container_name = container_name
    
    @property
    def name(self) -> str:
        return "file_read"
    
    @property
    def description(self) -> str:
        return "Read contents of a file (Local or Docker)"
    
    def can_handle(self, message: str) -> bool:
        return bool(_READ_FILE_RE.search(message))
    
    def extract_request(self, message: str) -> str | None:
        match = _READ_FILE_RE.search(message)
        if match:
            return match.group(1).strip()
        return None
    
    def _read_local(self, path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _read_docker(self, path: str) -> str:
        if not self.container_name:
            raise RuntimeError("Docker container name not specified")
        
        # Use cat to read file inside docker
        docker_cmd = f'docker exec {self.container_name} cat "{path}"'
        proc = subprocess.run(
            docker_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"Failed to read file in Docker (code {proc.returncode})")
        return proc.stdout

    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        path = request
        mode = "Docker" if self.use_docker else "Local"
        print(f"\n[tool] assistant requested to read file ({mode}): {path}")
        
        try:
            if self.use_docker:
                content = self._read_docker(path)
            else:
                content = self._read_local(path)
            
            result = ToolResult(
                tool_name=self.name,
                request=request,
                success=True,
                output=content,
                metadata={"mode": mode.lower(), "path": path}
            )
            return result.format()
            
        except Exception as e:
            result = ToolResult(
                tool_name=self.name,
                request=request,
                success=False,
                error=str(e)
            )
            return result.format()
