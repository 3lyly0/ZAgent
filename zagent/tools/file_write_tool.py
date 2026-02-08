import re
import subprocess
import os
from typing import Any, Dict

from zagent.tools.base import BaseTool, ToolResult

# Pattern: <write_file path="...">content</write_file>
_WRITE_FILE_RE = re.compile(r'<write_file\s+path=["\'](.*?)["\']>(.*?)</write_file>', re.DOTALL)

class FileWriteTool(BaseTool):
    """Tool for writing content to files (Local or Docker)."""
    
    def __init__(
        self, 
        use_docker: bool = False,
        container_name: str | None = None
    ) -> None:
        self.use_docker = use_docker
        self.container_name = container_name
    
    @property
    def name(self) -> str:
        return "file_write"
    
    @property
    def description(self) -> str:
        return "Write content to a file (Local or Docker)"
    
    def can_handle(self, message: str) -> bool:
        return bool(_WRITE_FILE_RE.search(message))
    
    def extract_request(self, message: str) -> str | None:
        match = _WRITE_FILE_RE.search(message)
        if match:
            # We return path and content separated by a null byte or just as a tuple-like string
            # But let's keep it simple for execute() to parse.
            path = match.group(1).strip()
            content = match.group(2)
            return f"{path}|{content}"
        return None
    
    def _write_local(self, path: str, content: str) -> None:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_docker(self, path: str, content: str) -> None:
        if not self.container_name:
            raise RuntimeError("Docker container name not specified")
        
        # We use a temp file or echo to write
        # To avoid shell injection issues with complex content, we can use a heredoc
        # escaping quotes for the outer docker command
        escaped_content = content.replace("'", "'\\''")
        docker_cmd = f"docker exec {self.container_name} sh -c \"cat << 'EOF' > '{path}'\n{content}\nEOF\n\""
        
        proc = subprocess.run(
            docker_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"Failed to write file in Docker (code {proc.returncode})")

    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        try:
            if "|" not in request:
                raise ValueError("Invalid write_file request format. Use <write_file path=\"...\">content</write_file>")
            
            path, content = request.split("|", 1)
            mode = "Docker" if self.use_docker else "Local"
            
            print(f"\n[tool] assistant requested to write file ({mode}): {path}")
            
            if self.use_docker:
                self._write_docker(path, content)
            else:
                self._write_local(path, content)
            
            result = ToolResult(
                tool_name=self.name,
                request=f"Write to {path}",
                success=True,
                output=f"Successfully wrote {len(content)} bytes to {path} ({mode})",
                metadata={"mode": mode.lower(), "path": path}
            )
            return result.format()
            
        except Exception as e:
            result = ToolResult(
                tool_name=self.name,
                request=request.split("|")[0] if "|" in request else request,
                success=False,
                error=str(e)
            )
            return result.format()
