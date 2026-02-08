import os
import re
from typing import Any, Dict
from datetime import datetime

from zagent.tools.base import BaseTool, ToolResult

# Pattern: <report title="...">finding</report>
_REPORT_RE = re.compile(r'<report\s+title=["\'](.*?)["\']>(.*?)</report>', re.DOTALL)

class ReportTool(BaseTool):
    """Tool for generating structured security reports with incremental IDs."""
    
    REPORT_FILE = "report.md"
    
    @property
    def name(self) -> str:
        return "report"
    
    @property
    def description(self) -> str:
        return "Add a finding to the security report with an incremental ID"
    
    def can_handle(self, message: str) -> bool:
        return bool(_REPORT_RE.search(message))
    
    def extract_request(self, message: str) -> str | None:
        match = _REPORT_RE.search(message)
        if match:
            title = match.group(1).strip()
            content = match.group(2).strip()
            return f"{title}|{content}"
        return None
    
    def _get_next_id(self) -> str:
        if not os.path.exists(self.REPORT_FILE):
            return "001"
        
        with open(self.REPORT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find all IDs in format ### ID: XXX
        ids = re.findall(r"### ID: (\d+)", content)
        if not ids:
            return "001"
        
        last_id = max(int(i) for i in ids)
        return f"{last_id + 1:03d}"

    def execute(self, request: str, context: dict[str, Any] | None = None) -> str:
        try:
            if "|" not in request:
                raise ValueError("Invalid report format")
            
            title, content = request.split("|", 1)
            next_id = self._get_next_id()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report_entry = (
                f"\n---\n"
                f"### ID: {next_id}\n"
                f"**Title**: {title}\n"
                f"**Date**: {timestamp}\n\n"
                f"{content}\n"
            )
            
            # Write to file
            mode = "a" if os.path.exists(self.REPORT_FILE) else "w"
            header = "# ZAgent Security Report\n\n" if mode == "w" else ""
            
            with open(self.REPORT_FILE, mode, encoding="utf-8") as f:
                if header:
                    f.write(header)
                f.write(report_entry)
            
            print(f"\n[tool] assistant added finding {next_id}: {title}")
            
            result = ToolResult(
                tool_name=self.name,
                request=title,
                success=True,
                output=f"Finding {next_id} successfully added to {self.REPORT_FILE}",
                metadata={"id": next_id, "title": title}
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
